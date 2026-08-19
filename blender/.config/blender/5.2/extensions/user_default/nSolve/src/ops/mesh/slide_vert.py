import bpy
import bmesh

from ....utils.nmesh import Nmesh
from ... import analytics


class NSOLVE_OT_SlideVert(bpy.types.Operator):
    bl_idname = "nsolve.slide_vert"
    bl_label = "Slide Vert"
    bl_description = f"{bl_label}\n\nSlide vertex along the edge"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    selection_mode: bpy.props.EnumProperty(items=(('CONTEXT', '' ,''), ('VERT', '' ,''), ('EDGE', '' ,'')), default='CONTEXT')
    multi_elem: bpy.props.BoolProperty(default=False)

    bm: bmesh.types.BMesh = None
    nm: Nmesh = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        nm = Nmesh.from_bmesh(context, bm, obj)

        select_mode = context.tool_settings.mesh_select_mode[:]
        if self.selection_mode == 'EDGE' or (self.selection_mode == 'CONTEXT' and select_mode[1]):
            nm.detect_element(event, mode=(False, True, False))
            if nm.element[0] == 'EDGE':
                edge = nm.element[1]

                if not edge.select or not self.multi_elem: bpy.ops.mesh.select_all(action='DESELECT')
                edge.select = True

                bpy.ops.transform.edge_slide('INVOKE_DEFAULT')

                return {'FINISHED'}

        if not (self.selection_mode == 'VERT' or (self.selection_mode == 'CONTEXT' and select_mode[0])):
            return {'CANCELLED'}

        nm.detect_element(event, mode=(True, False, False))

        vert = nm.element[1]

        if not vert:
            return {'CANCELLED'}

        if not vert.select or not self.multi_elem:bpy.ops.mesh.select_all(action='DESELECT')
        vert.select = True

        bpy.ops.transform.vert_slide('INVOKE_DEFAULT')
        analytics.stats("nSolve: Slide Vert")
        return {'FINISHED'}