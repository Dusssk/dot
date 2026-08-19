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

import os
import unittest
import batch
import renderjob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class TestRecipeLoading(unittest.TestCase):

    def test_nojobs(self):
        filepath = os.path.join(BASE_DIR, "recipe_no_jobs.json")

        with self.assertRaises(SystemExit):
            batch.load_recipe(filepath)

    def test_goodfile(self):
        filepath = os.path.join(BASE_DIR, "recipe_good.json")

        data = batch.load_recipe(filepath)
        self.assertIsInstance(data, dict)
        self.assertEqual(len(data["jobs"]), 2)


class TestCommandBuilding(unittest.TestCase):

    def test_command(self):
        blender_bin = "/usr/bin/blender"

        job = {
            "scene": "my_scene",
            "blend_file": "my_blend.blend",
            "output": "my_output",
            "frame_still": "120",
            "frame_start": "1",
            "frame_end": "200",
            "animated": False,
            "format": "PNG",
            "threads": 0,
        }

        cmd = renderjob.command(job, blender_bin, "[PY]")

        expected = (
            "/usr/bin/blender -b my_blend.blend -P [PY] -S my_scene"
            " -t 0 -x 0 -o my_output -F PNG -f 120"
        )
        cmd_str = " ".join(map(str, cmd))

        self.assertEqual(cmd_str, expected)


if __name__ == "__main__":
    unittest.main()
