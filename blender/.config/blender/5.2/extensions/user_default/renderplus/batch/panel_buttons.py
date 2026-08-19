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

from .panel_base import RP_PT_SubPanel
from . import state


class RP_PT_BatchButtons(RP_PT_SubPanel):
    """Panel to start batch"""

    bl_label = "Start Batch"
    bl_options = {"HIDE_HEADER"}

    @classmethod
    def poll(self, context):
        return len(context.scene.renderplus.batch.jobs) > 0

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.separator()

        match state.mode:
            case "NORMAL":
                split = layout.split(factor=0.9, align=True)
                col = split.column(align=True)

                col.scale_y = 1.2
                col.operator("renderplus.batch_start")

                col = split.column(align=True)
                col.scale_y = 1.2
                col.operator(
                    "renderplus.batch_toggle_mode", text="", icon="PREFERENCES"
                ).mode = "SETTINGS"
            case "SETTINGS":
                row = layout.row()
                row.scale_y = 1.2
                row.operator(
                    "renderplus.batch_toggle_mode",
                    text="Show batch list",
                    icon="LOOP_BACK",
                )
