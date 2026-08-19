import bpy
from ... import analytics


class NSOLVE_OT_set_nsolve_tool(bpy.types.Operator):
    bl_idname = "nsolve.set_nsolve_tool"
    bl_label = "nSolve"
    bl_description = "Set nSolve as active tool"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="nsolve.nsolvetool")
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSolve")
        analytics.stats("nSuite: Set nSolve")
        return {'FINISHED'}


class NSOLVE_OT_set_nsuite_tool(bpy.types.Operator):
    bl_idname = "nsolve.set_nsuite_tool"
    bl_label = "nSuite"
    bl_description = "Set nSuite as active tool"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="nsolve.nsuitetool")
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        analytics.stats("nSuite: Set nSuite")
        return {'FINISHED'}


class NSOLVE_OT_set_nflow_tool(bpy.types.Operator):
    bl_idname = "nsolve.set_nflow_tool"
    bl_label = "nFlow"
    bl_description = "Set nFlow as active tool"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.wm.tool_set_by_id(name="nsolve.nflow_edit_mode")
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nFlow")
        return {'FINISHED'}


classes = (
    NSOLVE_OT_set_nsolve_tool,
    NSOLVE_OT_set_nsuite_tool,
    NSOLVE_OT_set_nflow_tool,
)
