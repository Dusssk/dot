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


class RP_PT_CustomOverrides(RP_PT_SubPanel):
    """Panel for Custom Overrides"""

    bl_label = "Custom Overrides"

    def draw_header(self, context):
        self.layout.label(text="", icon="MODIFIER_ON")

    def enabled_prop_type(self, custom) -> bool:
        """Wether prop type row should be enabled."""

        match custom.kind:
            case 'bpy.data.collections':
                return bool(custom.col_pointer)
            case 'bpy.data.objects':
                return bool(custom.obj_pointer)
            case 'bpy.data.lights':
                return bool(custom.lights_pointer)
            case 'bpy.data.cameras':
                return bool(custom.cameras_pointer)
            case 'CUSTOM' | _:
                return True


    def draw(self, context):
        layout = self.layout
        settings = context.scene.renderplus

        job = settings.batch.jobs[settings.batch.index]

        layout.separator()

        row = layout.row(align=True)
        row.menu("RP_MT_CustomOverridePresets", text="Presets")
        row.operator("renderplus.add_override_preset", text="", icon="ADD")
        row.operator(
            "renderplus.add_override_preset", text="", icon="REMOVE"
        ).remove_active = True

        layout.separator()

        if not job.custom_overrides:
            box = layout.box()
            row = box.row()
            row.scale_y = 1.2
            row.operator("renderplus.batch_add_custom_override", icon="ADD")

            row = box.row(align=True)
            col = row.column(align=True)
            col.scale_y = 0.85
            col.label(text="You can use this section to override any data in")
            col.label(text="the blendfile.")
            col.separator(factor=4)
            col.label(
                text=("Note that data values are not checked for " "errors"),
                icon="INFO",
            )

            layout.separator()
            row = layout.row(align=True)
            row.scale_y = 1.1
            row.operator(
                "wm.url_open", text="Learn more about data paths", icon="URL"
            ).url = (
                "https://www.blender.org/api/blender"
                "_python_api_current/info_quickstart"
                ".html#accessing-attributes"
            )

        else:
            row = layout.row()

            row.template_list(
                "RP_UL_BatchOverrides",
                "RP_UL_BatchOverrides",
                job,
                "custom_overrides",
                job,
                "custom_overrides_index",
            )

            col = row.column(align=True)
            col.operator("renderplus.batch_add_custom_override", text="", icon="ADD")
            col.operator(
                "renderplus.batch_remove_custom_override", text="", icon="REMOVE"
            )

            col.separator()

            col.operator(
                "renderplus.batch_clone_override", text="", icon="NODE_COMPOSITING"
            )

            col.separator()
            col.operator(
                "renderplus.help", text="", icon="QUESTION", emboss=False
            ).section = "CUSTOM_OVERRIDES"

            col.separator()
            show_icon = 'HIDE_OFF' if job.show_override_sample else 'HIDE_ON'
            col.prop(job, 'show_override_sample', icon=show_icon, text='', emboss=False)

            layout.separator()

            custom = job.custom_overrides[job.custom_overrides_index]

            row = layout.row()
            row.label(text="Datapath", icon="RNA")

            row = layout.row(align=True)
            row.prop(custom, "kind", text="")

            match custom.kind:
                case 'bpy.data.collections':
                    pointer = "col_pointer"
                case 'bpy.data.objects':
                    pointer = "obj_pointer"
                case 'bpy.data.lights':
                    pointer = "lights_pointer"
                case 'bpy.data.cameras':
                    pointer = "cameras_pointer"
                case 'CUSTOM' | _:
                    pointer = "CUSTOM"

            if pointer != "CUSTOM":
                row.prop(custom, pointer, text='')

            row = layout.row(align=True)
            row.enabled = self.enabled_prop_type(custom)
            row.prop(custom, 'prop_type', text='')

            if custom.prop_type == 'CUSTOM':
                row.prop(custom, 'path', text='')


            layout.separator()
            row = layout.row()
            row.label(text="Custom Data", icon="EMPTY_DATA")


            if custom.prop_type == 'CUSTOM':
                row = layout.row()
                row.prop(custom, "data", text="")
            elif custom.get(custom.cid) is not None:
                if custom.prop_type == 'VISIBLE':
                    text = 'Visible'
                else:
                    text = ''

                row = layout.row()
                row.prop(custom, f'["{custom.cid}"]', text=text)

            if job.show_override_sample:
                if sample := custom.to_sample():
                    layout.separator()
                    box = layout.box()
                    box.label(text=sample, icon="SCRIPT")

            layout.separator()
