import bpy
from ....utils import addon


class NSOLVE_OT_FixGizmo(bpy.types.Operator):
    bl_idname = "nsolve.fix_gizmo"
    bl_label = "Fix Gizmo"
    bl_description = "Fix Gizmo Location if it goes out of bounds"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    gizmo: bpy.props.EnumProperty(name="Gizmo", description="Gizmo", items=[('NSO', 'nSolve', 'nSolve'), ('NSU', 'nSuite', 'nSuite')], default='NSO')

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def execute(self, context):

        if self.gizmo == "NSO":
            nsove = addon.pref().tools.nsolve
            nsove.main_gizmo_location = (15, 60)

        elif self.gizmo == "NSU":
            nsuite = addon.pref().tools.nsuite
            nsuite.ops_gizmo_location = (45, 20)

        return {'FINISHED'}
