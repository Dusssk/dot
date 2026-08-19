import bpy
from ....utils import addon

class NSOLVE_OT_EditGizmo(bpy.types.Operator):
    bl_idname = "nsolve.edit_gizmo"
    bl_label = "Edit Gizmo"
    bl_description = "Edit the gizmo"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        props = addon.pref().tools.nsuite
        props.nsu_edit_mode = not props.nsu_edit_mode

        return {'FINISHED'}
