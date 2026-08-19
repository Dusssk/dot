from pathlib import Path
from .utils import refresh_gizmo
import bpy

from ...utils import addon


class NSOLVE_MT_Ndraw(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'nsolve.ndrawtool'
    bl_label = 'nDraw'
    bl_description = 'nDraw tool'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "tools" / "npencil").as_posix()
    bl_widget = 'NSOLVE_GGT_Ndraw'
    bl_keymap = (
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': [('mode', 'SET')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'ctrl': True}, {'properties': [('mode', 'SUB')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True}, {'properties': [('mode', 'ADD')]}),
        ('nsolve.ndraw_draw', {'type': 'LEFT_CTRL', 'value': 'PRESS'}, {'properties': []}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):
        ndraw = addon.pref().tools.ndraw

        row = layout.row(align=True)
        row.prop(ndraw, "pencil_mode", text="", expand=True)
        text = "Edge" if ndraw.pencil_mode == 'EDGE' else "Quad"
        box = row.box()
        box.label(text=text)

        if addon.pref().menus:
            layout.separator_spacer()

            if addon.pref().menus_type == 'SEPARATED':
                layout.menu("NSOLVE_MT_SelectMenu", text="Select")
                layout.menu("NSOLVE_MT_VertMenu", text="Vert")
                layout.menu("NSOLVE_MT_EdgeMenu", text="Edge")
                layout.menu("NSOLVE_MT_FaceMenu", text="Face")

            else:
                layout.menu("NSOLVE_MT_MainMenu", text="Menu")


class NdrawPanelPref(bpy.types.PropertyGroup):
    hide: bpy.props.BoolProperty(name="Hide", description="Hide", default=True, update=refresh_gizmo)
    enable: bpy.props.BoolProperty(name="Enable NSU", description="Enable NSU", default=False)
    layout: bpy.props.BoolProperty(name="Layout", description="Layout", default=True)


class types():
    class pref(bpy.types.PropertyGroup):
        running: bpy.props.BoolProperty(name="Running", default=False, update=refresh_gizmo)
        pencil_mode: bpy.props.EnumProperty(name="Mode", items=[('EDGE', "", "Draw Edge From SElected Verts", 'IPO_LINEAR', 0), ('QUAD', "", "Draw Quad From Selected Edge", 'MESH_PLANE', 1)], default='QUAD', update=refresh_gizmo)
        snap_edge_radius: bpy.props.FloatProperty(name="Snap Edge Radius", default=800, min=1, precision=2)
        snap_vert_radius: bpy.props.FloatProperty(name="Snap Vert Radius", default=80, min=1, precision=2)

        ndraw: bpy.props.PointerProperty(type=NdrawPanelPref)


types_classes = (
    NdrawPanelPref,
    types.pref,
)
