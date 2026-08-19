import bpy
import bmesh


class NSOLVE_OT_PencilExtrude(bpy.types.Operator):
    bl_idname = "nsolve.pencilextrude"
    bl_label = "Draw Vertex"
    bl_description = "Draw a new vertex"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'GRAB_CURSOR', 'INTERNAL'}

    v_id: bpy.props.IntProperty(name="Vertex ID")

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def execute(self, context):
        # Ensure we are working with a mesh in edit mode
        obj = context.active_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Get the vert if self.v_id
        vert = bm.verts[self.v_id]

        if not isinstance(vert, bmesh.types.BMVert):
            self.report({'WARNING'}, "No active vertex selected")
            return {'CANCELLED'}

        selected_verts = [v for v in bm.verts if v.select]
        for v in selected_verts:
            v.select = False
        vert.select = True
        selected_verts.append(vert)

        # Update the mesh with the new geometry
        bmesh.update_edit_mesh(mesh)

        bpy.ops.mesh.extrude_context_move('INVOKE_DEFAULT')

        for v in selected_verts:
            v.select = True

        return {'FINISHED'}
