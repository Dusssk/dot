import bpy
from ....utils import addon
from .set import gizmo_props


class NSOLVE_OT_ScrollGizmo(bpy.types.Operator):
    bl_idname = "nsolve.scroll_gizmo"
    bl_label = "scroll Gizmo"
    bl_description = "Set Gizmo"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    mode: bpy.props.EnumProperty(
        name="Select Mode",
        description="Select Mode",
        items=[
            ('UP', 'Up', 'Up'),
            ('DOWN', 'Down', 'Down'),
        ],
        default='UP'
    )

    gizmo: bpy.props.EnumProperty(name="Gizmo", description="Gizmo", items=gizmo_props, default='JOIN')

    button: str

    @classmethod
    def poll(cls, context):
        if addon.pref().tools.nsolve.main_gizmo_skip_alt:
            return False
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def invoke(self, context, event):

        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSolve")
        return self.execute(context)

    def execute(self, context):

        prop = addon.pref().tools.nsolve

        operators_list = prop.main_gizmo_list_items
        index = prop.main_gizmo_list_index

        if self.mode == 'UP':
            index = (index + 1) % len(operators_list)
        elif self.mode == 'DOWN':
            index = (index - 1) % len(operators_list)

        prop.main_gizmo_list_index = index
        prop.main.operator = operators_list[index].operator
        bpy.ops.nsolve.banner('INVOKE_DEFAULT', operator=prop.main.operator, busy=True)

        return {'FINISHED'}
