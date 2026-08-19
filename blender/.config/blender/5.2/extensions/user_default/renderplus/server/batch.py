# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright (C) Diego Gangl
#   <diego@sinestesia.co>
#
#   This file is part of Render+.
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ## END GPL LICENSE BLOCK ##

"""Functions to control a batch."""
import os
import logging
import warnings
from enum import Enum
from multiprocessing import Pipe
from time import sleep
from copy import deepcopy
import concurrent.futures
from pathlib import Path, PureWindowsPath

import utils
import notifications
import poweroff
from config import Config
from exceptions import BatchCancelled
from job import RemoteJob, LocalJob

log = logging.getLogger("batch.run")


# TODO: Remove and capture KeyboardInterrupt when Bottle 0.13 is out
warnings.filterwarnings("ignore", category=ResourceWarning)


class Status(Enum):
    """Status for a batch."""

    WAITING = 0
    RUNNING = 1
    FINISHED = 2
    CANCELLED = 3


class Batch:
    """Represents a batch."""

    def __init__(self) -> None:
        self.status = Status.WAITING
        self.cancelling = False
        self.current_job = None
        self.recipe = {}
        self.name = ''
        self.hooks = {}
        self.notifications = []
        self.jobs = []
        self.parallel_jobs = 1
        self.pipes = []
        self.temp = utils.temp_path()


    def set_config(self, config: Config) -> None:
        """Set the config for this batch."""

        self.config = config
        self.cleanup = config.cleanup


    def set_recipe(self, recipe: dict) -> None:
        """Set a recipe for the batch."""

        self.recipe = recipe
        self.name = recipe["name"]
        self.blender_bin = recipe["settings"]["blender_bin"]
        self.hooks = recipe["hooks"]
        self.parallel_jobs = recipe["settings"]["parallel_jobs"]
        self.notifications = recipe["notifications"]
        self.jobs = self.build_jobs(recipe['jobs'])
        self.pipes = [Pipe() for _ in range(len(self.jobs))]
        self.cancel_pipes = [Pipe() for _ in range(len(self.jobs))]
        self.job_status = [j.to_dict() for j in self.jobs]
        self.recipe['settings']['temp'] = self.temp

        self.cli = False
        self.use_stats = True
        self.procs = []

        self.stats: dict[str, float] = {
            "slowest_index": -1,
            "slowest_time": -1,
            "fastest_index":-1,
            "fastest_time":-1,
            "average_time":-1,
        }

        self.times: dict[str, float] = {
            "started": -1,
            "finished": -1,
            "rendertime": -1,
        }


    def replace_filepath(self, filepath: str, new_path: str) -> None:
        """Replace filepath in render jobs."""

        for job in self.jobs:
            if self.recipe["settings"]["OS"] == "Windows":
                name = PureWindowsPath(job.file).name
            else:
                name = Path(job.file).name

            if name == filepath:
                log.debug(f"Found file {filepath} for job #{job.id}")
                log.debug(f"Replacing with {new_path}")

                job.file = new_path


    def get_mail_message(self) -> str:
        """Generate email message."""

        average = utils.format_time(self.stats["average_time"])
        fastest = utils.format_time(self.stats["fastest_time"])
        slowest = utils.format_time(self.stats["slowest_time"])

        started = utils.date_format(self.times["started"])
        finished = utils.date_format(self.times["finished"])
        rendertime = self.times["rendertime"]

        return (
            f'Hi! Batch "{self.name}" has just finished rendering.\n\n'
            f"- Number of jobs: {len(self.jobs)}\n"
            f"- Started: {started}\n"
            f"- Finished: {finished}\n"
            f"- Total Rendertime: {rendertime}\n"
            f"- Average rendertime: {average}\n"
            f'- Slowest Job was #{self.stats["slowest_job"]} at {slowest}\n'
            f'- Fastest Job was #{self.stats["fastest_job"]} at {fastest}\n'
        )


    def build_jobs(self, jobs: dict) -> list:
        """Build jobs according to settings."""

        # Use the blender bin from the config or
        # correct if blender binary is missing
        if self.config.blender_bin or not self.recipe['settings']['blender_bin']:
            self.recipe['settings']['blender_bin'] = self.config.blender_bin

        if not self.config.workers or self.config.disable_workers:
            # If no workers are setup or they are disabled, we just
            # generate local render jobs
            job_list = []

            for i, j in enumerate(jobs):
                local_job = LocalJob.from_recipe(i, j, self.recipe["settings"])
                local_job.temp_path = self.temp

                job_list.append(local_job)

            return job_list
        else:
            # Otherwise we distribute them to the different workers
            worker_iter = self.config.iter_workers()
            job_list = []

            for i, job in enumerate(jobs):
                single_recipe = self.single_job_recipe(job['id'])
                j = RemoteJob.from_recipe(i, single_recipe, next(worker_iter))
                job_list.append(j)

            return job_list


    def reset_state(self) -> None:

        self.times = {
            "started": -1,
            "finished": -1,
            "rendertime": -1,
        }

        self.stats = {
            "slowest_index": -1,
            "slowest_time": -1,
            "fastest_index": -1,
            "fastest_time": -1,
            "average_time": -1,
        }


    def jobs_info(self) -> list:
        """Return a dict with info from the pipes."""

        for i, job in enumerate(self.job_status):
            self.job_status[i] = self.jobs[i].to_dict()

        return self.job_status


    def single_job_recipe(self, index: int) -> dict:
        """Create a copy of the recipe with a single job."""

        new_recipe =  deepcopy(self.recipe)
        new_recipe['jobs'][:] = [j for j in new_recipe['jobs'] if j['id'] == index]

        return new_recipe


    def upload_urls(self) -> dict[str, str]:
        """Return list of file upload urls for all jobs."""

        output = {}

        for job in self.jobs:
            if job.url:
                output[job['id']] = job.url + 'batch/file'
            else:
                output[job['id']] = None

        return output


    def process(self) -> None:
        """Run a batch."""

        log.debug("Preparing to run a batch. Resetting state.")
        self.reset_state()

        self.status = Status.RUNNING
        log.debug("Running Pre-batch hook.")
        utils.run_hooks(self.hooks["PRE_BATCH"], self.blender_bin, self.name)

        log.debug("Starting batch.")

        started, stop_timer = utils.timer()
        self.times["started"] = started

        if not self.config.workers or self.config.disable_workers:
            parallel_count = self.parallel_jobs
        else:
            parallel_count = len(self.config.workers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as e:
            for job in self.jobs:
                if job.enabled:
                    e.submit(job.run)

        sleep(2)

        log.debug("Finished batch. Calculating times.")

        stopped, elapsed = stop_timer()
        self.times["rendertime"] = elapsed
        self.times["finished"] = stopped
        self.stats = utils.calculate_stats(self.jobs)

        log.debug("Running post-batch hook.")
        utils.run_hooks(self.hooks["POST_BATCH"], self.blender_bin, self.name)

        print("-- Batch Finished succesfully")

        log.debug(
            ("Batch completed succesfully." f' Rendertime: {self.times["rendertime"]}')
        )

        self.status = Status.FINISHED

    def run(self) -> None:
        try:
            self.process()
            print("Batch completed succesfully.")
            print(f'Total Rendertime: {self.times["rendertime"]}\n')

            if self.recipe['notifications']['mail']['enabled']:
                notifications.mail(self.recipe['notifications']['mail'],
                                   self.get_mail_message())

            if self.recipe['notifications']['desktop']:
                notifications.desktop('Batch Rendering Finished.')

            if self.recipe["notifications"]["sound"]["enabled"]:
                notifications.sound(
                    self.recipe["settings"]["blender_bin"],
                    self.recipe["notifications"]["sound"],
                )

            if self.recipe["poweroff"]["enabled"] and self.status == Status.FINISHED:
                poweroff.off(self.recipe["poweroff"]["action"])

        except FileNotFoundError as e:
            self.status = Status.CANCELLED
            print("-- Batch was cancelled due to error")
            print(e)
            log.debug("Batch was cancelled due to error")

        except BatchCancelled:
            print("-- Batch was cancelled")
            log.debug("Batch was cancelled")

        finally:
            self.reset_state()

            if self.cleanup:
                self.clean_temp()

    def cancel(self) -> None:
        """Cancel entire batch."""

        for job in self.jobs:
            job.do_cancel = True

    def cancel_job(self, index: int) -> None:
        """Cancel render job."""

        self.jobs[index].do_cancel = True


    def check_all_workers(self) -> dict[str, dict]:
        """Ping all workers and gather the replies."""

        output = {}

        for worker in self.config.workers:
            output[worker.name] = worker.check()

        return output


    def clean_temp(self) -> None:
        """Remove all files in the temp folder."""

        log.debug(f'Cleaning up temp folder: {self.temp}')

        for a_file in os.listdir(self.temp):
            filepath = os.path.join(self.temp, a_file)

            try:
                if os.path.isfile(filepath):
                    log.debug(f"Deleting {filepath}")
                    os.unlink(filepath)
            except PermissionError:
                print(f"Could not delete file {filepath}!")
                log.error(f"Could not delete file {filepath}!")
