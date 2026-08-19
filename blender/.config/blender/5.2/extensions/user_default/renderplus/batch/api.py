# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright Diego Gangl
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

"""API requests for the batch server."""


import sys
import requests
import subprocess
import time
import socket
from shutil import which
from functools import partial

from ..single import utils
from typing import Dict, Union
import json


# The server process
proc: None | subprocess.Popen = None

# Port to connect
port: None | int = None

# IP/Hostname of the batch server
address: None | str = None


def start_server(use_term: bool, use_log: bool, use_clear: bool, log: str) -> None:
    """Start the batch server."""

    global proc

    cmd = [
        sys.executable,
        utils.path("server", "__main__.py"),
        "--port",
        str(port),
    ]

    if not use_clear:
        cmd += ["--no-cleanup"]

    if use_log:
        cmd += ["--write-log", log]

    if use_term:
        prefs = utils.prefs()
        term = prefs.term_path or utils.default_terminal()
        rest = ' '.join(cmd[2:])

        # We have to convert it to a string to the string from
        # the preferences works as expected. We also wrap everything
        # in double quotes because Windows/MacOS
        if utils.sys == "Darwin":
            cmd = (
                f'{term} {cmd[0]} \\"{cmd[1]}\\" {rest}"\''  # noqa
            )
        elif utils.sys == "Windows":
            # noqa
            cmd = f'{term} "{cmd[0]}" "{cmd[1]}" {rest}'  # noqa
        else:
            string_cmd = ' '.join(cmd)
            cmd = f'{term} "{string_cmd}"'

    proc = subprocess.Popen(cmd, shell=use_term)

    # Wait for server to start
    while not socket_busy():
        time.sleep(0.1)


def is_local() -> bool:
    """Determine whether the batch server is in localhost."""

    return address in {"localhost", "127.0.0.1"}


def blender_bin_ok(path: str) -> bool:
    """Test if local blender binary is correct."""

    if not path:
        return True
    else:
        return which(path) is not None


def socket_busy() -> bool:
    """Check if the socket is busy."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((address, port))
    sock.close()

    return result == 0


def request(
    route: str, method: str, data: bytes = None
) -> Union[Dict, requests.Response]:
    """Run a request against the server."""

    url = f"http://{address}:{port}/{route}"
    timeout = 5

    if method == "GET":
        response = requests.get(url, timeout=timeout)
    elif method == "POST":
        response = requests.post(url, json=data, timeout=timeout)
    else:
        response = requests.delete(url, timeout=timeout)

    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        return response


def send_file(filepath: str) -> requests.Response:
    """Send a blendfile to the batch server."""

    url = f"http://{address}:{port}/batch/file/"
    the_file = {"file": open(filepath, "rb")}

    response = requests.post(url, files=the_file, timeout=10)
    return response


def stop() -> None:
    """Stop the server when running locally."""

    if proc:
        proc.terminate()


submit = partial(request, "batch/recipe", "POST")
start = partial(request, "batch/start", "GET")
cancel = partial(request, "batch", "DELETE")
cancel_job = partial(request, "batch/jobs/current", "DELETE")
poll = partial(request, "batch", "GET")
poll_job = partial(request, "batch/jobs", "GET")
upload_urls = partial(request, "batch/upload_urls", "GET")
poll_name = partial(request, "batch/name", "GET")
