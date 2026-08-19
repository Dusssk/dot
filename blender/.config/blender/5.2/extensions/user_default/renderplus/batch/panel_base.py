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

"""Panels and menus for the batch rendering panel."""

from bpy.types import Panel
from . import state


class RP_PT_SubPanel(Panel):
    """Basic sub panel type"""

    bl_label = "Panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"
    bl_parent_id = "RP_PT_Batch"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        return state.mode == "NORMAL" and len(context.scene.renderplus.batch.jobs) > 0

    def draw_header(self, context):
        self.layout.label(text="", icon="SCENE_DATA")
