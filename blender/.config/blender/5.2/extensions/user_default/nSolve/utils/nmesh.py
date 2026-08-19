import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import view3d

class Nmesh:
    """Class to handle the mesh data for the mesh element detection."""

    def __init__(self):
        self.bm = None
        self.obj = None
        self.bbox = None
        self.matrix = None
        self.bvh = None
        self.context = None
        self.region = None
        self.rv3d = None
        self.element = None
        self.array = None

    def __del__(self):
        self.finish()

    @classmethod
    def from_bmesh(cls, context, bm, obj):
        """Create a new instance of the class with the given context, event, and bmesh."""
        instance = cls()
        bm.faces.ensure_lookup_table()
        instance.context = context
        instance.bm = bm
        instance.obj = obj
        instance.bbox = bbox(obj)
        instance.matrix = obj.matrix_world
        instance.region = context.region
        instance.rv3d = context.region_data
        instance.bvh = BVHTree.FromBMesh(bm)
        return instance

    def finish(self):
        """Clean up the class."""
        self.context = None
        self.bm = None
        self.obj = None
        self.bbox = None
        self.matrix = None
        self.region = None
        self.rv3d = None
        self.element = None
        self.bvh = None
        self.array = None

    def detect_element(self, event, mode=(True, True, True)):
        """Detect the element under the mouse cursor based on the mode."""
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        _direction, _origin, local_origin, local_direction = self._get_ray(mouse_pos)
        hit_loc, index = self._ray_cast(local_origin, local_direction)

        if index is not None:
            face = self.bm.faces[index]
            closest_vert, closest_vert_2d = None, None
            closest_edge, closest_point_edge = None, None

            if mode[0]:
                closest_vert, closest_vert_2d = self._detect_closest_vertex(mouse_pos, face)
            if mode[1]:
                closest_edge, closest_point_edge = self._detect_closest_edge(mouse_pos, face)

            self._determine_element(mouse_pos, mode, face, hit_loc, closest_vert, closest_vert_2d, closest_edge, closest_point_edge)
        else:
            self._fallback_no_ray_hit(mouse_pos, mode)

    def _get_ray(self, mouse_pos):
        """Compute the ray direction and origin."""
        direction = view3d.region_2d_to_vector_3d(self.region, self.rv3d, mouse_pos)
        origin = view3d.region_2d_to_origin_3d(self.region, self.rv3d, mouse_pos)
        local_origin = self.matrix.inverted_safe() @ origin
        local_direction = self.matrix.inverted_safe().to_3x3() @ direction
        return direction, origin, local_origin, local_direction

    def _ray_cast(self, local_origin, local_direction):
        """Perform a ray cast and return the hit location and face index, skipping hidden faces."""
        max_iterations = 10  # Define a limit to avoid infinite loops in complex scenarios
        iterations = 0

        while iterations < max_iterations:
            hit_loc, _normal, index, _dist = self.bvh.ray_cast(local_origin, local_direction)

            if index is None:
                break

            face = self.bm.faces[index]

            if not face.hide:  # If the hit face is visible, return the result
                return hit_loc, index

            # If the face is hidden, continue raycasting from slightly beyond the hit point
            local_origin = hit_loc + local_direction * 0.001  # Offset slightly to avoid hitting the same face again
            iterations += 1

        # Return None if no visible face is hit
        return None, None

    def _detect_closest_vertex(self, mouse_pos, face):
        """Detect the closest vertex on the given face."""
        verts = [v for v in face.verts]
        verts_2d = self._verts_to_2darray(verts)
        return self._get_closest_vert(mouse_pos, verts, verts_2d)

    def _detect_closest_edge(self, mouse_pos, face):
        """Detect the closest edge on the given face."""
        edges = [e for e in face.edges]
        return self._get_closest_edge(mouse_pos, edges)

    def _determine_element(self, mouse_pos, mode, face, hit_loc, closest_vert, closest_vert_2d, closest_edge, closest_point_edge):
        """Determine the element based on the mode and detected components."""
        if mode == (True, False, False):
            self.element = ('VERT', closest_vert, None)
        elif mode == (False, True, False):
            self.element = ('EDGE', closest_edge, self.matrix.inverted() @ closest_point_edge)
        elif mode == (False, False, True):
            self.element = ('FACE', face, hit_loc)
        elif mode == (True, True, False):
            self.element = self._choose_vertex_or_edge(mouse_pos, closest_vert, closest_vert_2d, closest_edge, closest_point_edge)
        elif mode == (True, False, True):
            self.element = self._choose_vertex_or_face(mouse_pos, closest_vert, closest_vert_2d, face, hit_loc)
        elif mode == (False, True, True):
            self.element = self._choose_edge_or_face(mouse_pos, closest_edge, closest_point_edge, face, hit_loc)
        elif mode == (True, True, True):
            self.element = self._choose_vert_edge_or_face(mouse_pos, closest_vert, closest_vert_2d, closest_edge, closest_point_edge, face, hit_loc)
        else:
            self.element = [None, None, None]

    def _choose_vertex_or_edge(self, mouse_pos, closest_vert, closest_vert_2d, closest_edge, closest_point_edge):
        """Choose between vertex and edge based on proximity."""
        if closest_vert and self._is_within_radius(mouse_pos, closest_vert_2d):
            return ('VERT', closest_vert, None)
        return ('EDGE', closest_edge, self.matrix.inverted() @ closest_point_edge)

    def _choose_vertex_or_face(self, mouse_pos, closest_vert, closest_vert_2d, face, hit_loc):
        """Choose between vertex and face based on proximity."""
        if closest_vert and self._is_within_radius(mouse_pos, closest_vert_2d):
            return ('VERT', closest_vert, None)
        return ('FACE', face, hit_loc)

    def _choose_edge_or_face(self, mouse_pos, closest_edge, closest_point_edge, face, hit_loc):
        """Choose between edge and face based on proximity."""
        point_2d = view3d.location_3d_to_region_2d(self.region, self.rv3d, closest_point_edge, default=None)
        if closest_edge and point_2d and self._is_within_radius(mouse_pos, point_2d):
            return ('EDGE', closest_edge, self.matrix.inverted() @ closest_point_edge)
        return ('FACE', face, hit_loc)

    def _choose_vert_edge_or_face(self, mouse_pos, closest_vert, closest_vert_2d, closest_edge, closest_point_edge, face, hit_loc):
        """Choose between vertex, edge, and face based on proximity."""
        if closest_vert and self._is_within_radius(mouse_pos, closest_vert_2d):
            return ('VERT', closest_vert, None)
        point_2d = view3d.location_3d_to_region_2d(self.region, self.rv3d, closest_point_edge, default=None)
        if closest_edge and point_2d and self._is_within_radius(mouse_pos, point_2d):
            return ('EDGE', closest_edge, self.matrix.inverted() @ closest_point_edge)
        return ('FACE', face, hit_loc)

    def _get_closest_vert(self, mouse_pos, verts, verts_2d):
        """Get the closest vertex to the mouse cursor."""
        view_verts_pos, view_verts_index = verts_2d
        co = np.array(mouse_pos, dtype=np.float32)
        distances = np.linalg.norm(view_verts_pos - co, axis=1)
        closest_index = np.argmin(distances)
        closest_vert = verts[view_verts_index[closest_index]]
        closest_vert_2d = view_verts_pos[closest_index]
        return closest_vert, closest_vert_2d

    def _get_closest_edge(self, mouse_pos, edges):
        """Get the closest edge to the mouse cursor."""
        closest_edge = None
        closest_point = None
        min_dist = float('inf')
        co = np.array(mouse_pos, dtype=np.float32)

        for edge in edges:
            p1 = self.matrix @ edge.verts[0].co
            p2 = self.matrix @ edge.verts[1].co
            edge_point_3d = self._closest_point_on_edge_3d(p1, p2, mouse_pos)

            if not edge_point_3d:
                continue

            edge_point_2d = view3d.location_3d_to_region_2d(self.region, self.rv3d, edge_point_3d, default=None)

            if edge_point_2d is None:
                continue

            dist = np.linalg.norm(np.array(edge_point_2d) - co)

            if dist < min_dist:
                min_dist = dist
                closest_edge = edge
                closest_point = edge_point_3d

        return closest_edge, closest_point

    def _closest_point_on_edge_3d(self, p1, p2, mouse_pos):
        """Get the closest 3D point on the edge to the given 2D point."""
        p1_2d, p1_front = view3d.location_3d_to_region_2d_unclipped(self.region, self.rv3d, p1)
        p2_2d, p2_front = view3d.location_3d_to_region_2d_unclipped(self.region, self.rv3d, p2)

        # only ignore edge if both points are behind.
        if not p1_front and not p2_front:
            return None

        p1_2d = np.array(p1_2d)
        p2_2d = np.array(p2_2d)
        edge_vec_2d = p2_2d - p1_2d
        point_vec_2d = np.array(mouse_pos) - p1_2d
        edge_len_2d = np.linalg.norm(edge_vec_2d)
        edge_unit_2d = edge_vec_2d / edge_len_2d
        projection = np.dot(point_vec_2d, edge_unit_2d)
        projection = np.clip(projection, 0, edge_len_2d)
        closest_point_2d = p1_2d + projection * edge_unit_2d
        closest_point_ratio = np.linalg.norm(closest_point_2d - p1_2d) / edge_len_2d
        closest_point_3d = p1.lerp(p2, closest_point_ratio)
        return closest_point_3d

    def _is_within_radius(self, mouse_pos, point_2d, radius=20):
        """Check if the point is within the radius of the mouse cursor."""
        return np.linalg.norm(np.array(mouse_pos) - np.array(point_2d)) <= self.display_dot(radius)

    def _fallback_no_ray_hit(self, mouse_pos, mode):
        """Fallback detection to always detect the closest vertex if mode allows it."""
        if mode[0]:  # Only proceed if vertex detection is enabled
            verts = self.bm.verts
            if not self.array:
                self.array = self._verts_to_2darray(verts)
            verts_2d = self.array
            self.element = self._detect_closest_vert(mouse_pos, verts, verts_2d)
        else:
            self.element = [None, None, None]

    def _detect_closest_vert(self, mouse_pos, verts, verts_2d):
        """Detect the closest vertex to the mouse cursor."""
        view_verts_pos, view_verts_index = verts_2d
        co = np.array(mouse_pos, dtype=np.float32)
        ri = self._inside_circle(co, view_verts_pos, self.display_dot(20))
        detected_verts = [(verts[view_verts_index[i]], view_verts_pos[i]) for i in ri]
        detected_verts = [v for v in detected_verts if not v[0].hide]

        if detected_verts:
            detected_verts.sort(key=lambda v: np.linalg.norm(v[1] - co))
            closest_vert = detected_verts[0][0]
            return ('VERT', closest_vert, None)
        return (None, None)

    @staticmethod
    def _inside_circle(point, points, radius):
        """Return the indices of the points inside the circle."""
        rt = np.sum((points - point) ** 2, axis=-1)
        rr = np.float32(radius * radius)
        return np.where(rt <= rr)[0]

    @staticmethod
    def display_dot(val):
        """Convert the value to the display dot."""
        prefs = bpy.context.preferences.system
        return prefs.dpi / 25.4 * prefs.pixel_size * val

    def _verts_to_2darray(self, verts):
        """Convert the vertices to the region coordinates."""
        rv3d = self.context.region_data
        region = self.context.region
        width, height = region.width, region.height

        verts_pos = np.array([self.matrix @ v.co for v in verts], dtype=np.float32)
        coords = np.c_[verts_pos, np.ones(len(verts), dtype=np.float32)]
        coords = coords @ rv3d.perspective_matrix.transposed()
        coords = coords[:, :-1] / coords[:, 3:4]
        coords = coords * np.array((width / 2, height / 2, 1), dtype=np.float32) + np.array((width / 2, height / 2, 0), dtype=np.float32)

        return coords[:, :2], np.arange(len(coords), dtype='i')


def bbox(obj):
    """Calculate the bounding box center of an object."""
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    bbox_center = sum(bbox_corners, Vector()) / 8
    return bbox_center
