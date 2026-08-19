import math

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..common import *

from .slide_verts import Slide_Verts, divide01


class Add_Edge_LoopCut(NFlowBehavior):
    undo_message = 'Loop Cut'

    capabilities = {'SHRINKWRAP'}

    show_preview = True
    quads_only = True

    use_auto_shrinkwrap = True

    slide_mode = 'PROPORTIONAL'
    abs_slide_pref = 'NEAR'

    def hover(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.find_candidates(mouse_pos)

    def invoke(self, context, event):
        self.editors.get(self.obj) # make sure an editor is initialized
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.update_current_state(mouse_pos, event, copy=True)
        self.status_text = f'E: proportional or absolute, F: near or far edge (if absolute)'
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        
        self.process_event(event)
        
        if (event.type == 'MOUSEMOVE') or (event.value == 'PRESS'):
            self.update_current_state(mouse_pos, event, copy=True)
        
        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            self.update_current_state(mouse_pos, event, copy=False)
            return 'FINISHED'
        
        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.restore_initial_state()
            return 'CANCELLED'

    # Use the same logic
    process_event = Slide_Verts.process_event

    def update_current_state(self, mouse_pos, event, copy):
        self.editors.revert_last()
        
        self.find_candidates(mouse_pos)
        
        editor = self.editor
        
        affected_geom = set()
        for edge, t in self.candidate_edges.items():
            affected_geom.add(edge)
            affected_geom.update(edge.verts)
            affected_geom.update(edge.link_faces)
        
        if copy:
            copy_geom, remap = editor.duplicate(affected_geom, replace={'EDGES', 'FACES'})
        else:
            remap = (lambda elem: elem)
        
        keys = {}
        splits = []
        for i, (edge, t) in enumerate(self.candidate_edges.items()):
            keys[edge] = i
            splits.append((remap(edge), t))
        
        faces = []
        for face, (midpoint, face_cuts) in self.candidate_faces.items():
            face_cuts = [(keys[edgeA], keys[edgeB]) for edgeA, edgeB in face_cuts]
            faces.append((remap(face), midpoint, face_cuts))
        
        split_verts = []
        edge_loop = []
        
        def split_edge(edge, t):
            v0, v1 = edge.verts
            new_edge, new_vert = bmesh.utils.edge_split(edge, v0, t)
            if edge.select:
                new_vert.select = True
            editor.add(new_edge)
            editor.add(new_vert)
            return new_vert
        
        def split_face(face, v0, v1, select):
            new_face, new_loop = bmesh.utils.face_split(face, v0, v1)
            if select:
                new_loop.edge.select = True
                new_face.select = True
            editor.add(new_loop.edge)
            editor.add(new_face)
            edge_loop.append(new_loop.edge)
            return new_face, new_loop.edge
        
        for i, (edge, t) in enumerate(splits):
            new_vert = split_edge(edge, t)
            splits[i] = new_vert
            split_verts.append(new_vert)
        
        def find_face_with_vert(faces, v):
            return next(iter(f for f in faces if v in f.verts), None)
        
        for face, midpoint, face_cuts in faces:
            select = face.select
            key0, key1 = face_cuts[0]
            new_face, new_edge = split_face(face, splits[key0], splits[key1], select)
            if midpoint is None:
                continue
            
            sliced_faces = [face, new_face]
            
            cut_pos, cut_t = midpoint
            mid_vert = split_edge(new_edge, cut_t)
            mid_vert.co = cut_pos
            
            for cut_i in range(1, len(face_cuts)):
                key0, key1 = face_cuts[cut_i]
                v0, v1 = splits[key0], splits[key1]
                
                f = find_face_with_vert(sliced_faces, v0)
                f0, e0 = split_face(f, v0, mid_vert, select)
                
                f = find_face_with_vert(sliced_faces, v1)
                f1, e1 = split_face(f, v1, mid_vert, select)
                
                sliced_faces.append(f0)
                sliced_faces.append(f1)
        
        NFlow.cleanup()
        
        if self.use_auto_shrinkwrap:
            self.raycaster.snap_verts_to_surface(editor.obj, split_verts)
        
        if not copy:
            self.editors.apply()
            
            if self.use_post_select_elements:
                MeshUtil.select_elements({self.bm: (edge_loop or split_verts)},
                    mode=self.post_select_mode, sanitize='INCLUDE')
            
            MeshUtil.merge_nearby_verts(self.bm, split_verts)
        
        self.editors.update_meshes()

    def restore_initial_state(self):
        self.editors.revert()
        
        NFlow.cleanup()
        NFlow.update_scene_ref()

    def find_candidates(self, mouse_pos):
        elem = self.elements[0]
        if isinstance(elem, BMFace):
            element_sets = [(self.obj, elem.edges)]
            pos3d, obj, elem = self.raycaster.nearest_along_ray(mouse_pos, element_sets,
                use_raycast=False, use_depth=False, clamp=True)
        
        self.edge_start = elem
        
        edge = self.edge_start
        matrix = self.obj.matrix_world
        origin, endpoint = self.raycaster.ray_line(mouse_pos)
        cut_point, t = Raycaster.edge(edge, matrix, origin, endpoint, clamp=True)
        t_inv = 1 - t
        
        v0, v1 = edge.verts
        
        queue = []
        for face in edge.link_faces:
            loop = self.find_loop(face, edge)
            queue.append((loop, (loop.vert != v0)))
        
        edges_info = {self.edge_start: (self.edge_start.calc_length(), False)}
        self.candidate_edges = {self.edge_start: t}
        self.candidate_faces = {}
        
        while queue:
            item = queue.pop(0)
            loop, inverse = item
            
            if self.quads_only and len(loop.face.verts) != 4:
                continue
            
            opposite = self.find_opposite(loop)
            
            if opposite is None:
                continue
            
            face_cut = frozenset((loop.edge, opposite.edge))
            
            face_info = self.candidate_faces.get(loop.face)
            if face_info is None:
                face_cuts = [] # we need to preserve insertion order for multi-cuts
                self.candidate_faces[loop.face] = (None, face_cuts)
            else:
                midpoint, face_cuts = face_info
            
            if face_cut in face_cuts:
                continue
            
            face_cuts.append(face_cut)
            
            if opposite.edge not in self.candidate_edges:
                edge_inverse = (self.is_inverse(opposite) == inverse)
                self.candidate_edges[opposite.edge] = (t_inv if edge_inverse else t)
                edges_info[opposite.edge] = (opposite.edge.calc_length(), edge_inverse)
            
            if len(face_cuts) >= 2:
                midpoint = self.calc_cut_midpoint(face_cuts)
                self.candidate_faces[loop.face] = (midpoint, face_cuts)
            
            for loop2 in opposite.edge.link_loops:
                if loop2 != opposite:
                    inverse2 = ((loop2.vert == opposite.vert) != inverse)
                    queue.append((loop2, inverse2))
        
        if self.slide_mode != 'PROPORTIONAL':
            min_len = min(length for length, inverse in edges_info.values())
            is_far = (self.slide_mode == 'ABSOLUTE_FAR')
            dist = min((t_inv if is_far else t) * self.edge_start.calc_length(), min_len)
            for edge, (length, inverse) in edges_info.items():
                abs_t = divide01(dist, length)
                self.candidate_edges[edge] = (1 - abs_t if inverse != is_far else abs_t)
        
        if not self.show_preview:
            return
        
        NFlow.update_scene_ref()
        
        radius = NFlowPrefs.get('vert_radius_base')
        NFlow.add_vert(cut_point, PresetOverride.get('color_vertex'), radius)
        
        color = PresetOverride.get('color_edge_loop')
        for midpoint, face_cuts in self.candidate_faces.values():
            if midpoint is None:
                for edgeA, edgeB in face_cuts:
                    p0 = matrix @ self.get_point(edgeA)
                    p1 = matrix @ self.get_point(edgeB)
                    NFlow.add_edge([p0, p1], color)
            else:
                cut_pos, cut_t = midpoint
                cut_pos = matrix @ cut_pos
                for edgeA, edgeB in face_cuts:
                    p0 = matrix @ self.get_point(edgeA)
                    p1 = matrix @ self.get_point(edgeB)
                    NFlow.add_edge([cut_pos, p0], color)
                    NFlow.add_edge([cut_pos, p1], color)

    def get_point(self, edge):
        v0, v1 = edge.verts
        t = self.candidate_edges[edge]
        return v0.co.lerp(v1.co, t)

    def calc_cut_midpoint(self, face_cuts):
        if len(face_cuts) < 2:
            return None
        
        lines = [(self.get_point(edgeA), self.get_point(edgeB)) for edgeA, edgeB in face_cuts]
        
        if len(lines) == 2:
            lineA, lineB = lines
            pA0, pA1 = lineA
            pB0, pB1 = lineB
            midpoint = intersect_line_line(pA0, pA1, pB0, pB1)
            if midpoint is not None:
                midA, midB = midpoint
                deltaA = pA1 - pA0
                magA = deltaA.length_squared
                if magA > 0:
                    t = (deltaA / magA).dot(midA - pA0)
                    if (t >= 0) and (t <= 1):
                        return midA, t
        
        p = Vector()
        for line in lines:
            p += (line[0] + line[1]) * 0.5
        p /= len(lines)
        return p, 0.5

    @classmethod
    def is_inverse(cls, loop):
        v0, v1 = loop.edge.verts
        return loop.vert != v0

    @classmethod
    def find_loop(cls, face, edge):
        for loop in face.loops:
            if loop.edge == edge:
                return loop

    @classmethod
    def find_opposite(cls, loop):
        count = len(loop.face.loops)
        if (count & 1) != 0:
            return None
        
        for i in range(count >> 1):
            loop = loop.link_loop_next
        return loop


NFlow.behaviors['nFlow: Loop Cut'] = dict(
    type=Add_Edge_LoopCut,
    description='Cut edge(s) by loop(s)',
    cursor='PAINT_BRUSH',
    elements={'EDGE', 'FACE'},
    options=[
        dict(idname='use_auto_shrinkwrap', name='Allow Auto Shrinkwrap', default=True),
        dict(idname='show_preview', name='Preview', default=True),
        dict(idname='quads_only', name='Quads Only', default=True),
    ],
)
