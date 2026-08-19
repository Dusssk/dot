import bpy


class NSOLVE_OT_StartDraw(bpy.types.Operator):
    bl_idname = "nsolve.start_draw"
    bl_label = ""
    bl_description = "nDraw"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    tool: bpy.props.EnumProperty(default='NSO', name="Tool", description="Tool", items=[('NSO', 'nSolve', 'nSolve'), ('NSU', 'nSuite', 'nSuite'), ('NFLOW', 'nFlow', 'nFlow'), ('NFLOWOBJ', 'nFlow', 'nFlow')])

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode in {'OBJECT', 'EDIT_MESH'}
        return False

    def execute(self, context):

        obj = context.object
        if obj:
            if obj.mode == 'EDIT':
                bpy.ops.wm.tool_set_by_id(name='nsolve.ndrawtool')
                return {'FINISHED'}

        bpy.ops.object.select_all(action='DESELECT')

        mesh = bpy.data.meshes.new('mesh')
        obj = bpy.data.objects.new('nRetopo', mesh)

        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.wm.tool_set_by_id(name='nsolve.ndrawtool')

        return {'FINISHED'}
