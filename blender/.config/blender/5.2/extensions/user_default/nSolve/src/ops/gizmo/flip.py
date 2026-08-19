import bpy
from ....utils import addon

class NSOLVE_OT_FlipGizmo(bpy.types.Operator):
    bl_idname = "nsolve.flip_gizmo"
    bl_label = "Flip Gizmo"
    bl_description = "Flip the gizmo orientation"
    bl_options = {'REGISTER', 'INTERNAL'}

    gizmo: bpy.props.EnumProperty(
        name="Gizmo",
        description="Gizmo",
        items=[
            ('NSO', 'nSuite', 'nSuite'),
            ('NSU', 'nSuite', 'nSuite')
        ],
        default='NSO'
    )

    def execute(self, context):
        if self.gizmo == 'NSO':
            props = addon.pref().tools.nsolve
            props.main_gizmo_flip = not props.main_gizmo_flip
        else:
            props = addon.pref().tools.nsuite
            if len(props.nsu_gizmos_items) > 0:
                gizmo = props.nsu_gizmos_items[props.nsu_gizmos_index]
                gizmo.flip = not gizmo.flip
        
        return {'FINISHED'}
