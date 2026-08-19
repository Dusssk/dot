import bpy
import os
from pathlib import Path
from .... import bl_info
from ....icons.menus import get_icon_id
from ....utils import addon
from ...tools.nsolve import nsuite_options, nso_sliders
from ...ops.nflow.common import NFlowPrefs


class NSOLVE_OT_RefreshFolders(bpy.types.Operator):
    bl_idname = 'nsolve.refresh_folders'
    bl_label = "Refresh Folders"
    bl_description = "Refresh the list of demo folders"

    def execute(self, context):
        # Clear existing folder states
        addon.pref().tools.nsolve.folder_states.clear()
        # Rebuild subfolders
        helper = context.window_manager.operators.get("nsolve.helper")
        if helper:
            helper.create_folder_subpanel(helper.layout, helper.demo_files_dir)
        else:
            # If helper operator is not running, manually trigger the redraw
            context.area.tag_redraw()
        return {'FINISHED'}


class NSOLVE_OT_Helper(bpy.types.Operator):
    bl_idname = 'nsolve.helper'
    bl_label = "nSolve Helper"
    bl_description = "nSolve Helper"
    bl_options = {'UNDO'}

    main: bpy.props.BoolProperty(default=True, name="Main")
    aux: bpy.props.BoolProperty(default=False, name="Aux")
    sub: bpy.props.BoolProperty(default=False, name="Sub")
    ext: bpy.props.BoolProperty(default=False, name="Ext")

    demo_files_dir: Path = Path(__file__).parent.parent.parent.parent / "Files"

    @classmethod
    def poll(cls, context):
        return True

    def check(self, context):
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=380)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"nSolve Helper: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}")

        split = layout.split(factor=0.12)
        col = split.column()
        col.scale_y = 2
        col.scale_x = 2
        self.first_column(context, col)

        split = split.column(align=True)
        self.second_column(context, split)

    def first_column(self, context, layout):
        maincol = layout.column(align=True)

        row = maincol.row(align=True)
        sub = row.row()
        sub.scale_x = 0.5
        sub.separator()

        row.scale_x = 1.2
        row.scale_y = 0.8
        op = row.operator("nsolve.set_activetool", text="", icon_value=get_icon_id("nsolve"))
        op.tool = 'NSO'
        op.description = "nSolve"

        row = maincol.row(align=True)
        sub = row.row()
        sub.scale_x = 0.5
        sub.separator()

        row.scale_x = 1.2
        row.scale_y = 0.8
        op = row.operator("nsolve.set_activetool", text="", icon_value=get_icon_id("nsuite"))
        op.tool = 'NSU'
        op.description = "nSuite"

        row = maincol.row(align=True)
        sub = row.row()
        sub.scale_x = 0.5
        sub.separator()

        row.scale_x = 1.2
        row.scale_y = 0.8
        if context.mode == 'OBJECT':
            op = row.operator("nsolve.set_activetool", text="", icon_value=get_icon_id("nflow"))
            op.tool = 'NFLOWOBJ'
            op.description = "nFlow"
        else:
            op = row.operator("nsolve.set_activetool", text="", icon_value=get_icon_id("nflow"))
            op.tool = 'NFLOW'
            op.description = "nFlow"

    def second_column(self, context, layout):
        col = layout.column(align=False)

        if context.workspace.tools.from_space_view3d_mode(context.mode).idname == 'nsolve.nsolvetool':
            self.nsolve_layout(col)
        elif context.workspace.tools.from_space_view3d_mode(context.mode).idname == 'nsolve.nflow_edit_mode':
            self.nflow_layout(col)
        elif context.workspace.tools.from_space_view3d_mode(context.mode).idname == 'nsolve.nflow_object_mode':
            self.nflow_layout(col)
        elif context.workspace.tools.from_space_view3d_mode(context.mode).idname == 'nsolve.nsuitetool':
            self.nsuite_layout(col)
        elif context.workspace.tools.from_space_view3d_mode(context.mode).idname == 'nsolve.main_tool':
            self.files(col)

    def nflow_layout(self, col):
        nflow_config_workspace = bpy.context.workspace.nsolve.ops.nflow
        behavior_presets_config = nflow_config_workspace.behavior_presets_config
        behavior_presets = behavior_presets_config.behavior_presets

        draw_tool_header = NFlowPrefs.get('draw_tool_header')
        draw_tool_header(col, multiline=True, show_config=False)

        if behavior_presets:
            draw_presets = NFlowPrefs.get('draw_presets')
            draw_presets(col, place='HELPER')

    def draw_gizmos_layout(self, layout, props):
        if props.operator == 'JOIN':
            layout.prop(props, 'multi_join', text='Multi Join')
            layout.separator()
            col = layout.column(align=True, heading='Snap Mode')
            snap = props.snap_join
            col.prop(snap, 'vert', text='Vert', toggle=True)
            col.prop(snap, 'edge', text='Edge', toggle=True)
            col.prop(snap, 'face', text='Face', toggle=True)
            col.prop(snap, 'mid_edge', text='Mid Edge', toggle=True)
            col.prop(snap, 'perp_edge', text='Perp Edge', toggle=True)
            col.prop(snap, 'center_face', text='Center Face', toggle=True)
        elif props.operator == 'SELECT':
            layout.prop(props, 'select_mode', text='Select Mode')
        elif props.operator == 'MERGE':
            layout.prop(props, 'multi_merge', text='Multi Merge')
            layout.prop(props, 'center_merge', text='Center Merge')
            layout.prop(props, 'merge_weld', text='Merge Weld')
            if props.merge_weld:
                layout.prop(props, 'merge_weld_dist', text='Weld Distance')
        elif props.operator == 'LINE':
            layout.prop(props, 'line_cut_through', text='Cut Through')
        elif props.operator == 'COLLAPSE':
            layout.prop(props, 'collapse_affect_selected', text='Affect Selection')
        elif props.operator == 'DISSOLVE':
            layout.prop(props, 'dissolve_use_verts')
            layout.prop(props, 'dissolve_use_face_split')
        elif props.operator == 'SLIDE':
            layout.prop(props, 'slide_selection_mode')
            layout.prop(props, 'slide_multi_elem')
        elif props.operator == 'OFFSET':
            layout.prop(props, 'offset_distance', text='Distance')
            layout.prop(props, 'offset_even_offset', text='Even Offset')
        elif props.operator == 'KNIFE':
            layout.prop(props, 'knife_angle_limit', text='Angle Limit')
            layout.prop(props, 'knife_midpoint_snap', text='Midpoint Snap')
        elif props.operator == 'HIDE':
            layout.prop(props, 'hide_reverse', text='Reverse')
            layout.prop(props, 'hide_volume', text='Volume')

    def nsuite_layout(self, layout):
        nsu = addon.pref().tools.nsuite.nsu
        maincol = layout.column(align=True)
        box = maincol.box()

        split = box.split(factor=0.7)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(nsu, 'enable', text='', icon='TRIA_DOWN' if nsu.enable else 'TRIA_RIGHT', emboss=False)
        row.prop(nsu, 'enable', text='nSuite        ', emboss=False)

        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.operator("nsolve.place_gizmo", icon='DOT', text='').gizmo = 'NSU'
        row.separator()
        row.operator("nsolve.restore_default_operators", icon='EVENT_R', text="")
        row.separator()
        hide_icon = 'HIDE_OFF' if nsu.hide else 'HIDE_ON'
        row.prop(nsu, 'hide', text='', icon=hide_icon)

        if nsu.enable:
            nsuite_options(maincol)

    def nsolve_layout(self, col):
        nsolve = addon.pref().tools.nsolve
        nso = nsolve.nso
        nsu = nsolve.nsu
        nflow = nsolve.nflow

        maincol = col.column(align=True)
        box = maincol.box()

        split = box.split(factor=0.7)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(nso, 'enable', text='', icon='TRIA_DOWN' if nso.enable else 'TRIA_RIGHT', emboss=False)
        row.prop(nso, 'enable', text='nSolve           ', emboss=False)

        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.operator("nsolve.place_gizmo", icon='DOT', text='').gizmo = 'NSO'
        row.separator()
        row.operator("nsolve.restore_default_main_operators", icon='EVENT_R', text="")
        row.separator()
        hide_icon = 'HIDE_OFF' if nso.hide else 'HIDE_ON'
        row.prop(nso, 'hide', text='', icon=hide_icon)

        if nso.enable:
            subbox = maincol.box()
            row = subbox.row(align=False)
            row.popover('NSOLVE_PT_Nsolve', text="Options")
            row = row.row(align=True)
            row.popover('NSOLVE_PT_NsolvePersonas', text="Personas")
            row.menu('NSOLVE_MT_PersonasMenu', text="Set")

            row = subbox.row(align=True)
            labels = (nsolve.main_label, nsolve.aux_label, nsolve.sub_label, nsolve.ext_label)
            row.prop(self, 'main', text=labels[0], toggle=True)
            row.prop(self, 'aux', text=labels[1], toggle=True)
            row.prop(self, 'sub', text=labels[2], toggle=True)
            row.prop(self, 'ext', text=labels[3], toggle=True)

            subbox.use_property_decorate = True
            subbox.use_property_split = True

            if self.main:
                props = nsolve.main
                subcol = subbox.column()
                subbox.prop(props, 'operator', text=labels[0])
                self.draw_gizmos_layout(subbox, props)
            if self.aux:
                props = nsolve.aux
                subcol = subbox.column()
                subbox.prop(props, 'operator', text=labels[1])
                self.draw_gizmos_layout(subbox, props)
            if self.sub:
                props = nsolve.sub
                subcol = subbox.column()
                subbox.prop(props, 'operator', text=labels[2])
                self.draw_gizmos_layout(subbox, props)
            if self.ext:
                props = nsolve.ext
                subcol = subbox.column()
                subbox.prop(props, 'operator', text=labels[3])
                self.draw_gizmos_layout(subbox, props)

        maincol = col.column(align=True)
        box = maincol.box()

        split = box.split(factor=0.7)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(nsu, 'enable', text='', icon='TRIA_DOWN' if nsu.enable else 'TRIA_RIGHT', emboss=False)
        row.prop(nsu, 'enable', text='nSuite        ', emboss=False)

        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.operator("nsolve.place_gizmo", icon='DOT', text='').gizmo = 'NSU'
        row.separator()
        row.operator("nsolve.restore_default_operators", icon='EVENT_R', text="")
        row.separator()
        hide_icon = 'HIDE_OFF' if nsu.hide else 'HIDE_ON'
        row.prop(nsu, 'hide', text='', icon=hide_icon)

        if nsu.enable:
            nsuite_options(box)

        maincol = col.column(align=True)
        box = maincol.box()

        split = box.split(factor=0.7)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(nflow, 'enable', text='', icon='TRIA_DOWN' if nflow.enable else 'TRIA_RIGHT', emboss=False)
        row.prop(nflow, 'enable', text='nFlow        ', emboss=False)

        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.operator("nsolve.swap_mode", text="", icon='DOT').tool = 'NFLOW'

        if nflow.enable:
            box = maincol.box()
            self.nflow_layout(box)

    def nsovle_obj_layout(self, col):
        col.label(text=f' Welcome to nSolve version:{bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}')

    def files(self, col):

        maincol = col.column(align=True)

        if not os.path.exists(self.demo_files_dir):
            maincol.label(text="Demo files directory not found.")
            return

        self.create_folder_subpanel(maincol, self.demo_files_dir,  refresh=True)

    def get_folder_state(self, folder_name):
        folder_states = addon.pref().tools.nsolve.folder_states

        for state in folder_states:
            if state.name == folder_name:
                return state
        new_state = folder_states.add()
        new_state.name = folder_name
        return new_state

    def clean_folder_states(self, base_path):
        folder_states = addon.pref().tools.nsolve.folder_states
        existing_folders = {f.name for f in base_path.iterdir() if f.is_dir()}

        # Collect indices of folder states to be removed
        indices_to_remove = [i for i, state in enumerate(folder_states) if state.name not in existing_folders]

        # Remove folder states by index in reverse order to avoid indexing issues
        for index in sorted(indices_to_remove, reverse=True):
            folder_states.remove(index)

    def create_folder_subpanel(self, layout, folder_path, refresh=False):
        folder_name = os.path.basename(folder_path)
        files_and_folders = os.listdir(folder_path)
        sorted_items = sort_numerically(files_and_folders)

        folder_state = self.get_folder_state(folder_name)

        subbox = layout.box()
        split = subbox.split(factor=0.9)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(folder_state, "expanded", text='', icon='TRIA_DOWN' if folder_state.expanded else 'TRIA_RIGHT', emboss=False)
        row.prop(folder_state, "expanded", text=folder_name, emboss=False)

        if refresh:
            split = split.row(align=True)
            split.operator("nsolve.refresh_folders", text="", icon='FILE_REFRESH')

        if folder_state.expanded:
            for item in sorted_items:
                full_path = os.path.join(folder_path, item)
                if os.path.isdir(full_path):
                    self.create_folder_subpanel(subbox, full_path)
                elif item.lower().endswith('.blend'):
                    op = subbox.operator("nsolve.load_file", text=item)
                    op.filepath = full_path

    def ndraw_layout(self, layout):
        ndraw = addon.pref().tools.ndraw
        pref = ndraw.ndraw
        maincol = layout.column(align=True)
        box = maincol.box()

        split = box.split(factor=0.7)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(pref, 'enable', text='', icon='TRIA_DOWN' if pref.enable else 'TRIA_RIGHT', emboss=False)
        row.prop(pref, 'enable', text='nDraw        ', emboss=False)

        row = split.row(align=True)
        row.alignment = 'RIGHT'
        row.prop(ndraw, 'pencil_mode', text='', expand=True)

        if pref.enable:
            col = maincol.column(align=True)
            col.prop(ndraw, "snap_vert_radius", text="Snap Vert Radius")


def sort_numerically(items):
    import re

    def alphanum_key(key):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', key)]
    return sorted(items, key=alphanum_key)


def populate_menu(menu, context, path):
    files_and_folders = os.listdir(path)
    sorted_items = sort_numerically(files_and_folders)

    for item in sorted_items:
        full_path = os.path.join(path, item)
        if item.lower().endswith('.blend'):
            menu.layout.operator("nsolve.load_file", text=item).filepath = full_path
