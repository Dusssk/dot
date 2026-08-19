import bpy

from ... import analytics


class NSOLVE_OT_SetTool(bpy.types.Operator):
    bl_idname = "nsolve.set_tool"
    bl_label = "Set nSolve"
    bl_description = "Set tool"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    tool: bpy.props.StringProperty(name="Tool", description="Tool", default='NSO')

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def execute(self, context):

        if self.tool == 'NSO':
            bpy.ops.wm.tool_set_by_id(name="nsolve.nsolvetool")
        elif self.tool == 'NSU':
            bpy.ops.wm.tool_set_by_id(name="nsolve.nsuitetool")

        analytics.stats(f"nSuite: Set tool {self.tool}")
        return {'FINISHED'}
