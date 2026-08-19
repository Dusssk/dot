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

"""
    Render+ Batch Server

    This script runs batches of render jobs in Blender.
"""

import sys
import subprocess
import os
import json
import logging
import threading
import socket
import configparser

from argparse import ArgumentParser, Namespace
from typing import List
import urllib.request
from pathlib import Path, PureWindowsPath

import bottle
from bottle import run, get, post, delete, response, request

import utils
import rss
from config import Config

from batch import Batch, Status


log = logging.getLogger("batch")
batch = Batch()
config = None

# ------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------


def get_args(args: List) -> Namespace:
    """Set and parse command line parameters."""

    parser = ArgumentParser(description="Render+ Batch rendering server.")

    parser.add_argument(
        "--port",
        type=int,
        default=7777,
        metavar="(>1024)",
        help=("Change port to use when running server. " "Default is 7777"),
    )

    parser.add_argument(
        "--list-gpus",
        type=str,
        help=("List available GPUs (needs a Blender " "binary file)"),
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't clean up temp folder after running.",
    )

    parser.add_argument("--write-log", type=str, help="Write a log in the logs folder.")
    parser.add_argument("--config", type=str, help="Load a configuration file")

    parser.add_argument(
        "--version", action="version", version="Render+ Batch Server 3.0"
    )

    return parser.parse_args(args)


def setup_log(write: str) -> str | None:
    """Setup logging."""

    log.setLevel(logging.DEBUG)
    log.propagate = False

    file_format = logging.Formatter(
        ("[%(levelname)s][%(asctime)s] -> " "%(message)s \t (%(filename)s:%(lineno)d)")
    )

    cli_format = logging.Formatter(
        ("[%(levelname)s] -> " "%(message)s \t (%(filename)s:%(lineno)d)")
    )

    handler = logging.StreamHandler()
    handler.setFormatter(cli_format)
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)

    if write:

        log_name = f"renderplus_server_{utils.stamp_suffix()}.log"
        log_path = os.path.join(os.path.dirname(write), log_name)

        try:
            handler = logging.FileHandler(log_path)
            handler.setFormatter(file_format)
            handler.setLevel(logging.DEBUG)
            log.addHandler(handler)

            return log_path

        except (PermissionError, FileNotFoundError) as e:
            print(f"[ERROR] Could not write log file {log_path}\n{e}")


# ------------------------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------------------------


def send_request(port: int, route: str, method: str) -> bytes:
    """Make a request to server."""

    url = f"http://localhost:{port}/{route}"
    req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req) as stream:
            return stream.read()
    except urllib.error.HTTPError as e:
        print(f"Server replied with status: {e.code} {e.reason}")
    except urllib.error.URLError:
        print("Conection refused. Is the server running?")


def print_request(port: int, route: str) -> None:
    """Make a request to the server and print the result."""

    try:
        print(send_request(port, route).decode())
    except AttributeError:
        return


def error(code: int, msg: str) -> response:
    """Return an error response."""

    response.set_header("Content-type", "application/json")
    response.status = code

    return json.dumps({"status": msg})


def print_GPUs(binary: str) -> None:
    """Run Blender with a custom script to show available GPUs."""

    script = os.path.join(os.path.dirname(__file__), "list_gpus.py")

    command = [
        binary,
        "-b",
        "-P",
        script,
    ]

    subprocess.run(command)


# ------------------------------------------------------------------------------
# GET ROUTES
# ------------------------------------------------------------------------------
@get("/batch")
def get_batch():
    """Return batch information."""

    if batch.status != Status.RUNNING and not batch.jobs:
        return error(409, "Not running a batch right now")

    data = {
        "status": batch.status.name,
        "times": batch.times,
        "stats": batch.stats,
        "messages": [],
        "jobs": batch.jobs_info(),
    }

    return data


@get("/test")
def test():
    """Return server information."""

    log.debug("Recieved /test from %s", request.remote_addr)

    return {"version": "3.0"}


@get("/batch/ready")
def ready():
    """Determine if the server is ready to run a batch."""

    log.debug("Recieved /batch/ready from %s", request.remote_addr)
    output = {}

    if batch.status == Status.RUNNING:
        return error(401, "Still running a batch")

    output['main'] = {"status": "READY"}
    output['workers'] = batch.check_all_workers()

    return output


@get("/config")
def config():
    """Determine if the server is ready to run a batch."""

    log.debug("Recieved /config from %s", request.remote_addr)

    output = {
        'port': config.port,
        'disable_workers': config.disable_workers,
        'cleanup': config.cleanup,
        'workers': {}
    }

    for w in config.workers:
        output['workers'][w.name] = {
            'address': w.address,
            'port': w.port,
            'poll_interval': w.poll_interval,
        }

    return output


@get("/batch/rss")
def feed():
    """Determine if the server is ready to run a batch."""

    log.debug("Recieved /batch/rss from %s", request.remote_addr)

    if batch.jobs:
        response.set_header("Content-type", "application/rss+xml")
        response.status = 200

        return rss.generate(batch.jobs_info(), batch.name)
    else:
        return error(409, "Not running a batch right now")


@get("/batch/upload_urls")
def remote_urls():
    """Determine if the server is ready to run a batch."""

    log.debug("Recieved /batch/upload_urls from %s", request.remote_addr)

    if batch.jobs:
        return batch.upload_urls()
    else:
        return error(409, "Not running a batch right now")


@get("/batch/start")
def start():
    """Start a batch render."""

    log.debug("Recieved /batch/start from %s", request.remote_addr)

    if batch.jobs:
        log.debug("Starting Batch")
        t = threading.Thread(target=batch.run)
        t.start()

        response.status = 201
        return {"status": "Batch Started"}

    else:
        return error(409, "Never received a recipe")


@get("/batch/jobs/<index:int>")
def job_data(index: int):
    """Get information on a render job."""

    log.debug("Recieved /batch/jobs from %s", request.remote_addr)

    if batch.status != Status.RUNNING and not batch.jobs:
        return error(409, "No Batch has been run")

    try:
        data = batch.jobs[index].to_dict()
    except IndexError:
        return error(409, f"Can't find job {index}")

    response.status = 201
    return data


@get("/batch/name")
def name():
    """Get batch name."""

    log.debug("Recieved /batch/name from %s", request.remote_addr)

    if batch.name:
        response.set_header("Content-type", "application/json")
        return {"name": batch.name}
    else:
        return error(409, "No Batch has been run")


@get("/batch/upload_urls")
def upload_urls():

    log.debug("Recieved /batch/upload_urls from %s", request.remote_addr)

    if batch.jobs:
        return batch.upload_urls()
    else:
        return error(409, "Never received a recipe")


# ------------------------------------------------------------------------------
# POST ROUTES
# ------------------------------------------------------------------------------
@post("/batch/recipe")
def submit():
    """Submit a batch recipe."""

    log.debug("Recieved a recipe from %s", request.remote_addr)

    content_type = request.get_header("Content-type")

    if content_type != "application/json":
        log.debug(f"Recieved a bad content-type for POST: {content_type}")
        return error(406, "Content-type must be Json")

    if batch.status == Status.RUNNING:
        return error(409, "Already running a batch")

    post_data = request.body.read()
    batch.set_recipe(json.loads(post_data))

    response.status = 201
    return {"status": "Received Recipe"}


@post("/batch/file/")
def upload_file():
    """Receive a file to render."""

    log.debug("Receiving a file from %s", request.remote_addr)

    if not batch.jobs:
        return error(409, "Haven't received a recipe yet")

    if batch.status == Status.RUNNING:
        return error(409, "Already running a batch")

    upload = request.files.get("file")
    name, ext = os.path.splitext(upload.filename)

    if ext != ".blend":
        return error(406, "File extension not allowed.")

    # Appends upload.filename automatically
    saved = os.path.join(batch.temp, upload.filename)
    upload.save(saved, overwrite=True)

    # Change the job to point to this file
    batch.replace_filepath(upload.filename, saved)
    response.status = 201

    return {"status": f"Received file of {upload.content_length} bytes. Stored at {saved}"}


# ------------------------------------------------------------------------------
# DELETE ROUTES
# ------------------------------------------------------------------------------
@delete("/batch")
def cancel():
    """Cancel a batch."""

    log.debug("Recieved DELETE /batch from %s", request.remote_addr)

    if batch.status != Status.RUNNING:
        return error(409, "Not running a batch right now")

    batch.cancel()

    response.status = 200
    return {"status": "Cancelled Batch"}


@delete("/batch/jobs/<index:int>")
def cancel_job(index: int):
    """Cancel the currently running job."""

    log.debug("Recieved DELETE /batch/jobs from %s", request.remote_addr)

    if batch.status != Status.RUNNING:
        return error(409, "Not running a batch right now")

    batch.cancel_job(index)

    response.status = 200
    return {"status": "Cancelling job"}


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------


def public_ip() -> str:
    """Get network IP for this machine."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Doesn't even have to be reachable
        sock.connect(("10.255.255.255", 1))
        ip = sock.getsockname()[0]

    except Exception:
        ip = "-----"

    finally:
        sock.close()

    return ip


def main() -> None:
    """Parse arguments, load recipes and run batch."""

    global config, batch

    args = get_args(sys.argv[1:])
    config = Config.from_ags(args)
    setup_log(config.log_path)

    if config.list_gpus:
        print_GPUs(args.list_gpus)
        return

    batch.set_config(config)

    # Increase max accepted file size to 1GB
    bottle.BaseRequest.MEMFILE_MAX = 1024**3
    host = socket.gethostname()

    print("\n🚀 Render+ Batch Server Started")
    print(f"   >> Serving on {host} (127.0.0.1)")
    print(f"   >> Network ip is {public_ip()}")
    print(f"   >> Using port {config.port}")

    if config.log_path:
        print(f"   >> Writing logs to {config.log_path}")

    if not config.cleanup:
        print(f"   >> Not cleaning up temp files")

    print("   >> Press CTRL+C to quit\n")
    print('-' * 80)

    if config.log_path:
        log.info("Writing logs into %s", config.log_path)

    run(host="0.0.0.0", port=config.port, quiet=True)
