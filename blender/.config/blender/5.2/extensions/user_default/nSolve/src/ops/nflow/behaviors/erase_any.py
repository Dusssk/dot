import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *


class Erase_Any(NFlowBehavior):
    undo_message = 'Erase Elements'

    mode = 'DELETE'
    dissolve_2_val = True

    element_names = {
        'NONE': 'Elements',
        'VERTEX': 'Vertices',
        'EDGE': 'Edges',
        'FACE': 'Faces',
        'EDGE_LOOP': 'Edge Loops',
        'PERIMETER': 'Perimeter',
        'BOUNDARY': 'Boundary',
    }

    mode_names = {
        'DELETE': 'Delete',
        'DISSOLVE': 'Dissolve',
        'COLLAPSE': 'Collapse',
    }

    def invoke(self, context, event):
        self.merge_point = None
        
        self.target_infos = {}
        
        NFlow.cleanup()
        NFlow.update_scene_ref()
        
        if not self.mark_elements():
            return 'CANCELLED'
        
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            # Note: may need to resample the trajectory at small steps?
            # (though this could be prohibitive performance-wise)
            mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            if self.elem_type_start != 'NONE':
                elem_type = self.elem_type_start
            else:
                elem_type = {'VERTEX', 'EDGE', 'FACE'}
            obj, bm, elem_type, elements = find_closest_mesh_element(context, mouse_pos, elem_type)
            self.set_target(obj, bm, elem_type, elements)
            self.mark_elements()
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.erase_elements(context)
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            return 'CANCELLED'

    def erase_elements(self, context):
        element_name = self.element_names[self.elem_type_start]
        mode_name = self.mode_names[self.mode]
        self.undo_message = f'{mode_name} {element_name}'
        
        bm_elements = {}
        
        for obj, target_info in self.target_infos.items():
            bm = target_info['bm']
            elements = target_info['elements']
            
            if self.dissolve_2_val:
                verts = []
                for elem in elements:
                    if isinstance(elem, BMVert):
                        verts.append(elem)
                    else:
                        verts.extend(elem.verts)
            
            vertex = None
            
            if self.mode == 'DELETE':
                MeshUtil.delete_elements(bm, elements)
            elif self.mode == 'DISSOLVE':
                MeshUtil.dissolve_elements(bm, elements)
            elif self.mode == 'COLLAPSE':
                # Note: may return None if trying to collapse a vertex
                vertex = MeshUtil.collapse_elements(bm, elements, self.merge_point)
            
            if self.dissolve_2_val:
                verts = {v for v in verts if v.is_valid and (len(v.link_edges) == 2)}
                if verts: # verts must be unique
                    bmesh.ops.dissolve_verts(bm, verts=list(verts))
            
            if (vertex is not None) and vertex.is_valid:
                self.raycaster.snap_verts_to_surface(obj, [vertex])
                bm_elements.setdefault(bm, []).append(vertex)
        
        if self.use_post_select_elements:
            MeshUtil.select_elements(bm_elements, mode=self.post_select_mode)
        
        for obj, target_info in self.target_infos.items():
            mesh = obj.data
            bmesh.update_edit_mesh(mesh)

    def mark_elements(self):
        self.merge_point = None
        
        is_empty = not (self.obj and self.elements)
        if self.elem_type_start != 'NONE':
            if (self.elem_type != self.elem_type_start) or is_empty:
                return False
        elif is_empty:
            return True
        
        target_info = self.target_infos.get(self.obj)
        if not target_info:
            target_info = dict(bm=self.bm, elements=set())
            self.target_infos[self.obj] = target_info
        
        if self.elem_type == 'VERTEX':
            self.merge_point = Vector(self.elements[0].co)
        
        elements = target_info['elements']
        new_elements = set(self.elements).difference(elements)
        elements.update(new_elements)
        
        matrix = self.obj.matrix_world
        NFlow.add_elements(matrix, new_elements)
        
        return bool(new_elements)


NFlow.behaviors['nFlow: Erase Geometry'] = dict(
    type=Erase_Any,
    description='Mark and erase mesh elements',
    cursor='ERASER',
    elements={'VERTEX', 'EDGE', 'EDGE_LOOP', 'BOUNDARY', 'PERIMETER', 'FACE'},
    options=[
        dict(idname='mode', name='Mode', default='DISSOLVE', items=[
            ('DELETE', 'Delete'),
            ('DISSOLVE', 'Dissolve'),
            ('COLLAPSE', 'Collapse'),
        ]),
        dict(idname='dissolve_2_val', name='Dissolve 2-valence verts', default=True),
    ],
)
