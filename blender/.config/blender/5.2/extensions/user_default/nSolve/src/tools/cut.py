from pathlib import Path
import bpy

from ...utils import addon
from ... import bl_info


class NSOLVE_MT_Cut(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'nsolve.cut_tool'
    bl_label = "nCut"
    bl_description = f'version: {bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "tools" / "ncut").as_posix()
    bl_widget = ''
    bl_keymap = (
        ('nsolve.hard_loop_cut', {'type': 'R', 'value': 'PRESS', 'alt': True}, {'properties': []}),
        ('nsolve.mesh_cut', {'type': 'LEFTMOUSE', 'value': 'PRESS'}, {'properties': [('tool', True)]}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )


    def draw_settings(context, layout, tool):

        tool = addon.pref().tools.cut
        layout.prop(tool, "mode", text="Mode", expand=True)

        if addon.pref().menus:
            layout.separator_spacer()

            layout.menu("NSOLVE_MT_SelectMenu", text="Select")
            layout.menu("NSOLVE_MT_VertMenu", text="Vert")
            layout.menu("NSOLVE_MT_EdgeMenu", text="Edge")
            layout.menu("NSOLVE_MT_FaceMenu", text="Face")


class types():
    class pref(bpy.types.PropertyGroup):
        mode: bpy.props.EnumProperty(name="Mode", description="Mode", items=[('CUT', 'Cut', 'Cut'), ('SLICE', 'Slice', 'Slice')], default='CUT')


types_classes = (
    types.pref,
)
