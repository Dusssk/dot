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

"""Operations that print information or check the enviroment."""

import os
import pprint

import utils
import custom
import job

from typing import Dict


def run(data: Dict) -> None:
    """Print stats, values, commands and exit."""

    pretty_print = pprint.PrettyPrinter(indent=2, width=80)

    print("")
    print("=" * 80)
    print("[Render+] Dry Run")
    print("=" * 80)

    print(f'\nRecipe Info for "{data["name"]}"')
    print("-" * 80)
    print("")

    for key, value in data.items():
        if key != "jobs":
            print(f"- {key}:")
            pretty_print.pprint(value)
            print("")

    print("\n\nRender Jobs")
    print("-" * 80)

    for i, job in enumerate(data["jobs"]):
        print(f"\n- Job #{i}")
        pretty_print.pprint(job)

    print("\n\nRender Job commands")
    print("-" * 80)

    for i, job in enumerate(data["jobs"]):
        print(f"\n- Job #{i}")
        py_path = custom.filepath(data["name"], job["blend_file"])
        cmd = renderjob.command(job, data["blender_bin"], py_path)
        print(" ".join(map(str, cmd)))

    print("")


def check(data: Dict) -> None:
    """Check if commands can be run and files are present."""

    print("")
    print("=" * 80)
    print("[Render+] Recipe Check")
    print("=" * 80)
    print("")

    temp_dir = utils.path("temp")

    temp_ok = "[OK] Batch temp dir found and writeable ({0})"
    temp_not_found = "[ERROR] Batch temp not found ({0})"
    temp_not_writeable = "[ERROR] Batch temp not writeable ({0})"

    found = "[OK] Blend file for job #{1} ({0})"
    not_found = "[ERROR] Can't find Blend file for job #{1} ({0})"
    no_permissions = "[ERROR] Can't open Blend file for job #{1} ({0})"

    # Check batch temp folder
    if os.path.isdir(temp_dir):
        if os.access(temp_dir, os.W_OK):
            print(temp_ok.format(temp_dir))
        else:
            print(temp_not_writeable.format(temp_dir))
    else:
        print(temp_not_found.format(temp_dir))

    # Check Blender binary
    if os.path.isfile(data["blender_bin"]):
        print("[OK] Found Blender binary ({0})".format(data["blender_bin"]))
    else:
        print(
            ("[ERROR] Blender binary not " "found at {0}").format(data["blender_bin"])
        )

    # Check blend file for each job
    for i, job in enumerate(data["jobs"]):
        blendpath = job["blend_file"]

        if os.path.isfile(blendpath):
            if os.access(blendpath, os.R_OK):
                print(found.format(blendpath, i))
            else:
                print(no_permissions.format(blendpath, i))
        else:
            print(not_found.format(blendpath, i))

    print("")
