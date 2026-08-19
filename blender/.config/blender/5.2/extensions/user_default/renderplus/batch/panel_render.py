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

from .. import utils
from . import data
from .panel_base import RP_PT_SubPanel


class RP_PT_Output(RP_PT_SubPanel):
    """Panel for output settings."""

    bl_label = "Output"

    def draw_header(self, context):
        self.layout.label(text="", icon="OUTPUT")

    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = bpy.context.scene.renderplus
        engine = bpy.context.scene.render.engine
        network = utils.prefs().batch_server_location == "NETWORK"
        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        bad_output = network and job.output.startswith("//")
        col = layout.column(align=True)
        col.alert = bad_output
        col.prop(job, "output", text="")

        if network:
            if bad_output:
                col.separator()
                col.alert = False
                col.label(text="Please use absolute paths. Otherwise", icon="ERROR")
                col.label(text="renders will end in a temporary folder", icon="DOT")

            else:
                col.separator()
                col.label(text="Files will be in render server", icon="INFO")
        else:
            col.operator(
                "renderplus.batch_open_render_folder", text="Open Output Folder"
            )

        layout.separator()

        col = layout.column(align=True)
        col.prop(job, "use_custom_format")

        if job.use_custom_format:
            row = col.row()
            row.prop(job, "format", text="Format")
            row.enabled = job.use_custom_format
            col.separator(factor=3)

            if data.is_format_optional(job.format):
                col.label(
                    text="This format may not be available on your system", icon="INFO"
                )

        col.prop(job, "size_custom")

        if job.size_custom:
            col.prop(job, "size_x")
            col.prop(job, "size_y")
            col.separator(factor=3)

        col.prop(job, "use_section")

        if job.use_section:
            col.prop(job, "section_x")
            col.prop(job, "section_y")
            col.prop(job, "section_width")
            col.prop(job, "section_height")

            col.separator()
            row = col.split(factor=0.4)
            row.separator()
            row.operator("renderplus.batch_get_from_viewport", text="Get From Viewport")

            col.separator(factor=3)

        if settings.use_global_size and job.size_custom:
            col.separator()
            col.box().label(text="Global size is enabled", icon="INFO")

        col.separator()


class RP_PT_RenderEngine(RP_PT_SubPanel):
    """Panel for output settings."""

    bl_label = ""

    def draw_header(self, context):

        self.layout.label(text="Engine Settings", icon="SHADING_RENDERED")

    def draw(self, context):

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)

        settings = context.scene.renderplus
        engine = context.scene.render.engine
        network = utils.prefs().batch_server_location == "NETWORK"
        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        row = col.row()
        row.enabled = utils.check_turbotools()
        row.prop(job, "use_turbotools", text="Use TurboTools")
        col.prop(job, "threads")

        if engine == "CYCLES":
            col.prop(job, "cycles_samples", text="Samples")

        if engine == "CYCLES":
            layout.separator()
            col.prop(job, "device", text="Device")

            if job.device == "SINGLE_GPU" and not network:
                col.prop(job, "gpu_local", text="GPU")

        if job.threads == 0:
            col.separator(factor=2)
            col.box().label(text="Threads will be set automatically", icon="INFO")

        if engine == "CYCLES" and job.cycles_samples == 0:
            col.separator()
            col.box().label(
                text="Samples will be taken from Cycles settings", icon="INFO"
            )


class RP_UL_RenderPasses(UIList):
    """UI list to show render passes."""

    def filter_items(self, context, data, propname):

        items = getattr(data, propname)
        engine = context.scene.render.engine
        filtered = [self.bitflag_filter_item] * len(items)

        for index, item in enumerate(items):
            if item.engine not in ("ALL", engine):
                filtered[index] &= ~self.bitflag_filter_item

        return filtered, []

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):

        row = layout.row()
        col = row.column()
        col.enabled = item.enabled
        col.label(text=f"  {item.name}")
        row.prop(item, "enabled", text="")


class RP_PT_RenderPasses(RP_PT_SubPanel):
    """Panel for output settings."""

    bl_label = "Render Passes"

    def draw_header(self, context):
        self.layout.label(text="", icon="RENDERLAYERS")

    def draw(self, context):
        layout = self.layout
        settings = bpy.context.scene.renderplus.batch
        job = settings.jobs[settings.index]

        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        row.template_list(
            "RP_UL_RenderPasses",
            "RP_UL_RenderPasses",
            job,
            "passes",
            job,
            "passes_index",
        )

        if job.passes_index > -1:
            rpass = job.passes[job.passes_index]

            layout.separator()
            col = layout.column()
            col.enabled = rpass.enabled
            col.alert = not rpass.output
            col.prop(rpass, "output")
            layout.separator()
