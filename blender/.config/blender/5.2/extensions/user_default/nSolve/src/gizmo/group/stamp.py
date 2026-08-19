import bpy

from mathutils import Matrix


from ..types import move
from ....utils import addon


class NSOLVE_GGT_Stamp(bpy.types.GizmoGroup):
    bl_idname = 'NSOLVE_GGT_Stamp'
    bl_label = 'Nsolve Stamp Gizmo'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_region_type = 'WINDOW'
    bl_options = {'SCALE'}

    move_gizmo: move.Draw
    scale_gizmo: move.Draw
    rotate_gizmo: move.Draw

    @classmethod
    def poll(cls, context):
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        nsolve_tool = True if active_tool and active_tool.idname == 'nsolve.stamptool' else False
        return context.space_data.show_gizmo_tool and context.edit_object and nsolve_tool

    def setup(self, context):
        self.setup_matrix_gizmos(context)

    def refresh(self, context):

        stamp = addon.pref().tools.stamp
        original_matrix = Matrix(stamp.matrix)

        self.move_gizmo.update(original_matrix)
        self.scale_gizmo.update(original_matrix)
        self.rotate_gizmo.update(original_matrix)

    def setup_matrix_gizmos(self, context):

        # Retrieve the existing matrix from the preferences
        stamp = addon.pref().tools.stamp
        original_matrix = Matrix(stamp.matrix)
        matrix = flatten(original_matrix)

        # print(original_matrix)
        # print(matrix)

        self.move_gizmo = move.Draw(self, original_matrix, color=(1, 1, 1), alpha=0.4, scale_basis=1, line_width=2.0, draw_options={'FILL_SELECT'})
        self.move_gizmo.operator('nsolve.stamp_translate')
        self.scale_gizmo = move.Draw(self, original_matrix, color=(1, 1, 1), alpha=0.4, scale_basis=2, line_width=1.0, draw_options={'FILL_SELECT'})
        self.rotate_gizmo = move.Draw(self, original_matrix, color=(0, 0, 1), alpha=0.4, scale_basis=3, line_width=1.0, draw_options={'FILL_SELECT'})


def flatten(mat):
    dim = len(mat)
    return [mat[j][i] for i in range(dim) for j in range(dim)]
