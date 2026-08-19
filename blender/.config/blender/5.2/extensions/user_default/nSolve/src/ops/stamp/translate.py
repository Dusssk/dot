import bpy

from mathutils import Matrix

from ....utils import addon


class NSOLVE_OT_StampTranslate(bpy.types.Operator):
    bl_idname = "nsolve.stamp_translate"
    bl_label = "Stamp Translate"
    bl_description = "Translate Stamp Gizmo"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    start_mouse_pos: list
    delta: list

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':

            mouse_pos = (event.mouse_x, event.mouse_y)

            matris_from_pref = Matrix(addon.pref().tools.stamp.matrix)
            orig_loc, orig_rot, orig_scale = matris_from_pref.decompose()

            new_translation = (mouse_pos[0] - self.delta[0], mouse_pos[1] - self.delta[1], 0)

            # Reconstruct the matrix
            scale_matrix = Matrix.Diagonal(orig_scale.to_4d()).to_4x4()
            rotation_matrix = orig_rot.to_matrix().to_4x4()

            new_translation_matrix = Matrix.Translation(new_translation)

            # Correct order: Apply rotation, then scale, and apply translation last
            reconstructed_matrix = new_translation_matrix @ rotation_matrix @ scale_matrix

            addon.pref().tools.stamp.matrix = flatten(reconstructed_matrix)

            context.area.tag_redraw()

        elif event.type in {'LEFTMOUSE', 'RET'}:
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            matrix = addon.pref().tools.stamp.matrix
            orig_loc, orig_rot, orig_scale = Matrix(matrix).decompose()

            scale_matrix = Matrix.Diagonal(orig_scale.to_4d()).to_4x4()
            rotation_matrix = orig_rot.to_matrix().to_4x4()   
            translation_matrix = Matrix.Translation(orig_loc)

            reconstructed_matrix = translation_matrix @ rotation_matrix @ scale_matrix

            addon.pref().tools.stamp.matrix = flatten(reconstructed_matrix)
            context.area.tag_redraw()

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            # Store initial mouse position
            self.start_mouse_pos = (event.mouse_x, event.mouse_y)

            matris_from_pref = Matrix(addon.pref().tools.stamp.matrix)
            orig_loc, _orig_rot, _orig_scale = matris_from_pref.decompose()

            self.delta = (self.start_mouse_pos[0] - orig_loc[0], self.start_mouse_pos[1] - orig_loc[1])

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "Active space must be a 3D View")
            return {'CANCELLED'}


def flatten(mat):
    dim = len(mat)
    return [mat[j][i] for i in range(dim) for j in range(dim)]