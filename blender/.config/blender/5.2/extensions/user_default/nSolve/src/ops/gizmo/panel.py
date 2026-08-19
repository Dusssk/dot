import bpy
from ....utils import addon

class NSOLVE_OT_CallPanel(bpy.types.Operator):
    bl_idname = "nsolve.call_panel"
    bl_label = "Call NSO Panel"
    bl_description = "Open the NSO panel"
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
        bpy.ops.wm.call_panel(name="NSOLVE_PT_Nsolve")
        return {'FINISHED'}


