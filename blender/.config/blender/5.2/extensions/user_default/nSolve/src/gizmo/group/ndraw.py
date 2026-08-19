import bmesh
import bpy

from mathutils import Matrix

# Assuming the relative imports work in your project structure
from ..types import move, face
from ...ops.ndraw import loops

from ....utils import addon


class NSOLVE_GGT_Ndraw(bpy.types.GizmoGroup):
    bl_idname = 'NSOLVE_GGT_Ndraw'
    bl_label = 'nDraw Gizmo'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SHOW_MODAL_ALL'}


    @classmethod
    def poll(cls, context):
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        pecil_tool = True if active_tool and active_tool.idname == 'nsolve.ndrawtool' else False
        return context.space_data.show_gizmo_tool and context.edit_object and pecil_tool

    def setup(self, context):
        context.space_data.overlay.show_retopology = True

    def refresh(self, context):
        pass

    def tris_gizmos(self):

        ndraw = addon.pref().tools.ndraw
        point = ndraw.point
        mouse_gizmo = move.Draw(self, Matrix.Translation(point), (0, 0, 8), 0.8, 0.05, hide_select=True, draw_options={'FILL', 'ALIGN_VIEW'})
