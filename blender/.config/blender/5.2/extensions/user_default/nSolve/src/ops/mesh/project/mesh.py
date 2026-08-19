import bpy


class NSOLVE_OT_ProjectMesh(bpy.types.Operator):
    bl_idname = "nsolve.project_mesh"
    bl_label = "Project Mesh"
    bl_description = "Project Mesh"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def execute(self, context):

        print("Hello World")

        return {'FINISHED'}
