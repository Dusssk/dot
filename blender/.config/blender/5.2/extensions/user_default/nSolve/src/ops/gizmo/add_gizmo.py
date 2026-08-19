
import bpy
from ....utils import addon


class NSOLVE_OT_AddGizmo(bpy.types.Operator):
    bl_idname = "nsolve.add_gizmo"
    bl_label = "Add Gizmo"
    bl_description = "Add new gizmo"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        props = addon.pref().tools.nsuite
        
        # Create new gizmo
        gizmo = props.nsu_gizmos_items.add()
        gizmo.name = f"Gizmo {len(props.nsu_gizmos_items)}"
        gizmo.location = (50, 50)  # Default location
        gizmo.scale = 48  # Default scale
        gizmo.space = 2.5  # Default space
        gizmo.flip = True  # Default flip
        
        # Create empty slots
        for _ in range(75):  # 15 rows x 5 columns
            item = gizmo.list_items.add()
            item.operator = 'none'
        
        # Set as active
        props.nsu_gizmos_index = len(props.nsu_gizmos_items) - 1
        
        return {'FINISHED'}
