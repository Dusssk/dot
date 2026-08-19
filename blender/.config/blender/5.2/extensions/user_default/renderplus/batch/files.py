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

"""Functions to handle and send blendfiles."""

import bpy

import os
import glob
import logging
import subprocess

from ..server import utils


log = logging.getLogger(__name__)

# Directory this file is in
CURRENT_DIR = os.path.dirname(__file__)

# Temporary directory for packed blendfiles
TEMP_DIR = os.path.join(CURRENT_DIR, "temp")


def get_name(filepath: str) -> str:
    """Get the filename of filepath."""

    return os.path.split(filepath)[1]


def tmp_map(jobs: list) -> dict[str, str]:
    """Find blend files that need to be packed and uploaded."""

    result = {}
    temp_path = utils.temp_path()

    blends = set(
        [job.blend_file if job.use_external else bpy.data.filepath
         for job in jobs if job.enabled])

    for blend in blends:
        result[blend] = os.path.join(temp_path, os.path.basename(blend))

    return result


def blends_in_recipe(jobs: list[dict]) -> set[str]:
    """Find blendfiles in a recipe."""

    blends = [j['blend_file'] for j in jobs if j['enabled']]
    return set(blends)


def deep_pack(filepath: str) -> None:
    """ Deep-pack asssets linked to the loaded blend.

    Note: This function is meant to be run from the CLI, not from the addon
    """

    bpy.ops.object.make_local(type='ALL')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=filepath, check_existing=False)


def pack(filepath: str, destination: str) -> None:
    """Pack blendfile and save to temp folder."""

    cmd = [
        bpy.app.binary_path,
        "-b",
        filepath,
        "--python-expr",
        f"from bl_ext.user_default.renderplus.batch.files import deep_pack; deep_pack('{destination}')"
    ]

    log.debug(f"Packing {filepath} with command {cmd}")

    try:
        subprocess.run(cmd, timeout=10)
    except subprocess.TimeoutExpired:
        log.error(f"Failed to pack blend file {filepath}")
