import bpy
from ....utils import addon


class NSOLVE_OT_RemoveGizmo(bpy.types.Operator):
    bl_idname = "nsolve.remove_gizmo"
    bl_label = "Remove Gizmo"
    bl_description = "Remove gizmo"
    bl_options = {'REGISTER', 'INTERNAL'}

    gizmo_index: bpy.props.IntProperty()

    def execute(self, context):
        props = addon.pref().tools.nsuite
        
        # Check if index is valid
        if len(props.nsu_gizmos_items) <= self.gizmo_index:
            return {'CANCELLED'}
            
        # Remove the gizmo
        props.nsu_gizmos_items.remove(self.gizmo_index)
        
        # Update the active index if needed
        if props.nsu_gizmos_index >= len(props.nsu_gizmos_items):
            props.nsu_gizmos_index = max(0, len(props.nsu_gizmos_items) - 1)
            
        return {'FINISHED'}
