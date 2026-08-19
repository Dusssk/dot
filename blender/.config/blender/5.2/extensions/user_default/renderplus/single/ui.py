# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright (C) 2014 Diego Gangl
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

"""Main user interface."""

import logging

import bpy
from bpy.types import Operator, Menu, Panel

from . import utils
from . import stats
from . import notifications


log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
#  Help
# -----------------------------------------------------------------------------


class RP_OT_ShowHelp(Operator):
    """Call a popup with tips and help."""

    bl_idname = "renderplus.help"
    bl_label = "Render+ Help"

    section: bpy.props.EnumProperty(
        items=(("ACTIONS", "", ""), ("CUSTOM_OVERRIDES", "", ""))
    )

    def execute(self, context):
        if self.section == "ACTIONS":
            message = (
                "Settings can be found in bpy.context.scene.renderplus."
                " Actions will be disabled when opening a file for"
                "security reasons. Use Absolute Paths and remember to"
                " be careful :)"
            )

            pop = utils.popup("Tip", message)
            pop.icon = "HELP"
            pop.show()

        elif self.section == "CUSTOM_OVERRIDES":
            message = (
                "You can use this section to override any data"
                "in the scene. Add the full datapath below (starting"
                "from bpy.context.scene), and the value to it change"
                "to. Note that Render+ does not check types or bounds"
                "on custom values, it will simply use it. Double check"
                "these values before rendering!"
            )

            pop = utils.popup("Custom Overrides", message)
            pop.icon = "HELP"
            pop.link_text = 'More on Data Paths...'
            pop.link_url = 'https://docs.blender.org/api/current/info_api_reference.html#simple-data-access'
            pop.show()

        return {"FINISHED"}


# -----------------------------------------------------------------------------
#  Menu
# -----------------------------------------------------------------------------


class RP_MT_Notifications(Menu):
    """Notification options."""

    bl_label = ""

    def draw(self, context):
        layout = self.layout
        settings = context.scene.renderplus

        if utils.sys != "Windows":
            layout.prop(settings, "notify_desktop")

        layout.prop(settings, "notify_sound")
        layout.prop(settings, "notify_mail")


# -----------------------------------------------------------------------------
#  Panels
# -----------------------------------------------------------------------------


class RP_PT_Main(Panel):
    """Main Panel for Render+."""

    bl_label = "Single Render Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

    def draw(self, context):

        layout = self.layout
        settings = context.scene.renderplus

        # Notifications
        row = layout.row()
        row.label(text="Notifications", icon="LIGHT")
        row.menu("RP_MT_Notifications", text=utils.notification_text(settings))

        if notifications.error:
            row = layout.row()
            row.label(text=notifications.error, icon="ERROR")

        # Power Off
        row = layout.row()
        row.label(text="Power Off", icon="QUIT")
        row.prop(settings, "off_options", text="")

        # Autosave/Autohide
        row = layout.row()
        row.prop(settings, "autosave")
        row = layout.row()
        row.prop(settings, "autohide")

        # Stats
        layout.separator()


class RP_PT_MainStats(Panel):
    bl_label = "Stats"
    bl_parent_id = "RP_PT_Main"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.renderplus
        stats_data = scene.renderplus.stats

        if stats.times["start"] > 0:
            message = "Last Render took "
            message += utils.time_format(stats_data.total)
        else:
            message = "Waiting for the first render"

        if stats.is_animation():
            message = "Rendering..." if stats.times["running"] else message

            layout.row().label(icon="TIME", text=message)

            layout.separator()
            fmt = utils.time_format

            if stats.times["running"]:
                time_remaining = fmt(stats_data.remaining)
                frames = scene.frame_end - scene.frame_current
                remaining = f"{time_remaining} ({frames} frames left)"
            else:
                # Don't show any time when not rendering
                remaining = "Not Rendering"

            layout.row().label(text=f"Remaining: {remaining}", icon="AUTO")

            avg = "Rendering..." if stats.times["running"] else fmt(stats_data.average)

            layout.row().label(text=f"Average time: {avg}", icon="DISK_DRIVE")

            fastest = (
                "Rendering..."
                if stats.times["running"]
                else (
                    f"#{int(stats_data.fastest[1])} at " f"{fmt(stats_data.fastest[0])}"
                )
            )

            layout.row().label(text=f"Fastest frame: {fastest}", icon="ADD")

            slowest = (
                "Rendering..."
                if stats.times["running"]
                else (
                    f"#{int(stats_data.slowest[1])} at " f"{fmt(stats_data.slowest[0])}"
                )
            )

            layout.row().label(text=f"Slowest frame: {slowest}", icon="REMOVE")

        else:
            layout.row().label(text=message, icon="TIME")

        layout.separator()
        layout.row().prop(settings.stats, "save_file")
        layout.separator()
        layout.separator()


class RP_PT_PreRender(Panel):
    bl_label = "Pre-Render Action"
    bl_parent_id = "RP_PT_Main"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene.renderplus, "pre_enabled", text="")

    def draw(self, context):

        layout = self.layout
        settings = context.scene.renderplus

        split = layout.split(align=True, factor=0.3)
        split.column().label(text="Option")
        col = split.column()
        col.enabled = settings.pre_enabled
        col.prop(settings.pre_settings, "option", text="")

        split = layout.split(align=True, factor=0.3)

        if settings.pre_settings.option == "command":
            col = split.column()
            col.enabled = settings.pre_enabled
            col.label(text="Command")

            col = split.column()
            col.enabled = settings.pre_enabled
            row = col.row(align=True)
            row.prop(settings.pre_settings, "command", text="")
        else:
            col = split.column()
            col.enabled = settings.pre_enabled
            col.label(text="Script")

            col = split.column()
            col.enabled = settings.pre_enabled
            row = col.row(align=True)

            row.prop_search(settings.pre_settings, "script", bpy.data, "texts", text="")

        row.operator(
            "renderplus.help", text="", icon="QUESTION", emboss=False
        ).section = "ACTIONS"

        layout.separator()


class RP_PT_PostRender(Panel):
    bl_label = "Post-Render Action"
    bl_parent_id = "RP_PT_Main"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene.renderplus, "post_enabled", text="")

    def draw(self, context):

        layout = self.layout
        settings = context.scene.renderplus

        split = layout.split(align=True, factor=0.3)
        split.column().label(text="Option")
        col = split.column()
        col.enabled = settings.post_enabled
        col.prop(settings.post_settings, "option", text="")

        split = layout.split(align=True, factor=0.3)

        if settings.post_settings.option == "command":
            col = split.column()
            col.enabled = settings.post_enabled
            col.label(text="Command")

            col = split.column()
            col.enabled = settings.post_enabled
            row = col.row(align=True)
            row.prop(settings.post_settings, "command", text="")

        else:
            col = split.column()
            col.enabled = settings.post_enabled
            col.label(text="Script")

            col = split.column()
            col.enabled = settings.post_enabled
            row = col.row(align=True)
            row.prop_search(
                settings.post_settings, "script", bpy.data, "texts", text=""
            )

        row.operator(
            "renderplus.help", text="", icon="QUESTION", emboss=False
        ).section = "ACTIONS"

        layout.separator()
