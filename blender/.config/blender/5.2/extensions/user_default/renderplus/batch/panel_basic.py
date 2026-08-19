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

from . import state
from .. import utils
from .panel_base import RP_PT_SubPanel


def check_viewlayer(scene: Scene, layer: ViewLayer) -> bool:
    """Check if there's a render layer node."""

    problem = False

    if layer and scene.compositing_node_group.nodes:
        for node in scene.node_tree.nodes:
            if node.bl_idname == "CompositorNodeRLayers":
                problem = node.layer != layer

    return problem


class RP_PT_BasicSettings(RP_PT_SubPanel):
    """Basic Settings subpanel"""

    bl_label = "Basic Settings"
    bl_options = set()

    def draw_header(self, context):
        self.layout.label(text="", icon="SCENE_DATA")

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        if job.use_external:
            row = layout.row(align=True)
            row.alert = state.external_error
            row.prop(job, "blend_file", text="")
            row.operator(
                "renderplus.batch_set_external_file", text="", icon="FILE_FOLDER"
            )
            layout.separator()

        col = layout.column()
        col.prop(job, "name")

        if job.use_external:
            try:
                props = bpy.context.window_manager.renderplus
                extern = props[utils.base_filename(job.blend_file)]

                col.prop_search(job, "ex_scene", extern, "scenes", icon="SCENE")
                col.prop_search(job, "ex_camera", extern, "cameras", icon="CAMERA_DATA")

                col.prop_search(job, "ex_world", extern, "worlds", icon="WORLD")

                col.prop_search(
                    job, "ex_layer", extern, "view_layers", icon="RENDERLAYERS"
                )

            except KeyError:
                pass

        else:
            col.prop_search(job, "scene", bpy.data, "scenes", icon="SCENE")

            if job.scene:
                cam_row = col.row()
                cam_row.alert = not job.camera
                cam_row.prop(job, "camera", icon="CAMERA_DATA")

                col.prop_search(job, "world", bpy.data, "worlds", icon="WORLD")

                col.prop_search(
                    job, "layer", job.scene, "view_layers", icon="RENDERLAYERS"
                )

        layout.separator()

        col = layout.column()

        col.prop(job, "animation")
        col.prop(job, "use_external", text="Use external file")

        if check_viewlayer(job.scene, job.layer) and settings.fix_layer_nodes:
            layout.separator()
            box = layout.box().column(align=True)
            box.label(text="View layer used in nodes is different", icon="ERROR")
            box.separator()
            box.label(text="It will be automatically changed, but")
            box.label(text="note this could break your node setup.")


class RP_PT_CustomFrame(RP_PT_SubPanel):
    """Frame Settings subpanel"""

    bl_label = "Custom Frame(s)"

    def draw_header(self, context):
        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        self.layout.label(text="", icon="PREVIEW_RANGE")
        self.layout.prop(job, "frame_custom", text="")

    def draw(self, context):
        layout = self.layout
        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        col = layout.column(align=True)
        col.enabled = job.frame_custom

        if job.animation:
            col.prop(job, "frame_start")
            col.prop(job, "frame_end")
            col.prop(job, "frame_jump")
        else:
            row = col.row(align=True)
            row.prop(job, "frames", text="")
            row.operator("renderplus.custom_frame_popup", text="", icon="HELP")
            col.separator(factor=2)


class RP_PT_Actions(RP_PT_SubPanel):
    """Action Settings subpanel"""

    bl_label = "Actions"

    def draw_header(self, context):
        self.layout.label(text="", icon="LINENUMBERS_ON")

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        layout.prop(job, "use_pre_job_script", text="Run before render job")

        if job.use_pre_job_script:
            split = layout.split(factor=0.4)
            split.separator()

            if job.use_external:
                props = bpy.context.window_manager.renderplus
                extern = props[utils.base_filename(job.blend_file)]

                split.prop_search(
                    job, "ex_pre_job_script", extern, "scripts", icon="TEXT", text=""
                )

            else:
                split.prop(job, "pre_job_script", text="")
