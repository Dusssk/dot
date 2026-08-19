import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *

from .move_verts import Move_Verts


class Slide_Verts(Move_Verts):
    undo_message = 'Slide Elements'

    slide_mode = 'PROPORTIONAL'
    abs_slide_pref = 'NEAR'

    def initialize_data(self, mouse_pos):
        if self.elem_type not in ('EDGE', 'EDGE_LOOP'):
            return False # other behaviors not implemented yet
        
        self.gather_rails()
        
        if self.edges:
            if self.slide_dir is None:
                return False
            
            element_sets = [(self.obj, self.edges)]
            origin3d = self.raycaster.nearest_along_ray(mouse_pos, element_sets, use_raycast=False)[0]
            if origin3d is None:
                return False
            
            origin2d = self.raycaster.project(origin3d)
            if origin2d is None:
                return False
            
            self.screen_offset = origin2d - mouse_pos
        else:
            self.screen_offset = Vector((0, 0))
        
        self.mouse_pos_start = Vector(mouse_pos)
        
        self.factor = 0
        self.factor_side = 0
        
        self.status_text = f'E: proportional or absolute, F: near or far edge (if absolute)'
        
        return True

    def update_data(self, mouse_pos, event):
        self.process_event(event)
        
        factor, factor_side = self.calculate_factor(mouse_pos)
        
        self.slide(factor, factor_side)

    def process_event(self, event):
        if event is None:
            return
        
        if (event.type == 'E') and (event.value == 'PRESS'):
            if self.slide_mode != 'PROPORTIONAL':
                self.slide_mode = 'PROPORTIONAL'
            else:
                if self.abs_slide_pref == 'NEAR':
                    self.slide_mode = 'ABSOLUTE_NEAR'
                else:
                    self.slide_mode = 'ABSOLUTE_FAR'
            self.overridden_options.add('slide_mode')
        elif (event.type == 'F') and (event.value == 'PRESS'):
            if self.abs_slide_pref == 'NEAR':
                self.abs_slide_pref = 'FAR'
            else:
                self.abs_slide_pref = 'NEAR'
            
            if self.slide_mode != 'PROPORTIONAL':
                if self.abs_slide_pref == 'NEAR':
                    self.slide_mode = 'ABSOLUTE_NEAR'
                else:
                    self.slide_mode = 'ABSOLUTE_FAR'
            self.overridden_options.add('slide_mode')

    def calculate_factor(self, mouse_pos):
        offset = mouse_pos - self.mouse_pos_start
        factor = self.slide_dir.dot(offset)
        factor_side = (-1 if factor < 0 else 1)
        scale = self.sides_scale[factor_side]
        
        if self.slide_mode != 'PROPORTIONAL':
            scale *= self.range_infos[factor_side]['scale']
        
        factor = divide01(factor, scale)
        
        self.factor = factor
        self.factor_side = factor_side
        
        return factor, factor_side

    def slide(self, factor, factor_side):
        factor_ranges = self.range_infos[factor_side]['ranges']
        
        def get_opposite(rails):
            for p1, n1, side in rails:
                if factor_side == side:
                    return (p1, n1)
        
        for i in range(len(self.points_src)):
            p0 = self.points_src[i]
            n0 = self.normals_src[i]
            
            opposite = get_opposite(self.rails[i])
            if opposite is None:
                self.points_dst[i] = p0
                continue
            
            p1, n1 = opposite
            if n1.dot(n0) < 0:
                n1 = -n1
            
            factor_range = (factor_ranges[i] if factor_ranges else 0.0)
            
            if self.slide_mode == 'ABSOLUTE_NEAR':
                rail_factor = factor * factor_range
            elif self.slide_mode == 'ABSOLUTE_FAR':
                rail_factor = factor * factor_range + (1 - factor_range)
            else:
                rail_factor = factor
            
            self.points_dst[i] = p0.lerp(p1, rail_factor)
            self.directions[i] = n0.lerp(n1, rail_factor)

    def gather_rails(self):
        self.edges = MeshUtil.gather_edges(self.elements)
        self.edge0 = next(iter(elem for elem in self.elements
            if isinstance(elem, BMEdge)), None)
        self.edges_sorted = MeshUtil.sort_loop_edges(self.edges)
        
        face_sides = self.calc_face_sides()
        
        self.calc_edge_projection(face_sides)
        
        sides_distances = {-1: [], 1: []}
        
        self.rails = []
        for v in self.verts:
            sides_distance = {-1: 0.0, 1: 0.0}
            rails = []
            for e, side in self.gather_vertex_rails(v, face_sides).items():
                v2 = e.other_vert(v)
                rails.append((Vector(v2.co), Vector(v2.normal), side))
                if side != 0:
                    sides_distance[side] = (v2.co - v.co).magnitude
            self.rails.append(rails)
            
            # We need to make sure that distances match the vertices
            for side, distance in sides_distance.items():
                sides_distances[side].append(distance)
        
        self.range_infos = {}
        for side, distances in sides_distances.items():
            min_dist = (min(distances) if distances else 0.0)
            factor_ranges = [divide01(min_dist, d) for d in distances]
            scale = divide01(min_dist, self.sides_scale_3d[side])
            self.range_infos[side] = {'scale': scale, 'ranges': factor_ranges}

    def calc_edge_projection(self, face_sides):
        self.slide_dir = None
        self.sides_scale = None
        self.sides_scale_3d = None
        self.sides_exist = None
        self.side_edges = None
        self.side_faces = None
        
        if self.edge0 is None:
            return
        
        editor = self.editor
        matrix = editor.world_matrix_p
        
        edge_prj = self.raycaster.project_edge(matrix, *self.edge0.verts)
        if edge_prj is None:
            return
        
        (v0_3d, v0_2d), (v1_3d, v1_2d) = edge_prj
        
        slide_dir = (v1_2d - v0_2d).orthogonal().normalized()
        
        side_points = {-1: [], 1: []}
        for l in self.edge0.link_loops:
            side = face_sides.get(l.face)
            if side:
                l_prev = l.link_loop_prev
                if l_prev.edge != l.edge:
                    side_points[side].append(matrix @ l_prev.vert.co)
                l_next = l.link_loop_next.link_loop_next
                if l_next.edge != l.edge:
                    side_points[side].append(matrix @ l_next.vert.co)
        
        sides_scale = {-1: 0, 1: 0}
        sides_scale_3d = {-1: 0, 1: 0}
        
        for side, points in side_points.items():
            scale_total = 0.0
            scale_total_3d = 0.0
            scale_count = 0
            for p3d in points:
                p2d = self.raycaster.project(p3d)
                if p2d is not None:
                    scale_total += slide_dir.dot(p2d - v0_2d)
                    scale_total_3d += (p3d - v0_3d).magnitude
                    scale_count += 1
            
            if scale_count > 0:
                sides_scale[side] = scale_total / scale_count
                sides_scale_3d[side] = scale_total_3d / scale_count
        
        min_scale = 10.0
        def sanitize(value, sign):
            return math.copysign(max(abs(value), min_scale), sign)
        
        if (sides_scale[1] < 0) or (sides_scale[-1] > 0):
            slide_dir = -slide_dir
        sides_scale[1] = sanitize(sides_scale[1], 1)
        sides_scale[-1] = sanitize(sides_scale[-1], -1)
        
        side_edges = {-1: set(), 1: set()}
        side_faces = {-1: set(), 1: set()}
        for e in self.edges:
            e_verts = set(e.verts)
            for f in e.link_faces:
                side = face_sides.get(f)
                if not side:
                    continue
                side_faces[side].add(f)
                side_edges[side].update(e2 for e2 in f.edges
                    if (e2 != e) and not e_verts.isdisjoint(e2.verts))
        
        self.slide_dir = slide_dir
        self.sides_scale = sides_scale
        self.sides_scale_3d = sides_scale_3d
        self.sides_exist = {side: bool(points) for side, points in side_points.items()}
        self.side_edges = side_edges
        self.side_faces = side_faces

    def calc_face_sides(self):
        face_sides = {}
        
        if not self.edges:
            return face_sides
        
        e = self.edge0
        e_faces = list(e.link_faces)
        fc = len(e_faces)
        
        if (fc < 1) or (fc > 2):
            return face_sides
        
        face_sides[e_faces[0]] = 1
        if fc > 1:
            face_sides[e_faces[1]] = -1
        
        processed = set()
        wavefront = set()
        
        def add_to_wavefront(e):
            processed.add(e)
            wavefront.update(e2 for v in e.verts for e2 in v.link_edges
                if (e2 in self.edges) and (e2 not in processed))
        
        def propagate_face_side(f):
            if f in face_sides:
                return
            for e in f.edges:
                if e not in self.edges:
                    for f2 in e.link_faces:
                        side = face_sides.get(f2)
                        if side is not None:
                            face_sides[f] = side
                            return
        
        add_to_wavefront(e)
        
        while wavefront:
            e = wavefront.pop()
            for f in e.link_faces:
                propagate_face_side(f)
            add_to_wavefront(e)
        
        return face_sides

    def gather_vertex_rails(self, v, face_sides):
        rails = {}
        
        if self.edges:
            for e in v.link_edges:
                if e.hide or (e not in self.edges):
                    continue
                for l in e.link_loops:
                    l = (l.link_loop_prev if l.vert == v else l.link_loop_next)
                    if (not l.edge.hide) and (l.edge not in self.edges):
                        rails[l.edge] = face_sides.get(l.face, 0)
        
        if not rails:
            for e in v.link_edges:
                if not e.hide:
                    rails[e] = 0
        
        return rails


def divide(a, b, fallback):
    try:
        return a / b
    except Exception:
        return fallback

def divide01(a, b):
    v = divide(a, b, 0.5)
    if not (v > 0.0):
        return 0.0
    if not (v < 1.0):
        return 1.0
    return v


NFlow.behaviors['nFlow: Slide Edges'] = dict(
    type=Slide_Verts,
    description='Slide a single edge or edge loop along the adjacent edges',
    cursor='COPY',
    elements={'EDGE', 'EDGE_LOOP'},
    options=[
        # dict(idname='slide_mode', name='Mode', default='PROPORTIONAL', items=[
        #     ('PROPORTIONAL', 'Proportional'),
        #     ('ABSOLUTE_NEAR', 'Absolute (near)'),
        #     ('ABSOLUTE_FAR', 'Absolute (far)'),
        # ]),
        dict(idname='use_auto_shrinkwrap', name='Allow Auto Shrinkwrap', default=True),
    ],
)
