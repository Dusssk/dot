import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *


class Relax_Verts(NFlowBehavior):
    undo_message = 'Relax Geometry'

    capabilities = {'SHRINKWRAP'}

    mode = 'ALL'
    shrinkwrap_only = False
    use_sharp = False
    use_seam = False

    def init(self, context, event):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        self.relax_speed = nflow_config_workspace.relax_speed

    def invoke(self, context, event):
        NFlow.cleanup()
        NFlow.update_scene_ref()
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.update_vertex_positions(context, event, mouse_pos)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.editors.revert()
            return 'CANCELLED'

    def update_vertex_positions(self, context, event, mouse_pos):
        if self.elem_type == 'FACE':
            elem_type = 'FACE'
            obj, bm, elem_type, elements = find_closest_mesh_element(context, mouse_pos, elem_type)
        else:
            obj, bm, elem_type, elements = self.obj, self.bm, self.elem_type, self.elements
        
        if not obj:
            return
        
        editor = self.editors.get(obj)
        
        factor = self.relax_speed
        
        verts = []
        target_positions = []
        
        for v in self.filter_vertices(elements):
            p = self.calc_smoothed_position(v, factor)
            if p is not None:
                verts.append(v)
                target_positions.append(p)
        
        editor.move(verts, target_positions)
        
        self.raycaster.snap_verts_to_surface(obj, verts)
        
        editor.update_mesh()
        
        NFlow.cleanup()
        NFlow.update_scene_ref()
        
        matrix = obj.matrix_world
        NFlow.add_elements(matrix, verts)

    def filter_vertices(self, elements):
        use_all = (self.mode == 'ALL')
        use_boundary = (self.mode == 'BOUNDARY')
        use_sharp = self.use_sharp
        use_seam = self.use_seam
        
        def is_vert_boundary(v):
            return v.is_boundary
        
        def is_edge_boundary(e):
            return e.is_boundary or (use_sharp and (not e.smooth)) or (use_seam and e.seam)
        
        for v in MeshUtil.gather_verts(elements):
            if v.hide:
                continue
            
            if not use_all:
                is_boundary = is_vert_boundary(v) or any(is_edge_boundary(e) for e in v.link_edges)
                if is_boundary != use_boundary:
                    continue
            
            yield v

    def calc_smoothed_position(self, v, factor):
        if self.shrinkwrap_only:
            return v.co
        
        p = Vector()
        count = 0
        for e in v.link_edges:
            if not e.hide:
                p += e.other_vert(v).co
                count += 1
        return (v.co.lerp(p / count, factor) if count > 0 else None)


def settings_draw(option_infos):
    def draw(layout, context):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        
        layout.prop(nflow_config_workspace, 'relax_speed')
    
    return draw


NFlow.behaviors['nFlow: Relax Geometry'] = dict(
    type=Relax_Verts,
    description='Smooth the vertex positions',
    cursor='COPY',
    elements={'VERTEX', 'EDGE', 'EDGE_LOOP', 'BOUNDARY', 'PERIMETER', 'FACE'},
    options=[
        dict(idname='mode', name='Mode', default='INNER', items=[
            ('INNER', 'Inner'),
            ('BOUNDARY', 'Boundary'),
            ('ALL', 'All'),
        ]),
        dict(idname='shrinkwrap_only', name='Shrinkwrap only', default=False),
        dict(idname='use_sharp', name='Sharp is boundary', default=False),
        dict(idname='use_seam', name='Seam is boundary', default=False),
    ],
    settings_label='Relax Geometry',
    settings_draw=settings_draw,
)
