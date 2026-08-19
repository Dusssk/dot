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

"""Script to pack all files into a new blendfile."""

import sys
import bpy
import time

time.sleep(5)

# Get args after --
# We expect a filepath here
argv = sys.argv
args = argv[argv.index("--") + 1 :]

# If there's not filepath, leave with an error code
if not args:
    raise SystemExit(1)

try:
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=args[0], check_existing=False)

except RuntimeError:
    pass
