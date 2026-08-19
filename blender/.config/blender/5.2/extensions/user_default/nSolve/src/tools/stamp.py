from pathlib import Path
import bpy

from .utils import refresh_gizmo
from ...utils import addon


class NSOLVE_MT_Stamp(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'nsolve.stamptool'
    bl_label = 'Stamp'
    bl_description = 'Project the mesh onto the surface'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "tools" / "nstamp").as_posix()
    bl_widget = 'NSOLVE_GGT_Stamp'
    bl_keymap = (
        ('nsolve.project_mesh', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):

        layout.popover("NSOLVE_PT_NsolveStamp", text="", icon='OPTIONS')

        layout.separator_spacer()

        layout.menu("NSOLVE_MT_SelectMenu", text="Select")
        layout.menu("NSOLVE_MT_VertMenu", text="Vert")
        layout.menu("NSOLVE_MT_EdgeMenu", text="Edge")
        layout.menu("NSOLVE_MT_FaceMenu", text="Face")


class NSOLVE_PT_NsolveStamp(bpy.types.Panel):
    bl_label = "N'Solve"
    bl_idname = 'NSOLVE_PT_NsolveStamp'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'


    def draw(self, context):
        props = addon.pref().tools.stamp

        layout = self.layout
        layout.use_property_split = True

        layout.label(text='Options')
        layout.separator()

        layout.label(text='Stamps')

        col = layout.column(align=True)
        row = col.row()
        row.template_list('NSOLVE_UL_StampGizmoList', '', props, 'list_items', props, 'list_index', rows=14)


class NSOLVE_UL_StampGizmoList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        if item:
            layout.label(text=item.name, translate=False)

    def draw_filter(self, context, layout):
        pass


class NsolveStampGizmoList(bpy.types.PropertyGroup):
    # Store the type of modifier
    name: bpy.props.StringProperty(name="Name", description="Name", default="", update=refresh_gizmo)


class types():
    class pref(bpy.types.PropertyGroup):
        matrix:  bpy.props.FloatVectorProperty(
            name="Gizmo Matrix",
            description="Store a 4x4 transformation matrix",
            size=16,
            default=(20.0, 0.0, 0.0, 0.0,
                     0.0, 20.0, 0.0, 0.0,
                     0.0, 0.0, 1.0, 0.0,
                     400.0, 400.0, 0.0, 1.0),
            subtype='MATRIX',
            update=refresh_gizmo
        )
        hide: bpy.props.BoolProperty(name="Hide", description="Hide", default=False, update=refresh_gizmo)
        list_items: bpy.props.CollectionProperty(type=NsolveStampGizmoList)
        list_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)


types_classes = (
    NsolveStampGizmoList,
    NSOLVE_UL_StampGizmoList,
    types.pref,
)


classes = (
    NSOLVE_PT_NsolveStamp,
)