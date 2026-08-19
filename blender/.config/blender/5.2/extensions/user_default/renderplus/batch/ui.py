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

import bpy
from bpy.types import UIList, UILayout, Menu, Panel, PropertyGroup, ViewLayer, Scene

from ..single import utils
from . import data
from . import state
from . import recipe
from . import quick


# -----------------------------------------------------------------------------
#  UI Lists
# -----------------------------------------------------------------------------


class RP_UL_Batch(UIList):
    """UI list for batch jobs."""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):

        if item.animation:
            job_icon = "RENDER_ANIMATION"
        else:
            job_icon = "RENDER_STILL"

        layout.operator(
            "renderplus.toggle_render_job", emboss=False, text="", icon=job_icon
        ).index = index

        layout.prop(item, "name", text="", emboss=False, icon="NONE")

        if item.use_external:
            layout.label(text="", icon="FILE_BLEND")

        if state.mode == "RUNNING":
            try:
                job_state = state.reply["jobs"][index]["status"]

                if job_state == "FINISHED":
                    icon = "CHECKBOX_HLT"
                elif job_state == "QUEUED":
                    icon = "TIME"
                elif job_state == "RUNNING":
                    icon = "PREFERENCES"
                elif job_state == "FAILED":
                    icon = "ERROR"
                elif job_state == "CANCELLED":
                    icon = "X"
                elif job_state == "DISABLED":
                    icon = "REMOVE"

                layout.label(text="", icon=icon)
            except TypeError:
                pass
        else:
            layout.prop(item, "enabled", text="", index=index)


class RP_UL_BatchLogs(UIList):
    """UI list to show batch logs."""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):

        if item.animation:
            job_icon = "RENDER_ANIMATION"
        else:
            job_icon = "RENDER_STILL"

        job = context.scene.renderplus.batch.jobs[index]
        job_status = state.last_batch["jobs"][index]

        if job_status["status"] == "DISABLED":
            icon = "REMOVE"
        elif job_status["status"] == "FAILED":
            icon = "ERROR"
        else:
            icon = "TIME"

        layout.label(text=job.name, icon=job_icon)
        layout.label(text="", icon=icon)


class RP_UL_BatchOverrides(UIList):
    """Custom UI list for custom overrides."""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):

        layout.prop(item, "name", text="", emboss=False)
        layout.prop(item, "enabled", text="", index=index)


# -----------------------------------------------------------------------------
#  Menus
# -----------------------------------------------------------------------------


class RP_MT_BatchNotifications(Menu):
    """Notification options."""

    bl_label = ""

    def draw(self, context):
        layout = self.layout
        settings = context.scene.renderplus.batch

        if utils.sys != "Windows":
            layout.prop(settings, "notify_desktop")

        layout.prop(settings, "notify_sound")
        layout.prop(settings, "notify_mail")


class RP_MT_BatchOps(Menu):
    """Menu for extra options in render jobs list."""

    bl_label = ""

    def draw(self, context):
        layout = self.layout

        layout.operator(
            "renderplus.new_render_job", icon="NODE_COMPOSITING", text="Duplicate"
        ).duplicate = True

        layout.operator(
            "renderplus.add_external_render_jobs",
            icon="FILE_BLEND",
            text="Add external blends",
        )

        layout.operator(
            "renderplus.batch_toggle_mode", icon="NLA", text="Change output paths"
        ).mode = "OUTPUT_CHANGE"

        layout.separator()

        layout.operator(
            "renderplus.move_render_job", icon="TRIA_UP_BAR", text="Move to Top"
        ).direction = "TOP"
        layout.operator(
            "renderplus.move_render_job", icon="TRIA_DOWN_BAR", text="Move to Bottom"
        ).direction = "BOTTOM"
        layout.separator()

        layout.operator(
            "renderplus.batch_toggle", icon="RESTRICT_VIEW_OFF", text="Enable All"
        ).enable = True
        layout.operator(
            "renderplus.batch_toggle", icon="RESTRICT_VIEW_ON", text="Disable All"
        ).enable = False

        layout.operator(
            "renderplus.copy_settings", icon="NLA", text="Copy Settings to other jobs"
        )


        layout.separator()


        layout.operator(
            "renderplus.delete_render_job", icon="REMOVE", text="Remove all render jobs"
        ).clear = True

        layout.separator()

        row = layout.row()
        row.enabled = state.last_batch is not None
        row.operator(
            "renderplus.batch_toggle_mode",
            icon="PREVIEW_RANGE",
            text="Previous Batch Results",
        ).mode = "LOG"

        if utils.sys == "Windows":
            layout.separator()
            layout.operator(
                "renderplus.generate_script",
                icon="PREFERENCES",
                text="Generate BAT files for batch",
            )

        layout.separator()

        layout.operator("renderplus.apply_render_job", icon="PROPERTIES")


class RP_MT_CustomOverridePresets(Menu):
    bl_label = "Custom Overrides Presets"
    preset_subdir = "renderplus/overrides"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


# -----------------------------------------------------------------------------
#  Panel
# -----------------------------------------------------------------------------
def check_viewlayer(scene: Scene, layer: ViewLayer) -> bool:
    """Check if there's a render layer node."""

    problem = False

    if layer and scene.compositing_node_group.nodes:
        for node in scene.node_tree.nodes:
            if node.bl_idname == "CompositorNodeRLayers":
                problem = node.layer != layer

    return problem


def item(layout: UILayout, text: str, text2: str) -> UILayout:
    """Status items for running state."""

    split = layout.split(factor=0.4)
    split.column().label(text=text, icon="REMOVE")

    col = split.column()
    col.alignment = "RIGHT"
    col.label(text=str(text2))

    return split


def empty_state(layout: UILayout) -> None:
    """Layout for the emtpy state of the batch list."""

    layout.separator()
    row = layout.row()
    row.enabled = False
    row.operator(
        "renderplus.new_render_job", text="The batch list is empty", emboss=False
    )

    layout.separator()
    row = layout.row()
    row.scale_y = 1.2
    row.operator("renderplus.new_render_job", text="Add a new render job").duplicate = (
        False
    )

    row = layout.row()
    row.scale_y = 1.2
    op = row.operator("renderplus.batch_toggle_mode", text="Quick Batch")
    op.mode = "QUICK_BATCH"

    layout.separator()


def packing_state(layout: UILayout) -> None:
    """Layout when packing files."""

    layout.separator()
    layout.row().label(text="Sending Files", icon="EXPORT")
    layout.separator()

    box = layout.box()
    col = box.column(align=True)
    col.label(text="Packing and sending blendfiles to the server")
    col.label(text="(this could take a while)")
    col.separator()

    if state.packing_file:
        col.separator()
        col.label(text=state.packing_file, icon="BLENDER")
        col.separator()

    layout.separator()
    row = layout.row()
    row.scale_y = 1.1
    row.operator("renderplus.batch_cancel_packing")

    layout.separator()


def action_prop(layout: UILayout, prop, position: str) -> None:
    """Layout to set a batch action."""

    layout.row().prop(prop, "enabled", text=position)

    col = layout.column(align=True)
    col.enabled = prop.enabled
    prop_selector = "command" if prop.kind == "CMD" else "script"
    prop_icon = "CONSOLE" if prop.kind == "CMD" else "SCRIPTPLUGINS"

    col.prop(prop, prop_selector, icon=prop_icon)
    col.prop(prop, "kind")

    layout.separator()


def settings_state(layout: UILayout) -> None:
    """Layout for batch settings."""

    settings = bpy.context.scene.renderplus
    network = utils.prefs().batch_server_location == "NETWORK"

    row = layout.row()
    box = row.box()
    box.label(text="Batch Settings", icon="PREFERENCES")
    layout.separator()

    layout.row().prop(settings.batch, "ui_settings_tab", expand=True)
    layout.separator()

    if settings.batch.ui_settings_tab == "GENERAL":
        split = layout.split(factor=0.5)
        col = split.column(align=False)

        col.prop(settings.batch, "use_global_size")
        col.prop(settings.batch, "use_global_percentage")
        col.prop(settings.batch, "ignore_border")
        col.prop(settings.batch, "overwrite")

        row = col.row()
        row.enabled = not settings.batch.overwrite
        row.prop(settings.batch, "skip_existing")

        col.separator()

        col.prop(settings.batch, "write_logs")
        col.prop(settings.batch, "disable_addons")
        col.prop(settings.batch, "use_rss")

        col.separator()
        row = col.row()
        row.enabled = not network
        row.prop(settings.batch, "use_term")
        layout.row().prop(settings.batch, "use_rename")
        layout.row().prop(settings.batch, "fix_layer_nodes")

        col = split.column(align=True)
        row = col.row(align=True)
        row.enabled = settings.batch.use_global_size
        row.prop(settings.batch, "global_size_x")
        row = col.row(align=True)
        row.enabled = settings.batch.use_global_size
        row.prop(settings.batch, "global_size_y")

        row = col.row(align=True)
        row.enabled = settings.batch.use_global_percentage
        row.scale_y = 1.1
        row.prop(settings.batch, "global_percentage", text="")

        col.separator(factor=4)
        row = col.row()
        row.scale_y = 1.1
        row.prop(settings.batch, "parallel")

        col.separator(factor=10)
        layout.separator()

        row = layout.row()
        row.label(text="Notifications", icon="LIGHT")
        row.menu(
            "RP_MT_BatchNotifications", text=utils.notification_text(settings.batch)
        )

        row = layout.row()
        row.label(text="Power Off", icon="QUIT")
        row.prop(settings.batch, "poweroff", text="")

    if settings.batch.ui_settings_tab == "ACTIONS":
        action_prop(layout, settings.batch.pre_batch_hook, "Before running the batch")
        action_prop(layout, settings.batch.post_batch_hook, "After running the batch")
        action_prop(layout, settings.batch.pre_job_hook, "Before running a render job")
        action_prop(layout, settings.batch.post_job_hook, "After running a render job")


def running_state(layout: UILayout) -> None:
    """Layout for the state when a batch is running."""

    settings = bpy.context.scene.renderplus
    
    try:
        job = settings.batch.jobs[settings.batch.index]
    except IndexError:
        op = layout.row().operator('renderplus.batch_toggle_mode', text='Close')
        op = 'NORMAL'

    if state.reply["status"] == "FINISHED":
        utils.title(layout, "Batch Finished", "CHECKBOX_HLT")
    elif state.reply["status"] == "CANCELLED":
        utils.title(layout, "Batch Failed", "ERROR")
    else:
        utils.title(layout, "Running", "PREFERENCES")

    row = layout.row()
    row.template_list(
        "RP_UL_Batch",
        "RP_Batch_list",
        settings.batch,
        "jobs",
        settings.batch,
        "index",
        rows=2,
    )

    layout.separator()

    job_data = state.reply["jobs"][settings.batch.index]

    started = (
        utils.date_format(job_data["times"]["started"])
        if job_data["times"]["started"]
        else "---"
    )

    finished = (
        utils.date_format(job_data["times"]["finished"])
        if job_data["times"]["finished"]
        else "---"
    )

    rendertime = (
        utils.time_format(job_data["times"]["rendertime"])
        if job_data["times"]["rendertime"]
        else "---"
    )

    layout.separator()
    row = layout.row()

    if job_data["status"] == "QUEUED":
        row.label(text="Render job Queued", icon="TIME")

    elif job_data["status"] == "DISABLED":
        row.label(text="Render job Disabled", icon="REMOVE")

    elif job_data["status"] == "UPLOADING":
        row.label(text=job_data['upload_msg'], icon="TRIA_UP")

    elif job_data["status"] == "RUNNING":
        remaining = "Rendering..."
        icon = {
            "RENDERING": "OUTLINER_OB_CAMERA",
            "COMPOSITING": "SHADERFX",
            "COMPOSITING_INIT": "SHADERFX",
        }

        try:
            step = job_data["engine"]["data"]["step"]
        except KeyError:
            step = "RENDERING"

        if step == "RENDERING":
            try:
                remaining = "Remaining: " + job_data["engine"]["data"]["remaining"]
            except (KeyError, TypeError):
                pass

        elif step == "COMPOSITING":
            remaining = "Compositing..."

        elif step == "COMPOSITING_INIT":
            remaining = "Initializing Compositor..."

        row.label(text=f"{remaining}", icon=icon[step])

    elif job_data["status"] == "FINISHED":
        row.label(text="Render job Finished", icon="CHECKBOX_HLT")

    elif job_data["status"] == "CANCELLED":
        row.label(text="Render job Cancelled", icon="X")

    elif job_data["status"] == "FAILED":
        row.label(text="Render job Failed", icon="ERROR")

    if (
        job_data["engine"]["type"] == "NON_COMPATIBLE"
        or job_data["status"] == "DISABLED"
    ):
        row.operator("renderplus.batch_cancel_job", text="", icon="PANEL_CLOSE")
        row.enabled = job_data["status"] == "RUNNING"
    else:
        row = layout.row(align=True)
        row.progress(factor=job.progress / 100, text=f'{job.progress:.2f}%', type='BAR')
        row.operator("renderplus.batch_cancel_job", text="", icon="PANEL_CLOSE")
        row.enabled = job_data["status"] == "RUNNING"

    layout.separator()

    item(layout, "Started", started)
    item(layout, "Finished", finished)
    item(layout, "Rendertime", rendertime)

    if job_data["engine"]["type"] == "CYCLES":
        if job_data["status"] == "RUNNING":
            try:
                elapsed = job_data["engine"]["data"]["elapsed"]
                mem = job_data["engine"]["data"]["mem"]
                tiles_todo = job_data["engine"]["data"]["todo"]
                tiles_done = job_data["engine"]["data"]["done"]
                frame = job_data["engine"]["data"]["frame"]
            except (TypeError, KeyError):
                frame = elapsed = mem = tiles_todo = tiles_done = "---"
        else:
            frame = elapsed = mem = tiles_todo = tiles_done = "---"

        sp = item(layout, "Elapsed", elapsed)
        sp.enabled = job_data["status"] == "RUNNING"

        sp = item(layout, "Memory", mem)
        sp.enabled = job_data["status"] == "RUNNING"

        sp = item(layout, "Samples", f"{tiles_done} / {tiles_todo}")
        sp.enabled = job_data["status"] == "RUNNING"

        sp = item(layout, "Frame", frame)
        sp.enabled = job_data["status"] == "RUNNING"

    elif job_data["engine"]["type"] == "BLENDER_EEVEE":
        if job_data["status"] == "RUNNING":
            try:
                elapsed = job_data["engine"]["data"].get("elapsed", "")
                mem = job_data["engine"]["data"].get("mem", "")
                samples_todo = job_data["engine"]["data"].get("todo", "")
                samples_done = job_data["engine"]["data"].get("done", "")
                frame = job_data["engine"]["data"].get("frame", "")
            except (TypeError, AttributeError):
                frame = elapsed = mem = samples_todo = samples_done = "---"
        else:
            frame = elapsed = mem = samples_todo = samples_done = "---"

        sp = item(layout, "Elapsed", elapsed)
        sp.enabled = job_data["status"] == "RUNNING"

        sp = item(layout, "Memory", mem)
        sp.enabled = job_data["status"] == "RUNNING"

        sp = item(layout, "Samples", f"{samples_done} / {samples_todo}")
        sp.enabled = job_data["status"] == "RUNNING"

        sp = item(layout, "Frame", str(frame))
        sp.enabled = job_data["status"] == "RUNNING"

    if job_data["status"] == "FAILED" and job_data["messages"]:
        layout.row().label(text="Error Messages", icon="ERROR")
        [layout.row().label(text=line) for line in job_data["messages"]]

    layout.separator()
    layout.separator()

    if state.server_stuck:
        layout.row().label(text="Batch Server error", icon="ERROR")
        layout.row().label(
            text=("The server got stuck and was automatically " "stopped.")
        )
        layout.separator()

    row = layout.row()
    row.scale_y = 1.1

    if state.last_batch or state.server_stuck:
        op = row.operator("renderplus.batch_toggle_mode", text="Close")
        op.mode = "NORMAL"
    else:
        row.operator("renderplus.cancel_batch", text="Cancel Batch")


def normal_state(layout: UILayout) -> None:
    """Layout for the normal state of the batch list."""

    settings = bpy.context.scene.renderplus

    row = layout.row()
    op = row.operator("renderplus.batch_toggle_mode",
                      text="Quick Batch",
                      icon='SHADERFX')

    op.mode = "QUICK_BATCH"
    layout.separator()

    props = bpy.context.window_manager.renderplus

    if settings.batch.has_external and len(props) == 0:
        row = layout.row()
        row.scale_y = 1.2
        row.operator("renderplus.reload_external_blend_data", icon="FILE_REFRESH")

    row = layout.row()
    row.template_list(
        "RP_UL_Batch", "RP_Batch_list", settings.batch, "jobs", settings.batch, "index"
    )

    col = row.column(align=True)
    col.operator("renderplus.new_render_job", icon="ADD", text="").duplicate = False
    col.operator("renderplus.delete_render_job", icon="REMOVE", text="").clear = False
    col.separator()
    col.separator()
    col.operator("renderplus.move_render_job", icon="TRIA_UP", text="").direction = "UP"
    col.operator("renderplus.move_render_job", icon="TRIA_DOWN", text="").direction = (
        "DOWN"
    )

    col.separator()
    col.separator()
    col.menu("RP_MT_BatchOps", icon="COLLAPSEMENU", text="")


def output_change_state(layout: UILayout) -> None:
    """Layout for the output change state."""

    settings = bpy.context.scene.renderplus.batch_ops.output_change
    utils.title(layout, "Change output paths", "NLA")

    row = layout.row()
    row.label(text="Base directory", icon="FILE_FOLDER")
    row = layout.row()
    row.prop(settings, "base_directory", text="")

    layout.separator()
    row = layout.row()
    row.label(text="Create subdirectories", icon="NEWFOLDER")
    row = layout.row(align=True)
    row.prop(settings, "subdirs_scene", toggle=True)
    row.prop(settings, "subdirs_cam", toggle=True)
    row.prop(settings, "subdirs_layer", toggle=True)
    layout.separator()

    row = layout.row()
    row.label(text="File name", icon="FILE_BLANK")
    row = layout.row()
    row.prop(settings, "base_filename", text="")
    row = layout.row(align=True)
    row.label(text="Suffixes")
    row.prop(settings, "name_suffix_01", text="")
    row.prop(settings, "name_suffix_02", text="")
    row.prop(settings, "name_suffix_03", text="")

    layout.separator()
    layout.separator()
    row = layout.row()
    row.label(text="Sample (from first job):", icon="FILE")

    job = bpy.context.scene.renderplus.batch.jobs[0]
    sample = recipe.make_output_path(job)
    row = layout.row()
    row.label(text=sample)
    row.scale_y = 0.4

    layout.separator()
    layout.separator()

    utils.buttons(layout, "renderplus.batch_change_outputs", text="Change outputs")


def log_state(layout: UILayout) -> None:
    """Layout for the log state."""

    settings = bpy.context.scene.renderplus.batch
    utils.title(layout, "Previous batch results", "PREVIEW_RANGE")
    layout.separator()

    row = layout.row()
    row.template_list(
        "RP_UL_BatchLogs", "RP_Batch_list", settings, "jobs", settings, "index"
    )

    layout.separator()
    layout.row().prop(settings, "ui_log_tab", expand=True)
    layout.separator()

    if settings.ui_log_tab == "BATCH":
        batch_times = state.last_batch["times"]
        batch_start = utils.date_format(batch_times["started"])
        batch_end = utils.date_format(batch_times["finished"])
        batch_render = utils.time_format(batch_times["rendertime"])

        avg = utils.time_format(state.last_batch["stats"]["average_time"])
        slowest = utils.time_format(state.last_batch["stats"]["slowest_time"])
        fastest = utils.time_format(state.last_batch["stats"]["fastest_time"])

        slowest_job = state.last_batch["stats"]["slowest_job"]
        fastest_job = state.last_batch["stats"]["fastest_job"]

        item(layout, "Started", batch_start)
        item(layout, "Finished", batch_end)
        item(layout, "Rendertime", batch_render)

        item(layout, "Average time", avg)
        item(layout, "Slowest job", f"#{slowest_job} ({slowest})")
        item(layout, "Fastest job", f"#{fastest_job} ({fastest})")

    elif settings.ui_log_tab == "JOB":
        job = state.last_batch["jobs"][settings.index]

        if job["status"] == "DISABLED":
            layout.row().label(text="Job was Disabled", icon="INFO")
        elif job["status"] == "CANCELLED":
            layout.row().label(text="Cancelled", icon="X")

        elif job["status"] == "FAILED":
            layout.row().label(text="Failed", icon="ERROR")
            [layout.row().label(text=line) for line in job["messages"]]
        else:
            job_start = utils.date_format(job["times"]["started"])
            job_end = utils.date_format(job["times"]["finished"])
            job_render = utils.time_format(job["times"]["rendertime"])

            layout.separator()
            item(layout, "Started", job_start)
            item(layout, "Finished", job_end)
            item(layout, "Rendertime", job_render)


class RP_PT_Batch(Panel):
    """Panel for batch rendering."""

    bl_label = "Render+ Batch"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    @classmethod
    def poll(cls, context):
        return utils.prefs().show_batch

    def draw(self, context):
        layout = self.layout
        settings = context.scene.renderplus.batch

        if not settings.jobs and state.mode == "NORMAL":
            empty_state(layout)
        elif state.mode == "PACKING":
            packing_state(layout)
        elif state.mode == "RUNNING":
            running_state(layout)
        elif state.mode == "SETTINGS":
            settings_state(layout)
        elif state.mode == "LOG":
            log_state(layout)
        elif state.mode == "OUTPUT_CHANGE":
            output_change_state(layout)
        elif state.mode == "QUICK_BATCH":
            quick.quick_mode(layout)
        else:
            normal_state(layout)

        layout.separator()
