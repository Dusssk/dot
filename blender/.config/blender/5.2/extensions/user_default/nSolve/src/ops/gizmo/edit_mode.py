import bpy
from ....utils import addon


class NSOLVE_OT_ToggleEditMode(bpy.types.Operator):
    bl_idname = "nsolve.toggle_edit_mode"
    bl_label = "Toggle Edit Mode"
    bl_description = "Toggle gizmo edit mode"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        props = addon.pref().tools.nsuite
        props.nsu_edit_mode = not props.nsu_edit_mode
        return {'FINISHED'}
