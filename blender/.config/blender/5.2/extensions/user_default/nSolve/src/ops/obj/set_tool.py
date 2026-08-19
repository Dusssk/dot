import bpy
from ... import analytics


class NSOLVE_OT_SetActiveTool(bpy.types.Operator):
    bl_idname = "nsolve.set_activetool"
    bl_label = ""
    bl_description = "Set tool"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    tool: bpy.props.EnumProperty(default='NSO', name="Tool", description="Tool", items=[('NSO', 'nSolve', 'nSolve'), ('NSU', 'nSuite', 'nSuite'), ('NFLOW', 'nFlow', 'nFlow'), ('NFLOWOBJ', 'nFlow', 'nFlow')])
    description: bpy.props.StringProperty(name="Description", description="Description", default="")

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode in {'OBJECT', 'EDIT_MESH'}
        return False
    
    @classmethod
    def description(cls, context, properties):
        return properties.description

    def execute(self, context):

        # Check if there are any selected objects
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        active_object = bpy.context.active_object

        name = 'nsolve.nsolvetool' if self.tool == 'NSO' else 'nsolve.nsuitetool' if self.tool == 'NSU' else 'nsolve.nflow_edit_mode' if self.tool == 'NFLOW' else 'nsolve.nflow_object_mode'

        if active_object and active_object.mode == 'OBJECT':
            if self.tool in {'NFLOW', 'NSU', 'NSO'}:
                if selected_objects:
                    for obj in selected_objects:
                        context.view_layer.objects.active = obj
                        bpy.ops.wm.tool_set_by_id(name='builtin.select_box')
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.wm.tool_set_by_id(name=name)
                else:
                    self.report({'ERROR'}, "Pick a mesh object")
            else:
                bpy.ops.wm.tool_set_by_id(name=name)
        else:
            bpy.ops.wm.tool_set_by_id(name=name)
        
        analytics.stats(f"nSuite: Set tool {self.tool}")
        return {'FINISHED'}
