import math

import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import delaunay_2d_cdt

from ..common import *


class Add_Empty_SpeculativePolygon(NFlowBehavior):
    undo_message = 'Add Polygon'

    roll_mode = 'SUGGESTIONS'
    roll_on_hover = True
    show_tooltip = True
    enable_retopo_overlay = False

    candidate_index = 0
    last_editor = None

    @property
    def use_area_as_score(self):
        # return self.candidate_index != 0
        return True # it's probably better to always use stable sorting

    def init(self, context, event):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow
        self.poly_type = nflow_config_workspace.poly_type
        self.use_visibility = nflow_config_workspace.ignore_occluded_verts
        self.poly_search = nflow_config_workspace.poly_search

        if nflow_config_workspace.suggest_poly_roll:
            self.roll_mode = nflow_config_workspace.suggest_poly_roll_mode
        else:
            self.roll_mode = 'NONE'

    def hover(self, context, event):
        cls = Add_Empty_SpeculativePolygon

        consume_event = False

        if self.roll_on_hover:
            if event.type == 'MOUSEMOVE':
                cls.candidate_index = 0
            elif event.type == 'WHEELDOWNMOUSE':
                consume_event = self.roll(1, True)
            elif event.type == 'WHEELUPMOUSE':
                consume_event = self.roll(-1, True)
            elif (event.type == 'PAGE_DOWN') and (event.value == 'PRESS'):
                consume_event = self.roll(1, True)
            elif (event.type == 'PAGE_UP') and (event.value == 'PRESS'):
                consume_event = self.roll(-1, True)
        else:
            cls.candidate_index = 0

        self.candidate_index = cls.candidate_index

        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.find_candidate(mouse_pos)

        return consume_event

    def invoke(self, context, event):
        if self.enable_retopo_overlay:
            space_data = context.space_data
            if hasattr(space_data.overlay, 'show_retopology'):
                space_data.overlay.show_retopology = True

        region = context.region
        view_center = Vector((region.width*0.5, region.height*0.5))
        self.view_dir = Raycaster.ray(context, view_center)[1]
        self.bvh_trees = {}
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.try_add_face(mouse_pos)
        self.status_text = 'Page up / Page down: roll suggestions or algorithm'
        return 'RUNNING_MODAL'

    def modal(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        if event.type == 'MOUSEMOVE':
            self.readd_polygon(mouse_pos)
        elif event.type == 'WHEELDOWNMOUSE':
            self.readd_polygon(mouse_pos, 1)
        elif event.type == 'WHEELUPMOUSE':
            self.readd_polygon(mouse_pos, -1)
        elif (event.type == 'PAGE_DOWN') and (event.value == 'PRESS'):
            self.readd_polygon(mouse_pos, 1)
        elif (event.type == 'PAGE_UP') and (event.value == 'PRESS'):
            self.readd_polygon(mouse_pos, -1)

        if (event.type == self.invoke_event_type) and (event.value == 'RELEASE'):
            if self.use_post_select_elements:
                bm_elements = self.editors.get_elements('ADDED', sanitize='INCLUDE')
                MeshUtil.select_elements(bm_elements, mode=self.post_select_mode)
            return 'FINISHED'

        if (event.type in self.cancel_event_types) and (event.value == 'PRESS'):
            self.editors.revert()
            return 'CANCELLED'

    def cleanup(self, context):
        NFlow.cleanup()

    def roll(self, direction, globally=False):
        if self.roll_mode == 'SUGGESTIONS':
            if globally:
                cls = Add_Empty_SpeculativePolygon
                cls.candidate_index += direction
                self.candidate_index = cls.candidate_index
            else:
                self.candidate_index += direction
        elif self.roll_mode == 'ALGORITHM':
            context = bpy.context
            nflow_config_workspace = context.workspace.nsolve.ops.nflow
            if nflow_config_workspace.poly_search == 'WORLD':
                nflow_config_workspace.poly_search = 'SCREEN'
            elif nflow_config_workspace.poly_search == 'SCREEN':
                nflow_config_workspace.poly_search = 'STABLE'
            else:
                nflow_config_workspace.poly_search = 'WORLD'
            self.poly_search = nflow_config_workspace.poly_search

        return (self.roll_mode != 'NONE')

    def readd_polygon(self, mouse_pos, roll_direction=None):
        if roll_direction is None:
            self.candidate_index = 0
        else:
            NFlow.cleanup()

            self.roll(roll_direction)

            if self.last_editor:
                self.last_editor.pop_state()
                self.update_bvh_trees(self.last_editor.obj)

        if not self.is_over_mesh(mouse_pos):
            self.try_add_face(mouse_pos)

    def find_candidate(self, mouse_pos):
        self.candidate_info = None

        if self.poly_search == 'WORLD':
            search_result = self.find_candidates_3d(mouse_pos)
        elif self.poly_search == 'SCREEN':
            search_result = self.find_candidates_2d(mouse_pos)
        else:
            search_result = self.find_candidates_stable(mouse_pos)

        if not search_result:
            return

        candidate_polygons, count_estimate = search_result

        if not candidate_polygons:
            return

        candidate_index = self.candidate_index % len(candidate_polygons)

        if not self.show_tooltip:
            self.hover_text = ''
        elif self.roll_mode == 'SUGGESTIONS':
            if count_estimate > len(candidate_polygons):
                self.hover_text = f'Candidate {candidate_index+1}/{count_estimate}+'
            else:
                self.hover_text = f'Candidate {candidate_index+1}/{count_estimate}'
        elif self.roll_mode == 'ALGORITHM':
            if self.poly_search == 'WORLD':
                self.hover_text = 'World-space'
            elif self.poly_search == 'SCREEN':
                self.hover_text = 'Screen-space'
            elif self.poly_search == 'STABLE':
                self.hover_text = 'Stable tesselation'

        candidate_polygons.sort(key=(lambda item: item[0]))
        dist, obj, bm, hull = candidate_polygons[candidate_index]
        hull_verts, polygon3d, polygon2d = hull

        self.candidate_info = obj, bm, hull_verts

        NFlow.update_scene_ref()
        NFlow.add_face(polygon3d, PresetOverride.get('color_face'))

    def find_candidates_stable(self, mouse_pos):
        element_sets = []
        for obj, mesh, bm in EditableMeshes.all():
            elements = (v for v in bm.verts
                if (not v.hide) and (v.is_boundary or v.is_wire or (len(v.link_edges) == 0)))
            element_sets.append((obj, elements))

        nearest_point = self.raycaster.nearest_along_ray(mouse_pos, element_sets, use_raycast=True)[0]

        if nearest_point is None:
            return None

        candidate_triangles = []
        candidate_polygons = []

        for obj, mesh, bm in EditableMeshes.all():
            matrix = obj.matrix_world
            visible_verts, visible_edges = self.gather_candidates(bm, matrix)

            i2v = list(visible_verts.keys())
            v2i = {v: i for i, v in enumerate(i2v)}
            src_coords = [Vector(pos2d) for pos3d, pos2d in visible_verts.values()]
            src_edges = [(v2i[v0], v2i[v1]) for v0, v1 in visible_edges]
            src_faces = []
            output_type = 0 # triangles with convex hull
            epsilon = 1e-3
            result = delaunay_2d_cdt(src_coords, src_edges, src_faces, output_type, epsilon)
            dst_coords, dst_edges, dst_faces, orig_verts, orig_edges, orig_faces = result

            connectivity = {}
            triangles = []

            for i0, i1, i2 in dst_faces:
                verts0 = orig_verts[i0]
                verts1 = orig_verts[i1]
                verts2 = orig_verts[i2]

                if not (verts0 and verts1 and verts2):
                    continue

                i0 = verts0[0]
                i1 = verts1[0]
                i2 = verts2[0]

                connectivity[(i0, i1)] = i2
                connectivity[(i1, i2)] = i0
                connectivity[(i2, i0)] = i1

                p0 = src_coords[i0]
                p1 = src_coords[i1]
                p2 = src_coords[i2]
                polygon2d = (p0, p1, p2)

                if winding_number(mouse_pos, polygon2d) == 0:
                    continue

                triangles.append((i0, i1, i2))

                v0 = i2v[i0]
                v1 = i2v[i1]
                v2 = i2v[i2]
                hull_v = (v0, v1, v2)

                polygon3d = [visible_verts[v][0] for v in hull_v]

                score = math.inf # there is always only 1 triangle candidate

                hull_info = (hull_v, polygon3d, polygon2d)
                candidate_triangles.append((score, obj, bm, hull_info))

            if self.poly_type == 'TRIS':
                continue

            edges_set = set(src_edges)

            for indices in triangles:
                for offset in (0, 1, 2):
                    i0 = indices[offset-2]
                    i1 = indices[offset-1]
                    i2 = indices[offset-0]
                    i3 = connectivity.get((i1, i0))
                    if i3 is None:
                        continue

                    if ((i0, i1) in edges_set) or ((i1, i0) in edges_set):
                        continue

                    v0 = i2v[i0]
                    v1 = i2v[i1]
                    v2 = i2v[i2]
                    v3 = i2v[i3]
                    hull_v = (v0, v3, v1, v2)

                    polygon3d = [visible_verts[v][0] for v in hull_v]
                    polygon2d = [visible_verts[v][1] for v in hull_v]

                    score = point_line_distance(mouse_pos, src_coords[i0], src_coords[i1])

                    hull_info = (hull_v, polygon3d, polygon2d)
                    candidate_polygons.append((score, obj, bm, hull_info))

        if self.poly_type != 'QUADS':
            candidate_polygons.extend(candidate_triangles)

        candidate_count_estimate = len(candidate_polygons)

        return candidate_polygons, candidate_count_estimate

    def find_candidates_2d(self, mouse_pos):
        element_sets = []
        for obj, mesh, bm in EditableMeshes.all():
            elements = (v for v in bm.verts
                if (not v.hide) and (v.is_boundary or v.is_wire or (len(v.link_edges) == 0)))
            element_sets.append((obj, elements))

        nearest_point = self.raycaster.nearest_along_ray(mouse_pos, element_sets, use_raycast=True)[0]

        if nearest_point is None:
            return None

        candidate_triangles = []
        candidate_polygons = []

        for obj, mesh, bm in EditableMeshes.all():
            matrix = obj.matrix_world
            visible_verts, visible_edges = self.gather_candidates(bm, matrix, nearest_point)

            if len(visible_verts) <= 2:
                continue

            edge_cast = self.make_edge_caster(visible_verts, visible_edges)

            best_dist, best_edge = self.find_closest_edge(visible_verts, visible_edges, edge_cast, mouse_pos)

            if not best_edge:
                continue

            hulls = self.find_best_hull(best_edge, visible_verts, edge_cast, mouse_pos)

            for score, hull_v, polygon3d, polygon2d in hulls:
                hull_info = (hull_v, polygon3d, polygon2d)

                if self.use_area_as_score:
                    if len(polygon3d) <= 3:
                        score *= 2
                    score = (score, polygon_3d_area(hull_info[1]))
                else:
                    score = (score, best_dist)

                if len(polygon3d) > 3:
                    candidate_polygons.append((score, obj, bm, hull_info))
                else:
                    candidate_triangles.append((score, obj, bm, hull_info))

        if self.poly_type != 'QUADS':
            candidate_polygons.extend(candidate_triangles)

        candidate_count_estimate = len(candidate_polygons)

        return candidate_polygons, candidate_count_estimate

    def find_candidates_3d(self, mouse_pos):
        element_sets = []
        for obj, mesh, bm in EditableMeshes.all():
            elements = [v for v in bm.verts
                if (not v.hide) and (v.is_boundary or v.is_wire or (len(v.link_edges) == 0))]
            if elements:
                element_sets.append((obj, elements))
            elements = [e for e in bm.edges if (not e.hide) and (e.is_boundary or e.is_wire)]
            if elements:
                element_sets.append((obj, elements))

        nearest_point, obj, elem = self.raycaster.nearest_along_ray(mouse_pos, element_sets,
            use_raycast=True, use_depth=True)

        if nearest_point is None:
            return None

        if elem is None:
            pos3d, obj, elem = self.raycaster.nearest_to_point(nearest_point, element_sets)
            if elem is None:
                return None

        bm = EditableMeshes.get_bm(obj)

        if isinstance(elem, BMVert):
            verts = next(iter(elements for obj2, elements in element_sets
                if (obj2 == obj) and (isinstance(elements[0], BMVert))))
        elif isinstance(elem, BMEdge):
            edges = next(iter(elements for obj2, elements in element_sets
                if (obj2 == obj) and (isinstance(elements[0], BMEdge))))
            verts = list(set(v for e in edges for v in e.verts))
            verts.extend(v for v in bm.verts if (not v.hide) and (len(v.link_edges) == 0))

        matrix = obj.matrix_world
        coords = [matrix @ v.co for v in verts]

        def swap(a, i0, i1):
            a[i0], a[i1] = a[i1], a[i0]

        n = len(verts)

        if isinstance(elem, BMVert):
            i = verts.index(elem)
            swap(verts, 0, i)
            swap(coords, 0, i)
            def tri_generator():
                for i1 in range(1, n):
                    for i2 in range(i1+1, n):
                        yield 0, i1, i2
        elif isinstance(elem, BMEdge):
            for v, i_dst in zip(elem.verts, (0, 1)):
                i = verts.index(v)
                swap(verts, i_dst, i)
                swap(coords, i_dst, i)
            def tri_generator():
                for i2 in range(2, n):
                    yield 0, 1, i2

        def calc_tri_size(p0, p1, p2):
            delta10 = p1 - p0
            delta21 = p2 - p1
            delta02 = p0 - p2

            info = delta10.length_squared, delta10, p1, p2

            mag2 = delta21.length_squared
            if mag2 < info[0]:
                info = mag2, delta21, p2, p0

            mag2 = delta02.length_squared
            if mag2 < info[0]:
                info = mag2, delta02, p0, p1

            normal = delta10.cross(delta02)

            dir_u = info[1].normalized()
            dir_v = normal.cross(dir_u).normalized()
            p = info[3] - info[2]
            p_u = dir_u.dot(p)
            p_v = dir_v.dot(p)

            return normal, max(abs(p_u), abs(p_v))

        origin, direction = self.raycaster.ray(mouse_pos)

        size_factor = 0.01

        candidates = []
        for i0, i1, i2 in tri_generator():
            p0, p1, p2 = coords[i0], coords[i1], coords[i2]
            p = intersect_ray_tri(p0, p1, p2, direction, origin)
            if p is not None:
                dist = direction.dot(p - origin)
                normal, size = calc_tri_size(p0, p1, p2)
                score = dist + size * size_factor
                if direction.dot(normal) > 0:
                    i1, i2 = i2, i1
                candidates.append((score, i0, i1, i2))

        if not candidates:
            return None

        unique_hulls = set()

        candidates.sort(key=(lambda item: item[0]))

        candidate_count_estimate = 0

        candidate_triangles = []
        candidate_polygons = []

        remaining_candidates = len(candidates)
        for candidate in candidates:
            score, i0, i1, i2 = candidate

            def calc_score(points):
                n = len(points)
                angles = [(points[i] - points[i-1]).angle(points[i-2] - points[i-1]) for i in range(n)]
                score = max(angles) - min(angles)
                if self.poly_type == 'QUADS':
                    return (-n, score)
                elif self.poly_type == 'TRIS':
                    return (n, score)
                else:
                    return score

            def add_hull(*indices):
                # Avoid any rotated equivalents
                i_min = min(indices)
                i_min_i = indices.index(i_min)
                indices = indices[i_min_i:] + indices[:i_min_i]

                hull_verts = tuple(verts[i] for i in indices)
                if hull_verts in unique_hulls:
                    return None, None

                polygon3d = [coords[i] for i in indices]
                polygon2d = None
                hull_info = (hull_verts, polygon3d, polygon2d)

                if self.use_area_as_score:
                    score = polygon_3d_area(polygon3d)
                    if len(polygon3d) <= 3:
                        score *= 2
                else:
                    score = calc_score(polygon3d)

                if len(polygon3d) > 3:
                    candidate_polygons.append((score, obj, bm, hull_info))
                else:
                    candidate_triangles.append((score, obj, bm, hull_info))

                unique_hulls.add(hull_verts)

                return hull_verts, polygon3d

            hull_verts, polygon3d = add_hull(i0, i1, i2)

            if hull_verts is None:
                continue

            if self.poly_type != 'TRIS':
                best_info = math.inf, None
                for i in range(3):
                    dist = point_line_distance(nearest_point, polygon3d[i-1], polygon3d[i-2])
                    if dist < best_info[0]:
                        best_info = dist, i

                i = best_info[1]
                hull_verts = hull_verts[i], hull_verts[i-1], hull_verts[i-2]
                polygon3d = polygon3d[i], polygon3d[i-1], polygon3d[i-2]

                i012 = (i0, i1, i2)
                p0, p1, p2 = polygon3d
                normal = (p1 - p0).cross(p2 - p0)
                edge_delta = p1 - p2
                p_mid = (p1 + p2) * 0.5
                p_dir = normal.cross(edge_delta)
                if p_dir.dot(p_mid - p0) < 0:
                    p_dir = -p_dir

                dir_u = direction.cross(edge_delta).normalized()
                dir_v = direction.cross(dir_u).normalized()

                def find_nearest_quadpoint(p_mid, p_dir, p_dst):
                    best_info = math.inf, None
                    for i3 in range(n):
                        if i3 in i012:
                            continue
                        p = coords[i3]
                        if p_dir.dot(p - p_mid) > 0:
                            dist = (p - p_dst).length_squared
                            if dist < best_info[0]:
                                best_info = dist, i3
                    return best_info

                def hull_indices(*indices):
                    hull = ConvexHull2D()
                    for i in indices:
                        p = coords[i]
                        hull.add((dir_u.dot(p), dir_v.dot(p)))
                    return [indices[i] for i in hull.indices()]

                p_dst = (p1 + p2) - p0
                i3 = find_nearest_quadpoint(p_mid, p_dir, p_dst)[1]
                if i3 is not None:
                    add_hull(*hull_indices(i0, i1, i3, i2))

                p_dst = (p0 - p_mid).reflect(edge_delta) + p_mid
                i3 = find_nearest_quadpoint(p_mid, -p_dir, p_dst)[1]
                if i3 is not None:
                    add_hull(*hull_indices(i0, i1, i3, i2))

            candidate_count_estimate = len(candidate_polygons)
            remaining_candidates -= 1

            if (self.candidate_index == 0) and (candidate_count_estimate > 1):
                candidate_count_estimate += remaining_candidates
                break

        if self.poly_type != 'QUADS':
            candidate_polygons.extend(candidate_triangles)
            candidate_count_estimate += len(candidate_triangles)

        return candidate_polygons, candidate_count_estimate

    def is_over_mesh(self, mouse_pos):
        origin, direction = self.raycaster.ray(mouse_pos)

        # Can't use selection cast here (Blender will crash)
        for obj, mesh, bm in EditableMeshes.all():
            matrix = obj.matrix_world
            matrix_inv = matrix.inverted_safe()
            matrix_3x3 = matrix_inv.to_3x3()
            bvh_tree = self.bvh_trees[obj]
            result = bvh_tree.ray_cast(matrix_inv @ origin, matrix_3x3 @ direction)
            if result[0] is not None:
                return True
        return False

    def try_add_face(self, mouse_pos):
        self.find_candidate(mouse_pos)

        modified_obj = None

        if self.candidate_info:
            obj, bm, verts = self.candidate_info

            editor = self.editors.get(obj)
            self.last_editor = editor

            editor.push_state()

            f = editor.add_face(verts)

            view_dir_local = editor.local_matrix_v @ self.view_dir
            if MeshUtil.is_face_misaligned(f, fallback=-view_dir_local):
                editor.flip(f)

            editor.update_mesh()

            modified_obj = obj

        self.update_bvh_trees(modified_obj)

    def update_bvh_trees(self, modified_obj=None):
        for obj, mesh, bm in EditableMeshes.all():
            if (obj not in self.bvh_trees) or (obj == modified_obj):
                self.bvh_trees[obj] = BVHTree.FromBMesh(bm)

    def gather_candidates(self, bm, matrix, nearest_point=None):
        visible_verts_ordered = []
        visible_verts = {}
        visible_edges = set()

        # Gather the visible non-inner verts and their edges
        with self.raycaster.batch():
            for v in bm.verts:
                if v.hide or not (v.is_boundary or v.is_wire or (len(v.link_edges) == 0)):
                    continue

                pos3d = matrix @ v.co
                pos2d = self.raycaster.project(pos3d)

                if not pos2d:
                    if self.use_visibility: continue
                    else:
                        pos2d = self.raycaster.project_occluded(bpy.context, pos3d)
                # if self.use_visibility and not self.raycaster.is_visible(pos3d, pos2d):
                #     continue

                visible_verts[v] = (pos3d, pos2d)
                visible_edges.update(tuple(e.verts) for e in v.link_edges
                    if (not e.hide) and (e.is_boundary or e.is_wire))

                if nearest_point is not None:
                    distance = (pos3d - nearest_point).magnitude
                    visible_verts_ordered.append((distance, v))

        if nearest_point is not None:
            # Sort verts by distances to the point under the mouse
            visible_verts_ordered.sort(key=(lambda item: item[0]))

            # Add the nearest pair of vertices as another edge candidate
            if len(visible_verts_ordered) >= 2:
                visible_edges.add(tuple(v for distance, v in visible_verts_ordered[:2]))

        # Include edge vertices, even if they are occluded
        for edge_verts in visible_edges:
            edge_prj = self.raycaster.project_edge(matrix, *edge_verts)
            if edge_prj is not None:
                for v, (pos3d, pos2d) in zip(edge_verts, edge_prj):
                    visible_verts[v] = (pos3d, pos2d)

        return visible_verts, visible_edges

    def find_closest_edge(self, visible_verts, visible_edges, edge_cast, mouse_pos):
        # Find the edge candidate closest to the mouse
        best_dist = math.inf
        best_edge = None

        for edge_verts in visible_edges:
            v0, v1 = edge_verts
            p0_3d, p0_2d = visible_verts.get(v0)
            p1_3d, p1_2d = visible_verts.get(v1)
            # TODO: intersect with the view's near plane?
            if (p0_2d is not None) and (p1_2d is not None):
                if not edge_cast(p0_2d, p1_2d):
                    distance2d = point_line_distance(mouse_pos, p0_2d, p1_2d)
                    if distance2d < best_dist:
                        best_dist = distance2d
                        best_edge = (v0, v1)

        return best_dist, best_edge

    def make_edge_caster(self, visible_verts, visible_edges):
        vertices = []
        vertex_indices = {}
        for v, (p3d, p2d) in visible_verts.items():
            vertex_indices[v] = len(vertices)
            vertices.append((p2d[0], p2d[1], -1))
            vertices.append((p2d[0], p2d[1], +1))

        polygons = []
        for v0, v1 in visible_edges:
            i0n = vertex_indices[v0]
            i0p = i0n + 1
            i1n = vertex_indices[v1]
            i1p = i1n + 1
            polygons.append((i0n, i1n, i0p))
            polygons.append((i0p, i1n, i1p))

        edge_bvh = BVHTree.FromPolygons(vertices, polygons, all_triangles=True, epsilon=0.0)

        epsilon = 0.001
        distance_scale = 1 - epsilon * 2
        def edge_cast(src, dst):
            direction = dst - src
            distance = direction.magnitude * distance_scale
            origin = src + direction * epsilon
            origin = (origin[0], origin[1], 0)
            direction = (direction[0], direction[1], 0)
            result = edge_bvh.ray_cast(origin, direction, distance)
            return result[0] is not None

        return edge_cast

    def find_best_hull(self, best_edge, visible_verts, edge_cast, mouse_pos):
        v0, v1 = best_edge
        p0_3d, p0_2d = visible_verts[v0]
        p1_3d, p1_2d = visible_verts[v1]

        midpoint = (p1_3d + p0_3d) * 0.5
        edge_axis_x = (p1_3d - p0_3d).normalized()
        bbox_start_xmax = (p1_3d - p0_3d).magnitude

        edge_ort_2d = (p1_2d - p0_2d).orthogonal()
        edge_ort_2d *= math.copysign(1, edge_ort_2d.dot(mouse_pos - p0_2d))

        candidates = [(v, p3d, p2d) for v, (p3d, p2d) in visible_verts.items()
            if (v not in best_edge) and (edge_ort_2d.dot(p2d - p0_2d) > 0)]

        edge_2d = (p0_2d, p1_2d)
        def is_colliding(hull_v):
            for v in hull_v:
                if v not in best_edge:
                    src = visible_verts[v][-1]
                    for dst in edge_2d:
                        if edge_cast(src, dst):
                            return True
            return False

        hulls = []
        unique_hulls = set()

        def add_hull(hull, verts):
            count = hull.count()
            if count < len(verts):
                return

            hull_v = tuple(verts[i] for i in hull.indices())
            if hull_v in unique_hulls:
                return

            polygon2d = [visible_verts[v][-1] for v in hull_v]
            if winding_number(mouse_pos, polygon2d) == 0:
                return

            if is_colliding(hull_v):
                return

            polygon3d = [visible_verts[v][0] for v in hull_v]

            other_verts = [visible_verts[v][0] for v in hull_v if v not in best_edge]
            midpoint2 = sum(other_verts, Vector()) / len(other_verts)
            midpoint_dir = (midpoint2 - midpoint).normalized()
            edge_axis_z = edge_axis_x.cross(midpoint_dir).normalized()
            edge_axis_y = edge_axis_x.cross(edge_axis_z)
            midpoint_dot = midpoint_dir.dot(edge_axis_y)

            bbox_min = Vector()
            bbox_max = Vector((bbox_start_xmax, 0, 0))
            for p in other_verts:
                p = p - p0_3d
                px = edge_axis_x.dot(p)
                py = edge_axis_y.dot(p)
                pz = edge_axis_z.dot(p)
                bbox_min.x = min(bbox_min.x, px)
                bbox_min.y = min(bbox_min.y, py)
                bbox_min.z = min(bbox_min.z, pz)
                bbox_max.x = max(bbox_max.x, px)
                bbox_max.y = max(bbox_max.y, py)
                bbox_max.z = max(bbox_max.z, pz)
            bbox = bbox_max - bbox_min

            size_factor = sum((polygon3d[i] - polygon3d[j]).magnitude
                for i in range(count-1) for j in range(i+1, count))

            score = bbox.x + bbox.y + bbox.z
            score += size_factor / count
            score /= count

            if self.poly_type == 'QUADS':
                score = (-count, score)
            elif self.poly_type == 'TRIS':
                score = (count, score)

            hulls.append((score, hull_v, polygon3d, polygon2d))
            unique_hulls.add(hull_v)

        hull_edge = ConvexHull2D()
        hull_edge.add(p0_2d)
        hull_edge.add(p1_2d)
        for i in range(len(candidates)-1, -1, -1):
            vi, vi3d, vi2d = candidates[i]
            hull_tri = ConvexHull2D(source=hull_edge)
            hull_tri.add(vi2d)
            add_hull(hull_tri, [v0, v1, vi])
            hull_verts = [v0, v1, vi, None]
            for j in range(i-1, -1, -1):
                vj, vj3d, vj2d = candidates[j]
                hull_quad = ConvexHull2D(source=hull_tri)
                hull_quad.add(vj2d)
                hull_verts[-1] = vj
                add_hull(hull_quad, hull_verts)

        hulls.sort(key=(lambda item: item[0]))

        return hulls


def settings_draw(option_infos):
    def draw(layout, context):
        nflow_config_workspace = context.workspace.nsolve.ops.nflow

        row = layout.row(align=True)
        draw_enum_items(row, nflow_config_workspace, 'poly_type')

        layout.prop(nflow_config_workspace, 'ignore_occluded_verts')

        row = layout.row(align=True)
        row.label(text='Poly prediction:')
        row.prop(nflow_config_workspace, 'poly_search', text='')

        row = layout.row(align=True)
        row.prop(nflow_config_workspace, 'suggest_poly_roll', text='Rolling:')
        row.prop(nflow_config_workspace, 'suggest_poly_roll_mode', text='')

    return draw


NFlow.behaviors['nFlow: Suggest Polygon'] = dict(
    type=Add_Empty_SpeculativePolygon,
    description='Suggest a new polygon to be added between standalone/boundary vertices and edges',
    cursor='PAINT_BRUSH',
    elements={'NONE'},
    options=[
        # dict(idname='roll_mode', name='Scroll mode', default='SUGGESTIONS', items=[
        #     ('NONE', 'None'),
        #     ('SUGGESTIONS', 'Polygons'),
        #     ('ALGORITHM', 'Algorithm'),
        # ]),
        dict(idname='roll_on_hover', name='Scroll on hover', default=True),
        dict(idname='show_tooltip', name='Show tooltip', default=True),
        dict(idname='enable_retopo_overlay', name='Enable Retopology overlay', default=False),
    ],
    settings_label='Suggest Polygon',
    settings_draw=settings_draw,
    settings_draw_fold=True,
    settings_order=-1,
)
