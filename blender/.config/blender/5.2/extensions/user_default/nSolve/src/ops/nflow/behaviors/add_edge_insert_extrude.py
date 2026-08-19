import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *

from .move_verts import Move_Verts
from .slide_verts import Slide_Verts


class Add_Edge_InsertExtrude(NFlowBehavior):
    undo_message = 'Insert/Extrude Edges'

    capabilities = {'SHRINKWRAP', 'SNAP', 'MIRROR'}

    use_auto_shrinkwrap = True

    slide_mode = 'PROPORTIONAL'
    emulate_move_key = 'Z'
    emulate_move = False

    move_behavior = None
    slide_behavior = None

    def invoke(self, context, event):
        if self.elem_type not in ('EDGE', 'EDGE_LOOP'):
            return 'CANCELLED' # other behaviors not implemented yet
        
        self.editors.get(self.obj) # make sure an editor is initialized
        
        if any((not elem.is_wire) for elem in self.elements):
            self.slide_behavior = self.make_behavior(Slide_Verts, context, event, self.elements)
            if self.slide_behavior:
                self.slide_behavior.use_auto_shrinkwrap = self.use_auto_shrinkwrap
                self.slide_behavior.slide_mode = self.slide_mode
        
        if any((elem.is_boundary or elem.is_wire) for elem in self.elements):
            self.move_behavior = self.make_behavior(Move_Verts, context, event, self.elements)
            if self.move_behavior:
                self.move_behavior.use_auto_shrinkwrap = self.use_auto_shrinkwrap
        
        if not (self.slide_behavior or self.move_behavior):
            return 'CANCELLED'
        
        if self.emulate_move_key != 'NONE':
            self.status_text = f'{self.emulate_move_key}: toggle the move mode'
        
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        
        if (event.type == self.emulate_move_key) and (event.value == 'PRESS'):
            self.emulate_move = not self.emulate_move
        
        if (event.type == 'MOUSEMOVE') or (event.value == 'PRESS'):
            self.update_current_state(mouse_pos, event, copy=True)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.update_current_state(mouse_pos, event, copy=False)
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.restore_initial_state()
            return 'CANCELLED'

    def update_current_state(self, mouse_pos, event, copy):
        self.editors.revert_last()
        
        def slide(faces, edges, ref_edges):
            self.slide_behavior.use_snap = self.use_snap
            
            if self.emulate_move:
                self.slide_behavior.on_mousemove(mouse_pos, event)
                return ref_edges
            
            self.slide_behavior.update_data(mouse_pos, event)
            self.slide_behavior.snap_points_dst()
            pos_map = self.make_position_map(self.slide_behavior)
            return self.bisect(faces, edges, ref_edges, pos_map, copy)
        
        def move(ref_edges):
            self.move_behavior.use_snap = self.use_snap
            
            if self.emulate_move:
                self.move_behavior.on_mousemove(mouse_pos, event)
                return ref_edges
            
            self.move_behavior.update_data(mouse_pos, event)
            self.move_behavior.snap_points_dst()
            pos_map = self.make_position_map(self.move_behavior)
            return self.extrude(ref_edges, pos_map)
        
        edge_loop = None
        
        if self.slide_behavior:
            self.slide_behavior.update_data(mouse_pos, None)
            factor = self.slide_behavior.factor
            side = self.slide_behavior.factor_side
            
            edges = self.slide_behavior.edges
            side_edges = self.slide_behavior.side_edges
            side_faces = self.slide_behavior.side_faces
            
            if side_edges[side]:
                edge_loop = slide(side_faces[side], side_edges[side], edges)
            elif self.move_behavior:
                edge_loop = move(edges)
        elif self.move_behavior:
            edge_loop = move(self.elements)
        
        if edge_loop is None:
            return
        
        highlight_edges = [elem for elem in edge_loop if isinstance(elem, BMEdge)]
        NFlow.update_display_data(self.obj, self.elem_type, highlight_edges)
        
        if not copy:
            self.editors.apply()
            
            if self.use_post_select_elements:
                MeshUtil.select_elements({self.bm: edge_loop}, mode=self.post_select_mode)
            
            edge_loop_verts = [elem for elem in edge_loop if isinstance(elem, BMVert)]
            MeshUtil.merge_nearby_verts(self.bm, edge_loop_verts)
        
        self.editors.update_meshes()

    def restore_initial_state(self):
        self.editors.revert()
        
        NFlow.cleanup()
        NFlow.update_scene_ref()

    def make_position_map(self, behavior):
        return {v: p for v, p in zip(behavior.verts, behavior.points_dst)}

    def bisect(self, faces, edges, ref_edges, pos_map, copy):
        editor = self.editor
        bm = editor.bm
        
        faces = list(faces)
        edges = list(edges)
        
        vert_positions = []
        for e in edges:
            v0, v1 = e.verts
            p = pos_map.get(v0)
            if p is None:
                p = pos_map.get(v1)
            vert_positions.append(Vector(p))
        
        affected_geom = set(f for e in edges for f in e.link_faces)
        affected_geom.update(edges)
        
        if copy:
            copy_geom, remap = editor.duplicate(affected_geom, replace='ALL')
            faces = list(remap(faces))
            edges = list(remap(edges))
            ref_edges = set(remap(ref_edges))
        
        result = MeshUtil.insert_edge_loop_parallel(bm, faces, edges, ref_edges)
        new_verts = result['verts']
        new_edges = result['edges']
        new_faces = result['faces']
        edge_loop = result['edge_loop']
        
        if copy:
            editor.add(new_verts)
            editor.add(new_edges)
            editor.add(new_faces)
        
        editor.move(new_verts, vert_positions)
        
        return new_verts + edge_loop

    def extrude(self, ref_edges, pos_map):
        editor = self.editor
        bm = editor.bm
        
        if not isinstance(ref_edges, list):
            ref_edges = list(ref_edges)
        
        result = bmesh.ops.extrude_edge_only(bm, edges=ref_edges)
        elements = result['geom']
        editor.add(elements)
        
        new_verts = []
        edge_loop = []
        
        for elem in elements:
            if isinstance(elem, BMVert):
                new_verts.append(elem)
            elif isinstance(elem, BMEdge):
                if not any((v in pos_map) for v in elem.verts):
                    edge_loop.append(elem)
        
        def get_position(v):
            for e in v.link_edges:
                v2 = e.other_vert(v)
                p = pos_map.get(v2)
                if p is not None:
                    return Vector(p)
        
        editor.move(new_verts, get_position)
        
        return new_verts + edge_loop


NFlow.behaviors['nFlow: Extrude Edges'] = dict(
    type=Add_Edge_InsertExtrude,
    description='Insert (inside) or extrude (outside) a single edge or edge loop',
    cursor='PAINT_BRUSH',
    elements={'EDGE', 'EDGE_LOOP'},
    options=[
        # dict(idname='slide_mode', name='Mode', default='PROPORTIONAL', items=[
        #     ('PROPORTIONAL', 'Proportional'),
        #     ('ABSOLUTE_NEAR', 'Absolute (near)'),
        #     ('ABSOLUTE_FAR', 'Absolute (far)'),
        # ]),
        dict(idname='use_auto_shrinkwrap', name='Allow Auto Shrinkwrap', default=True),
        dict(idname='emulate_move_key', name='Move mode key', default='Z', event=True),
    ],
)
