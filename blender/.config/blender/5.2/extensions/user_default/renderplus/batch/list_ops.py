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

"""List manipulation operators for the render jobs list."""

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, BoolProperty, EnumProperty


from . import ops
from . import data
from ..single import utils


def index() -> int:
    """Get index of the currently selected render job."""

    return bpy.context.scene.renderplus.batch.index


class RP_OT_NewRenderJob(Operator):
    """Add a new Render job to the batch list."""

    bl_idname = "renderplus.new_render_job"
    bl_label = "Add a new Render job to the batch list"

    duplicate: BoolProperty(default=False)

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs
        new_index = len(batch_list)
        scene = context.scene
        prefs = utils.prefs()

        batch_list.add()
        batch_list[new_index].name = data.check_job_name(scene.name)

        if self.duplicate:
            original = ops.current_job()
            dupe_index = index() + 1
            batch_list.move(new_index, dupe_index)
            dupe = batch_list[dupe_index]

            for key, value in original.items():
                dupe[key] = value

            dupe["name"] = data.check_job_name(original["name"] + "_duplicate")
            context.scene.renderplus.batch.index = dupe_index

        else:
            # Move index to the new job
            context.scene.renderplus.batch.index = new_index

            # Use scene updater to auto-populate settings
            batch_list[new_index].scene = context.scene
            batch_list[new_index].frame_start = scene.frame_start
            batch_list[new_index].frame_end = scene.frame_end

            output = ops.default_output(scene)

            batch_list[new_index].output = output

            if prefs.batch_always_turbo:
                batch_list[new_index].use_turbotools = True

            data.fill_render_passes(batch_list[new_index])

        return {"FINISHED"}


class RP_OT_CopyJobSettings(Operator):
    """Add a new Render job to the batch list."""

    bl_idname = "renderplus.copy_settings"
    bl_label = "Copy Settings to the other render jobs"
    poll = ops.ready_to_run

    animation: BoolProperty(name='Animation', default=False)
    custom_frame: BoolProperty(name='Custom Frame', default=False)
    frame: BoolProperty(name='Frame', default=False)
    frame_start: BoolProperty(name='Frame Start', default=False)
    frame_end: BoolProperty(name='Frame End', default=False)
    scene: BoolProperty(name='Scene', default=False)
    camera: BoolProperty(name='Camera', default=False)
    world: BoolProperty(name='World', default=False)
    layer: BoolProperty(name='Layer', default=False)
    file_format: BoolProperty(name='File Format', default=False)


    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


    def draw(self, context) -> None:
        layout = self.layout

        layout.separator()
        layout.label(text='Select which settings to copy',
                     icon='EXPERIMENTAL')

        layout.prop(self, 'scene')
        layout.prop(self, 'camera')
        layout.prop(self, 'world')
        layout.prop(self, 'layer')

        layout.separator()
        layout.prop(self, 'animation')
        layout.prop(self, 'custom_frame')

        if self.animation:
            row1 = layout.row()
            row2 = layout.row()

            row1.enabled = self.custom_frame
            row2.enabled = self.custom_frame

            row1.prop(self, 'frame_start')
            row2.prop(self, 'frame_end')
        else:
            row = layout.row()
            row.enabled = self.custom_frame

            row.prop(self, 'frame')

        layout.separator()
        layout.prop(self, 'file_format')


        layout.separator()

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs
        current = batch_list[index()]

        for job in batch_list:
            if job == current:
                continue

            if self.animation:
                job.animation = current.animation

            if self.custom_frame:
                job.frame_custom = current.frame_custom

            if self.frame:
                job.frames = current.frames

            if self.frame_start:
                job.frame_start = current.frame_start

            if self.frame_end:
                job.frame_end = current.frame_end

            if self.file_format:
                job.use_custom_format = True
                job.format = current.format

            if not job.use_external:
                print(current.camera)
                if self.scene:
                    job.scene = current.scene

                if self.world:
                    job.world = current.world

                if self.camera:
                    job.camera = current.camera

                if self.layer:
                    job.layer = current.layer

        self.report({'INFO'}, 'Copied settings to all jobs')
        return {"FINISHED"}



class RP_OT_ToggleJobs(Operator):
    """Disable/Enable render jobs."""

    bl_idname = "renderplus.batch_toggle"
    bl_label = "Toggle Render jobs"
    bl_options = {"UNDO"}
    poll = ops.ready_to_run

    enable: BoolProperty(default=True)

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs

        for job in batch_list:
            job.enabled = self.enable

        return {"FINISHED"}


class RP_OT_DeleteRenderJob(Operator):
    """Removes a render job from the batch list."""

    bl_idname = "renderplus.delete_render_job"
    bl_label = "Remove Render jobs"
    poll = ops.ready_to_run

    clear: BoolProperty(default=False)

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs
        current = index()

        if self.clear:
            batch_list.clear()
            return {"FINISHED"}

        if current >= 0:
            batch_list.remove(current)

            if current > 0:
                context.scene.renderplus.batch.index -= 1

            return {"FINISHED"}
        else:
            return {"CANCELLED"}

    def draw(self, context):
        layout = self.layout
        layout.label(
            text="Are you sure you want to remove ALL render jobs?", icon="ERROR"
        )

    def invoke(self, context, event):
        if self.clear:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)


class RP_ToggleJobType(Operator):
    """Toggle job type between still and animation."""

    bl_idname = "renderplus.toggle_render_job"
    bl_label = "Toggle render job type"
    poll = ops.ready_to_run

    index: IntProperty(min=0)

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs
        job = batch_list[self.index]

        job.animation = not job.animation

        return {"FINISHED"}


class RP_OT_MoveRenderJob(Operator):
    """Move a Render job up or down in the batch list."""

    bl_idname = "renderplus.move_render_job"
    bl_label = "Removes a Render job from the batch list"
    poll = ops.ready_to_run

    direction: EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("TOP", "Top", ""),
            ("BOTTOM", "Bottom", ""),
        )
    )

    def move_index(self, context):
        """Move index of a render job while clamping it."""

        list_length = len(context.scene.renderplus.batch.jobs) - 1
        current = index()
        new_index = 0

        if self.direction == "UP":
            new_index = current - 1
        elif self.direction == "DOWN":
            new_index = current + 1
        elif self.direction == "TOP":
            new_index = 0
        elif self.direction == "BOTTOM":
            new_index = list_length

        new_index = max(0, min(new_index, list_length))
        context.scene.renderplus.batch.index = new_index

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs
        current = index()

        if current >= 0:
            if self.direction == "DOWN":
                neighbor = current + 1
                batch_list.move(current, neighbor)
                self.move_index(context)

            elif self.direction == "UP":
                neighbor = current - 1
                batch_list.move(neighbor, current)
                self.move_index(context)

            elif self.direction == "BOTTOM":
                neighbor = len(batch_list) - 1
                batch_list.move(current, neighbor)
                self.move_index(context)

            elif self.direction == "TOP":
                neighbor = 0
                batch_list.move(current, neighbor)
                self.move_index(context)

            else:
                return {"CANCELLED"}

            return {"FINISHED"}
        else:
            return {"CANCELLED"}
