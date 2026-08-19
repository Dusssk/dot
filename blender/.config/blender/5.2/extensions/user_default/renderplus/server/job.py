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

"""Functions and state for a single render job."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from io import TextIOWrapper
import os
import logging
import re
import subprocess
import time
import datetime
import requests

from typing import Dict, Tuple, Self
from pathlib import Path
from platform import system


# If name has dots in it, it's imported as a part of a package
# (inside Blender), otherwise it's imported by the server script
# which needs absolute imports. Yeah, the module system sucks
if "." in __name__:
    from . import custom
    from . import utils
    from .config import WorkerConfig
    from .status import Status, Step
    from .parser import ParsedData, Parser
else:
    import utils
    import custom
    from config import WorkerConfig
    from status import Status, Step
    from parser import ParsedData, Parser


log = logging.getLogger("batch.job")


@dataclass
class BaseJob(ABC):
    """Abstract base class for renderjobs."""

    id: int | None = None
    name: str = ''
    url: str = ''
    file: str = ''

    recipe: dict = field(default_factory=lambda: {})
    enabled: bool = True
    engine: str = ''
    use_turbotools: bool = False
    output: str = ''
    settings: dict = field(default_factory=lambda: {})

    status: Status = Status.WAITING
    progress: float = 0
    step: Step = Step.RENDERING
    time_start: float = 0
    time_end: float = 0
    time_total: float = 0

    messages: list = field(default_factory=lambda: [])
    from_engine: dict = field(default_factory=lambda: {})
    do_cancel: bool = False
    poll_interval: int = 2


    def __str__(self) -> str:
        """String representation."""

        return f"Job #{self.id}. Status: {self.status}"


    def to_dict(self) -> Dict:
        """Pass data as dict for json."""

        out = {
            "id": 0,
            "status": self.status.value,
            "name": self.name,
            "times": {
                "started": self.time_start,
                "finished": self.time_end,
                "rendertime": self.time_total,
            },
            "messages": self.messages,
            "progress": self.progress,
            "upload_msg": self.upload_msg(),
            "engine": {
                "type": self.engine,
                "data": self.from_engine,
            },
        }

        return out

    def upload_msg(self) -> str:
        """Upload message."""

        return ''


    @abstractmethod
    def setup(self) -> None:
        """Setup the renderjob."""
        ...


    @abstractmethod
    def cancel(self) -> None:
        """Cancel the renderjob."""
        ...


    @abstractmethod
    def poll(self) -> None:
        """Poll progress of the renderjob."""
        ...

    def poll_loop(self) -> None:
        """Continually check render job."""

        self.poll()

        while self.status is Status.RUNNING:
            time.sleep(self.poll_interval)
            self.poll()

            if self.do_cancel:
                log.debug(f"Cancelling job #{self.id}...")
                self.cancel()

        self.poll()


    def run(self) -> None:
        """Start the renderjob."""

        self.setup()
        self.poll_loop()
        self.on_finished()


    @abstractmethod
    def on_finished(self) -> None:
        """Run when the render job has finished"""
        ...



class RemoteJob(BaseJob):
    """Render jobs running in other computers."""

    @classmethod
    def from_recipe(cls, id: int, recipe: dict, config: WorkerConfig) -> Self:
        instance = cls()

        instance.id = id
        instance.name = recipe['jobs'][0]['name']
        instance.engine = recipe['jobs'][0]['engine']
        instance.enabled = recipe['jobs'][0]['enabled']
        instance.file = recipe['jobs'][0]['blend_file']
        instance.recipe = recipe

        instance.url = f'http://{config.address}:{config.port}/'
        instance.poll_interval = config.poll_interval

        if not instance.enabled:
            instance.status = Status.DISABLED

        return instance


    def pre_check(self) -> bool:
        r = requests.get(self.url + 'batch/ready')

        return r.json()['status'] == 'READY'


    def upload_msg(self) -> str:
        """Upload message."""

        return f'Uploading to worker at {self.url}'


    def upload_file(self) -> requests.Response:
        """Upload file to worker."""

        with open(self.file, 'rb') as stream:
            the_file = { 'file': stream }
            file_upload = requests.post(self.url + 'batch/file/',
                                        files=the_file,
                                        timeout=20)

        return file_upload


    def setup(self) -> None:
        """Start the rendering process."""

        log.debug(f'Setting up remote job {self.id} for {self.url}')
        submission = requests.post(self.url + 'batch/recipe', 
                                             json=self.recipe, 
                                             timeout=20)

        if submission.status_code != 201:
            self.status = Status.FAILED
            log.error(f"Failed to submit recipe for remote job #{self.id}.")
            return

        log.debug(f'Uploading file for remote job at {self.url}')
        self.status = Status.UPLOADING
        
        try:
            uploaded = self.upload_file()
        except FileNotFoundError:
            self.status = Status.FAILED
            log.error(f"Failed to find blend file {self.file}")
            return

        except PermissionError:
            self.status = Status.FAILED
            log.error(f"Not enough permissions to open {self.file}")
            return

        if uploaded.status_code != 201:
            self.status = Status.FAILED
            log.error(f"Failed to send blendfile for remote job #{self.id}")
            log.error(f"Upload failed with status {uploaded.status_code}. Reply: {uploaded.text}")
            return

        started = requests.get(self.url + 'batch/start')

        if started.status_code != 201:
            self.status = Status.FAILED
            log.error(f"Failed to start remote batch for job #{self.id}")
            return

        log.debug(f'Batch has started for remote job at {self.url}')
        self.status = Status.RUNNING


    def poll(self) -> None:

        if self.status not in (Status.WAITING, Status.RUNNING):
            return

        r = requests.get(self.url + 'batch/jobs/0', timeout=5)
        data = r.json()

        self.progress = data['progress']
        self.messages = data['messages']
        self.status = Status[data['status']]
        self.engine = data['engine']['type']
        self.from_engine = data['engine']['data']
        self.time_start = data['times']['started']
        self.time_end = data['times']['finished']
        self.time_total = data['times']['rendertime']


    def on_finished(self) -> None:
        """Finish the rendering process."""

        log.debug(f"Remote Job #{self.id} finished running. Result: {self.status}")


    def cancel(self) -> None:
        """Cancel the remote job."""

        r = requests.get(self.url + 'cancel')

        if r.status_code == 200:
            self.status = Status.CANCELLED
            log.debug(f"Remote Job #{self.id} cancelled successfully")
        else:
            self.status = Status.FAILED
            log.debug(f"Remote Job #{self.id} failed to cancel")


class LocalJob(BaseJob):
    """A renderjob running on this computer."""

    proc: None | subprocess.Popen = None
    blendfile: str = ''
    clean_output: bool = False
    blender_bin: str = ''
    log_handler: None | TextIOWrapper = None
    log_path: str = ''
    hooks: dict[str, list] = field(default_factory=lambda: {})
    parser: None | Parser = None
    temp_path: str = ''


    @classmethod
    def from_recipe(cls, id: int, recipe: dict, settings: dict) -> Self:
        instance = cls()

        instance.id = id
        instance.name = recipe['name']
        instance.hooks = recipe['hooks']
        instance.engine = recipe['engine']
        instance.blender_bin = settings['blender_bin']
        instance.use_turbotools = recipe['use_turbotools']
        instance.enabled = recipe['enabled']
        instance.file = recipe['blend_file']

        instance.output = recipe['output']
        instance.clean_output = '#' not in recipe['output']

        instance.recipe = recipe
        instance.settings = settings

        if not instance.enabled:
            instance.status = Status.DISABLED

        return instance


    def start_timer(self) -> None:
        """Start timer to measure render time."""

        self.time_start = time.time()


    def on_stopped(self, status: Status) -> None:
        """Calculate render times."""

        self.time_end = time.time()
        self.time_total = abs(self.time_start - self.time_end)
        self.progress = 100
        self.status = status


    def generate_custom_py(self) -> str:
        """Generate the custom python code for this job."""

        return custom.write(self.recipe, self.name, self.settings)


    def stdout_path(self) -> str:
        """Get path to filename to use for job's stdout."""

        use_log = self.settings["write_log"]
        opsys = self.settings["OS"]
        ext = "log" if use_log else "out"
        output = self.output
        stamp = utils.stamp_suffix()

        name = f"{utils.strip_extension(output, opsys)}_{stamp}.{ext}"

        if use_log:
            filepath = os.path.join(os.path.dirname(output), name)
        else:
            filepath = os.path.join(self.temp_path, name)

        log.debug(f"Job stdout file will be at {filepath}")

        return filepath


    def write_log_header(self) -> None:
        """Write header for job log files."""

        assert self.log_handler is not None

        start_time = datetime.datetime.now().isoformat()

        header = (
            f"Render job #{self.id} from Batch {self.name} started in {start_time}\n"
        )
        header += "-" * 80
        header += "\n\n"


        # Move stream position to the end of
        # the header, so stdout comes below the title.
        self.log_handler.write(header)
        self.log_handler.seek(0, 2)


    @staticmethod
    def with_stem(path: Path, stem: str) -> Path:
        """Temporary replacement for with_stem to support older Pythons"""

        return path.with_name(stem + path.suffix)


    def avoid_overwrite(self, srcpath: str) -> str:
        """Rename output filepath so it doesn't get overwritten."""

        log.debug("Attempting to avoid overwrite...")
        log.debug(f"Received {srcpath}")

        index = 0
        anim = self.recipe["animated"]
        frame = self.recipe["frame_start" if anim else "frames"]

        log.debug(f"Frame is {frame}")

        new_path = Path(srcpath)
        original_path = Path(srcpath)

        stem = original_path.stem
        fill = stem.count("#")

        if anim or not self.clean_output:
            log.debug("Will not remove frames from rendered file")

            if fill:
                original_stem = stem.replace("#" * fill, str(frame).zfill(fill))
                original_path = self.with_stem(original_path, original_stem)
            else:
                original_stem = stem
        else:
            log.debug("Will remove frames from rendered file")

            original_stem = stem.replace("_" + ("#" * fill), "")
            original_path = self.with_stem(original_path, original_stem)
            stem = original_stem

        log.debug(f"Path would be {original_path}")

        check_path = original_path

        log.debug(f"Starting to check paths with {check_path}")

        while check_path.exists():
            log.debug(f"Path {check_path} exists")

            # Update index
            index += 1
            log.debug(f"Updating index to {index}")

            # Add index and re-test
            check_stem = original_stem + f"_{index:0>3}"
            check_path = self.with_stem(check_path, check_stem)

            # Also update new path
            new_path = self.with_stem(new_path, stem + f"_{index:0>3}")

            log.debug(f"New path is {new_path}")

            if index > 999:
                log.error("Ran into an infinite loop! Exiting...")
                break

        return str(new_path)


    def generate_command(self) -> list:
        """Return the command for a render job."""

        self.output = utils.sane_path(self.output)

        if not self.settings["overwrite"] and not self.settings["skip_existing"]:
            self.output = self.avoid_overwrite(self.output)

        default_path = os.path.join(
            os.path.dirname(self.recipe["blend_file"]), "render"
        )
        self.output = self.output or default_path

        command = [
            self.settings["blender_bin"],
            "-b",
            self.file,
        ]

        # This needs to be before the rest, so it gets executed
        # first and has a chance to alter the scene
        if self.recipe["use_pre_job_script"]:
            command += ["--python-text", self.recipe["pre_job_script"]]

        command += [
            "-P",
            self.custom_py,
            "-S",
            self.recipe["scene"],
        ]

        if self.use_turbotools:
            return command
        else:
            command += [
                "-t",
                str(self.recipe["threads"]),
                "-o",
                self.output,
                "-j",
                str(self.recipe["frame_jump"]),
            ]

        # Always add extension
        command += ["-x", "1"]

        if self.recipe["format"]:
            command += ["-F", str(self.recipe["format"])]

        if self.recipe["animated"] and not self.recipe["split_frames"]:
            command += [
                "-s",
                str(self.recipe["frame_start"]),
                "-e",
                str(self.recipe["frame_end"]),
                "-a",
            ]
        else:
            command += ["-f", self.recipe["frames"].strip()]

        return command


    def setup(self) -> None:
        """Prepare enviroment and run render job for rendering."""

        use_log = self.settings["write_log"]
        self.log_path = self.stdout_path()
        self.log_handler = open(self.log_path, "w")

        self.custom_py = self.generate_custom_py()
        cmd = self.generate_command()

        log.debug(f"Running job #{self.id}")
        log.debug(f'Blend file is {self.recipe["blend_file"]}')
        log.debug(f'Output file is {self.recipe["output"]}')
        log.debug(f"Generated command is {cmd}")

        if use_log:
            self.write_log_header()

        log.debug("Running pre-job hook.")
        utils.run_hooks(self.hooks["PRE_JOB"], self.blender_bin, self.blendfile)

        self.start_timer()
        self.proc = subprocess.Popen(cmd, stdout=self.log_handler, 
                                     stderr=self.log_handler, 
                                     bufsize=1024 ** 2, text=True)

        self.parser = Parser(self.engine)

        if self.recipe['animated']:
            self.parser.set_animation(self.recipe["frame_start"],
                                      self.recipe["frame_end"])



    def strip_frame_number(self) -> None:
        """Remove frame number from final file."""

        p = Path(self.output)
        anim = self.recipe["animated"]
        frame = self.recipe["frame_start" if anim else "frames"]

        try:
            ext = utils.determine_extension(self.recipe['format'])  # ext debe incluir el punto, p.ej. '.png'
        except KeyError:
            log.error(f'Uknown file format: {self.recipe["format"]}')
            return

        # Si la salida ya tiene sufijo, trabajamos sobre esa ruta; si no, añadimos número+ext
        if p.suffix:
            filename = str(p)
        else:
            filename = f'{self.output}{frame:>04}{ext}'

        # Eliminar un ".<digitos>" justo antes de la extensión (maneja cualquier longitud de dígitos)
        pattern = rf'\.\d+(?={re.escape(ext)}$)'
        fixed_name = re.sub(pattern, '', filename)

        log.debug(f'Renaming {filename} to {fixed_name}')

        try:
            Path(filename).rename(fixed_name)
        except BaseException as e:
            log.debug(f'Failed to rename: {e}')


    def on_finished(self) -> None:

        log.debug(f"Job #{self.id} finished running. Result: {self.status}")

        if self.log_handler:
            self.log_handler.close()

        if self.status == Status.FINISHED:
            if not self.recipe["animated"]:
                try:
                    if self.clean_output and self.settings["use_rename"]:
                        self.strip_frame_number()
                except FileNotFoundError:
                    log.debug("Got file not found from strip_frame_number.")
                    log.debug("Is overwrite disabled?")

            log.debug("Running post-job hook.")
            utils.run_hooks(self.hooks["POST_JOB"], self.blender_bin, self.blendfile)


    def poll(self) -> None:
        """Get progress on render job."""

        assert self.proc is not None
        assert self.parser is not None

        # In the odd case poll() is called again after returning
        # finished, cancelled or failed.
        if self.status not in (Status.WAITING, Status.RUNNING):
            return

        match self.proc.poll():
            case None if self.progress == 100:
                log.debug("Renderjob finished succesfully.")
                self.on_stopped(Status.FINISHED)

                # Sometimes Blender doesn't quit after rendering because some
                # addon leaves it hanging so we have to take drastic measures
                if self.proc.poll() != 0:
                    self.proc.kill()

            case None:
                self.status = Status.RUNNING

                with open(self.log_path, "r") as stream:
                    if not stream:
                        return

                    try:
                        line = list(stream)[-1]
                    except IndexError:
                        return
                
                    for l in list(stream):
                        if l.strip().lower() == 'blender quit':
                            self.on_stopped(Status.FINISHED)
                            return

                parsed = self.parser.update(line)

                self.progress = max(self.progress, parsed.progress)
                self.from_engine = parsed.to_dict()


            case 0:
                log.debug("Renderjob finished succesfully.")
                self.on_stopped(Status.FINISHED)

            case -9:
                log.debug("Render job was cancelled.")
                self.on_stopped(Status.CANCELLED)

            case _ if self.progress == 100:
                log.debug("Renderjob finished succesfully.")
                self.on_stopped(Status.FINISHED)

            case _:
                log.debug("Render job failed.")

                is_error = not os.path.isfile(self.output)
                self.on_stopped(Status.FAILED if is_error else Status.FINISHED)
                self.messages = ["Blender exited with an error.", "Please check the logs."]


    def cancel(self) -> None:
        """Kill the render job."""

        if self.proc:
            self.proc.kill()

        self.on_stopped(Status.CANCELLED)
