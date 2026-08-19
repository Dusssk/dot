# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright (C) 2018 Diego Gangl
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


import time
import logging
import csv

import bpy

from . import utils


log = logging.getLogger(__name__)


times = {
    "start": -1,
    "last_frame": -1,
    "frame_start": -1,
    "frames": [],
    "running": False,
}


def start() -> None:
    """Start timer for stats."""

    times["start"] = time.time()
    times["running"] = True
    times["frame_start"] = bpy.context.scene.frame_current
    log.debug(f'Stats started at {times["start"]}.')


def reset() -> None:
    """Reset stats."""

    settings = bpy.context.scene.renderplus.stats

    settings.total = 0
    settings.average = 0
    settings.slowest = (0, 0)
    settings.fastest = (0, 0)

    times["start"] = -1
    times["last_frame"] = -1
    times["frames"] = []


def is_animation() -> bool:
    """Detect if we are rendering an animation."""

    return len(times["frames"]) > 1


def remaining() -> float:
    """Estimate remaining time for animation renders."""

    scene = bpy.context.scene

    avg = sum(times["frames"]) / len(times["frames"])
    remaining = avg * (scene.frame_end - scene.frame_current)

    log.debug(f"Remaining time: {remaining}")
    return remaining


def average_frame() -> float:
    """Calculate average frame render time."""

    avg = sum(times["frames"]) / len(times["frames"])
    log.debug(f"Average rendertime: {avg}")

    return avg


def slowest_frame() -> float:
    """Calculate slowest frame rendertime."""

    rendertime = max(times["frames"])
    index = times["frames"].index(rendertime) + times["frame_start"]

    log.debug(f"Slowest frame time: {rendertime}")
    log.debug(f"Slowest frame: {index}")

    return rendertime, index


def fastest_frame() -> float:
    """Calculate slowest frame rendertime."""

    rendertime = min(times["frames"])
    index = times["frames"].index(rendertime) + times["frame_start"]

    log.debug(f"Fastest frame time: {rendertime}")
    log.debug(f"Fastest frame: {index}")

    return rendertime, index


def stop() -> None:
    """Stop the stats and calculate."""

    settings = bpy.context.scene.renderplus.stats

    settings.total = time.time() - times["start"]
    log.debug(f"Total Rendertime: {settings.total}")

    if is_animation():
        settings.slowest = slowest_frame()
        settings.fastest = fastest_frame()
        settings.average = average_frame()

        if settings.save_file:
            export_csv(f"{bpy.data.filepath}_stats.csv")

    times["running"] = False
    log.debug("Stats stopped.")


def update_frame() -> None:
    """Update the current frame rendertime."""

    settings = bpy.context.scene.renderplus.stats

    current_time = time.time() - (
        times["last_frame"] if times["frames"] else times["start"]
    )

    times["frames"].append(current_time)
    times["last_frame"] = time.time()

    log.debug(f"Updating frame time: {current_time}")

    if is_animation():
        settings.remaining = remaining()


def export_csv(filepath: str) -> None:
    """Export stats data to a csv file."""

    settings = bpy.context.scene.renderplus.stats
    fastest_time = utils.time_format(settings.fastest[1])
    slowest_time = utils.time_format(settings.slowest[1])

    fastest = f"{settings.fastest[0]} (#{fastest_time})"
    slowest = f"{settings.slowest[0]} (#{slowest_time})"

    with open(filepath, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Frame", "Time"])

        [
            writer.writerow([i, utils.time_format(f)])
            for i, f in enumerate(times["frames"])
        ]

        writer.writerow(["Fastest", fastest])
        writer.writerow(["Slowest", slowest])
        writer.writerow(["Average", utils.time_format(settings.average)])
        writer.writerow(["Total", utils.time_format(settings.total)])
