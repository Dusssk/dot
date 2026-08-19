import bpy
from ....utils import addon


class NSOLVE_OT_ExpandGizmo(bpy.types.Operator):
    bl_idname = "nsolve.expand_gizmo"
    bl_label = "Expand Gizmo"
    bl_description = "Expand Gizmo"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def execute(self, context):

        esxpand = addon.pref().tools.nsolve.expanded

        if esxpand:
            addon.pref().tools.nsolve.expanded = False
        else:
            addon.pref().tools.nsolve.expanded = True

        context.area.tag_redraw()

        return {'FINISHED'}
