import bpy
from ....utils import addon


class NSOLVE_OT_SwapMode(bpy.types.Operator):
    bl_idname = "nsolve.swap_mode"
    bl_label = "Start nSolve"
    bl_description = "Start nSolve"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    tool: bpy.props.EnumProperty(default='NSO', name="Tool", description="Tool", items=[('NSO', 'nSolve', 'nSolve'), ('NSU', 'nSuite', 'nSuite'), ('NFLOW', 'nFlow', 'nFlow')])

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode in {'OBJECT', 'EDIT_MESH'}
        return False

    def execute(self, context):

        # Check if there are any selected objects
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        name = 'nsolve.nsolvetool' if self.tool == 'NSO' else 'nsolve.nsuitetool' if self.tool == 'NSU' else 'nsolve.nflow_edit_mode'

        if selected_objects:
            for obj in selected_objects:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.wm.tool_set_by_id(name='builtin.select_box')
                if obj.mode == 'OBJECT':
                    bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.wm.tool_set_by_id(name=name)

        else:
            bpy.ops.wm.tool_set_by_id(name='builtin.select_box')

        return {'FINISHED'}
