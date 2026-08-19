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

"""Batch rendering state."""

# Hold the return value of poll requests to the server
reply = None

# Holds the last reply to check for a stuck server
last_reply = None

# Number of times we got the same reply (check for a stuck server)
same_replies = 0

# Flag for when the server get stuck
server_stuck = False

# Hold the result of the last batch (for log mode)
last_batch = None

# Flag for the different UI modes in the batch panel
mode = "NORMAL"

# Flag when a external blend file can't be read
external_error = False

# Name of the blendfile currently being packed
packing_file = ""

# Flag to cancel packing/upload
packing_cancel = False

# Process for the file packing
packing_proc = None
