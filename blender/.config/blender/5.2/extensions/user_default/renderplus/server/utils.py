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

"""Utility functions."""

import os
import datetime
import subprocess
import time
import logging
import pathlib
import tempfile

from typing import Callable, List, Dict, Tuple


log = logging.getLogger("batch.utils")


def path(*paths: str) -> str:
    """Get a path relative to the script."""

    source = pathlib.Path(__file__).parent.absolute()
    return os.path.join(source, *paths)


def sane_path(path: str) -> str:
    """Return a normalized path."""

    return os.path.normpath(os.path.abspath(path))


def temp_path(*paths: str) -> str:
    """Get a path relative to the script."""

    # source = pathlib.Path(__file__).parent.absolute()
    # return os.path.join(source, "temp", *paths)
    return tempfile.mkdtemp(prefix='renderplus_')


def strip_extension(filename: str, OS: str) -> str:
    """Remove extension from filename."""

    if OS == "Windows":
        return pathlib.PureWindowsPath(filename).stem
    else:
        return pathlib.Path(filename).stem


def stamp_suffix() -> str:
    """Create a timestamp to use as suffix for filenames."""

    return datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S")


def format_time(timestamp: float) -> str:
    """Format a delta timestamp into HH:MM:SS.ss."""

    formatted = str(datetime.timedelta(seconds=timestamp))
    return formatted[: formatted.find(".") + 3]


def date_format(timestamp: float) -> str:
    """Formats a date from a timestamp."""

    date = datetime.datetime.fromtimestamp(timestamp)
    return date.strftime("%H:%M:%S - %d/%m/%Y")


def determine_extension(file_format: str) -> str:
    """Get file extension for format."""

    ext = {
        "BMP": ".bmp",
        "IRIS": ".sgi",
        "PNG": ".png",
        "JPEG": ".jpg",
        "JPEG2000": ".jp2",
        "TARGA": ".tga",
        "TARGA_RAW": ".tga",
        "CINEON": ".cin",
        "DPX": ".dpx",
        "OPEN_EXR_MULTILAYER": ".exr",
        "OPEN_EXR": ".exr",
        "HDR": ".hdr",
        "TIFF": ".tif",
    }

    return ext[file_format]


def add_extension(path: str, file_format: str) -> str:
    """Auomatically add extension to path."""

    # If the path already has an extension, just return it
    if "." in path:
        return path

    # Extensions only for still images. Animations
    # don't get their frame number removed.
    ext = {
        "BMP": ".bmp",
        "IRIS": ".sgi",
        "PNG": ".png",
        "JPEG": ".jpg",
        "JPEG2000": ".jp2",
        "TARGA": ".tga",
        "TARGA_RAW": ".tga",
        "CINEON": ".cin",
        "DPX": ".dpx",
        "OPEN_EXR_MULTILAYER": ".exr",
        "OPEN_EXR": ".exr",
        "HDR": ".hdr",
        "TIFF": ".tif",
    }

    try:
        result = pathlib.Path(path).with_suffix(ext[file_format])
    except KeyError:
        result = pathlib.Path(path)

    return str(result)


def strip_frame_number(filepath: str, frame: int) -> None:
    """Remove the frame number suffix added automatically by Blender."""

    # Blender adds the frame number to the end of the filename with
    # four zeroes as padding
    src_path = pathlib.Path(filepath.replace("#", ""))

    # Replace the underscore, but only the last one. We need to
    # reverse the string to do a replace there, and then reverse
    # again to get the original string back.

    target_name = src_path.stem + src_path.suffix
    fixed = f"{src_path.stem}{src_path.suffix}{frame:0>4}"
    realpath = src_path.with_name(fixed)
    rename_path = src_path.with_name(target_name)

    log.debug("Stripping frame number...")
    log.debug(f"Received {filepath}")
    log.debug(f"Target name is {target_name}")
    log.debug(f"Real path is {realpath}")
    log.debug(f"Renaming to {rename_path}")

    try:
        realpath.rename(rename_path)

    except FileExistsError:
        os.remove(src_path)
        realpath.rename(src_path)


def run_hooks(hooks: List, blender_bin: str, blend: str) -> None:
    """Run hooks."""

    def run_hook(hook: Dict) -> None:

        if hook["type"] == "SCRIPT":
            cmd = [
                blender_bin,
                "-b",
                blend,
                "--python-text",
                hook["script"],
            ]
        else:
            cmd = hook["cmd"]

        try:
            log.debug(f"Running Hook: {cmd}")
            subprocess.run(
                cmd,
                check=True,
                shell=(hook["type"] != "SCRIPT"),
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            msg = f'Hook command failed: {e.stderr.decode("utf-8")}'
            log.debug(msg)
            print(msg)

    [run_hook(h) for h in hooks if h["enabled"]]


def timer() -> Tuple[float, Callable]:
    """Take the time to render a job/batch."""

    started = time.time()

    def stop() -> Tuple[float, float]:
        """Stop the timer and return the stopped & elapsed times."""

        stopped = time.time()
        return stopped, (stopped - started)

    return started, stop


def calculate_stats(stats_list: List) -> Dict:
    """Calculate average, slowest and fastest job rendertimes."""

    times = [
        (index, t.time_total) for index, t in enumerate(stats_list) if t.time_total
    ]

    try:
        min_index, min_value = min(times, key=lambda p: p[1])
        max_index, max_value = max(times, key=lambda p: p[1])
        avg = sum([t[1] for t in times]) / len(times)

        return {
            "average_time": avg,
            "slowest_job": max_index,
            "slowest_time": max_value,
            "fastest_job": min_index,
            "fastest_time": min_value,
        }

    except ValueError:
        return {
            "average_time": None,
            "slowest_job": None,
            "slowest_time": None,
            "fastest_job": None,
            "fastest_time": None,
        }
