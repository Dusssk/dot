import bpy
import bmesh
import numpy as np
from mathutils import Vector
from ....utils import addon, view3d, scene
from ...draw.polyline import DrawPolyline
from ...draw.circle import DrawCircle
from ...draw.face import DrawFace
from ..utils import infobar


class NSOLVE_OT_Pencil(bpy.types.Operator):
    bl_idname = "nsolve.pencil"
    bl_label = "Draw Vertex"
    bl_description = "Draw a new vertex"
    bl_options = {'REGISTER', 'UNDO', 'UNDO_GROUPED', 'BLOCKING', 'GRAB_CURSOR'}

    point: Vector = Vector((0, 0, 0))
    snap_edge_radius: float = 800
    snap_vert_radius: float = 80

    mode: bpy.props.EnumProperty(name="Mode", items=[('EDGE', "Edge", "Edge"), ('QUAD', "Quad", "Quad")], default='EDGE')

    edge_index: int = -1
    vert_index: int = -1

    boundary_edges: list
    boundary_verts: set

    _handle_point: int
    _callback_point: DrawCircle
    _handles_verts: int
    _callback_verts: DrawCircle
    _handle_polylines: int
    _callback_polylines: DrawPolyline
    _handle_face: int
    _callback_face: DrawFace
    _callback_radius: int
    _handle_radius: int

    bm: bmesh.types.BMesh = None
    last_mouse_position: np.ndarray = None

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def invoke(self, context, event):
        self.get_defaults()
        self.bm = bmesh.from_edit_mesh(context.edit_object.data)
        self.cache_mesh_elements()
        self.run(context, event)
        self.setup_drawing(context)
        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set('nDraw Pencil')
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def get_defaults(self):
        '''Get the default values for the pencil tool'''
        self.snap_edge_radius = addon.pref().tools.ndraw.snap_edge_radius
        self.snap_vert_radius = addon.pref().tools.ndraw.snap_vert_radius

    def cache_mesh_elements(self):
        '''Cache boundary vertices and edges for faster access'''
        self.boundary_edges = [e for e in self.bm.edges if len(e.link_faces) < 2]
        self.boundary_verts = {v for e in self.boundary_edges for v in e.verts}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.handle_mouse_move(context, event)
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.handle_left_mouse(context, event)
        elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            self.handle_undo(context)
            return {'FINISHED'}
        elif event.type == 'LEFT_BRACKET':
            if event.value == 'PRESS':
                self.update_drawing_radius(context, event, False, 'VERT')
            elif event.value == 'RELEASE':
                self.clear_drawing_radius(context, event)
        elif event.type == 'RIGHT_BRACKET':
            if event.value == 'PRESS':
                self.update_drawing_radius(context, event, True, 'VERT')
            elif event.value == 'RELEASE':
                self.clear_drawing_radius(context, event)
        elif (event.type == 'LEFT_CTRL' and event.value == 'RELEASE') or (event.type == 'ESC' and event.value == 'PRESS'):
            self.handle_cancel(context)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def handle_mouse_move(self, context, event):
        '''Handle the mouse move event for the pencil tool'''
        mouse_pos = np.array((event.mouse_region_x, event.mouse_region_y))
        if self.last_mouse_position is None or np.linalg.norm(mouse_pos - self.last_mouse_position) > 1:
            self.last_mouse_position = mouse_pos
            self.run(context, event)
            self.update_drawing(context)

    def handle_left_mouse(self, context, event):
        '''Handle the left mouse button press for the pencil tool'''
        bpy.ops.ed.undo_push()
        self.create_mesh(context)
        self.run(context, event)
        bmesh.update_edit_mesh(context.edit_object.data)
        context.area.tag_redraw()

    def handle_undo(self, context):
        '''Undo the pencil tool'''
        self.end(context)
        context.area.tag_redraw()
        bpy.ops.ed.undo()

    def handle_cancel(self, context):
        '''Cancel the pencil tool'''
        addon.pref().tools.ndraw.running = False
        self.end(context)
        context.area.tag_redraw()

    def run(self, context, event):
        '''Run the pencil tool'''
        self.ray_cast(context, event)
        self.detect_edge(context, event)
        self.detect_vert(context, event)

    def end(self, context):
        '''Remove the drawing handlers and reset the pencil tool'''
        self.bm = None
        self.last_mouse_position = None
        self.point = Vector((0, 0, 0))
        self.edge_index = -1
        self.vert_index = -1
        self.boundary_edges = []
        self.boundary_verts = set()
        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')
        self.remove_draw_handlers()

    def remove_draw_handlers(self):
        '''Remove the drawing handlers'''
        handlers = [self._handle_point, self._handles_verts, self._handle_polylines, self._handle_face, self._handle_radius]
        for handler in handlers:
            bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')

    def ray_cast(self, context, event):
        '''Cast a ray in the scene from the viewport camera using the mouse position'''
        mouse = (event.mouse_region_x, event.mouse_region_y)
        ray = scene.ray_cast_visible(context, mouse)
        if ray['hit']:
            self.point = context.edit_object.matrix_world.inverted() @ ray['location']
            addon.pref().tools.ndraw.running = True
        else:
            addon.pref().tools.ndraw.running = False
        context.area.tag_redraw()

    def setup_drawing(self, context):
        '''Setup the drawing for the circle and vertices within the circle'''
        theme = addon.pref().theme.ops.ndraw.pencil
        self._callback_point = DrawCircle([], 12, 2.0, theme.verts, [None], context.region, context.region_data)
        self._handle_point = bpy.types.SpaceView3D.draw_handler_add(self._callback_point.draw, (context,), 'WINDOW', 'POST_PIXEL')

        self._callback_verts = DrawCircle([], 12, 2.0, theme.verts, [], context.region, context.region_data)
        self._handles_verts = bpy.types.SpaceView3D.draw_handler_add(self._callback_verts.draw, (context,), 'WINDOW', 'POST_PIXEL')

        self._callback_polylines = DrawPolyline([], 2.0, theme.edges)
        self._handle_polylines = bpy.types.SpaceView3D.draw_handler_add(self._callback_polylines.draw, (context,), 'WINDOW', 'POST_VIEW')

        self._callback_face = DrawFace([], theme.faces, culling=False)
        self._handle_face = bpy.types.SpaceView3D.draw_handler_add(self._callback_face.draw, (context,), 'WINDOW', 'POST_VIEW')

        self._callback_radius = DrawCircle([], 1, 2.0, theme.radius, [], context.region, context.region_data)
        self._handle_radius = bpy.types.SpaceView3D.draw_handler_add(self._callback_radius.draw, (context,), 'WINDOW', 'POST_PIXEL')

    def update_drawing(self, context):
        '''Update the drawing for the circle and vertices within the circle'''
        obj = context.edit_object
        matrix_world = obj.matrix_world
        point = matrix_world @ self.point
        self._callback_point.update_batch([point])
        if self.mode == 'EDGE':
            verts = self.get_selected_verts(matrix_world)
        elif self.mode == 'QUAD':
            verts = self.get_edge_points(matrix_world)
        self._callback_verts.update_batch(verts)
        polylines = self.get_polyline(verts, matrix_world, point)
        self._callback_polylines.update_batch(polylines)
        if self.mode == 'QUAD':
            face_points = self.get_face_points(polylines)
            self._callback_face.update_batch(face_points)

    def update_drawing_radius(self, context, event, additive, mode):
        '''Update the drawing for the radius of the snapping circle'''
        mouse = (event.mouse_region_x, event.mouse_region_y)
        mouse3d = view3d.region_2d_to_location_3d(context.region, context.region_data, mouse, self.point)

        if additive:
            self.snap_vert_radius += 5
        else:
            self.snap_vert_radius -= 5

        addon.pref().tools.ndraw.snap_vert_radius = self.snap_vert_radius
        radius = self.snap_vert_radius if mode == 'VERT' else self.snap_edge_radius
        self._callback_radius.update_batch([mouse3d], radius=radius)
        context.area.tag_redraw()

    def clear_drawing_radius(self, context, event):
        '''Clear the drawing for the radius of the snapping circle'''
        self._callback_radius.update_batch([], radius=0)
        context.area.tag_redraw()

    def get_selected_verts(self, matrix_world):
        '''Get the selected vertices based on the current selection state'''
        selected_verts = [v for v in self.boundary_verts if v.select]
        if selected_verts:
            return [matrix_world @ v.co for v in selected_verts]
        return []

    def get_edge_points(self, matrix_world):
        '''Get the edge points based on the detected edge'''
        if self.edge_index != -1:
            self.bm.edges.ensure_lookup_table()
            return [matrix_world @ v.co for v in self.bm.edges[self.edge_index].verts]
        return []

    def get_polyline(self, verts, matrix_world, point):
        '''Get the polyline based on the edge points and the detected point'''
        if verts:
            return [[v, point] for v in verts]
        selected_verts = [v for v in self.bm.verts if v.select]
        if len(selected_verts) == 1:
            return [(matrix_world @ selected_verts[0].co, point)]
        return []

    def get_face_points(self, polyline):
        '''Get the face points based on the polyline'''
        if len(polyline) == 2:
            return [[polyline[0][0], polyline[1][0], polyline[0][1]]]
        return []

    def detect_edge(self, context, event):
        '''Detect the edge under the mouse cursor'''
        obj = context.edit_object
        region = context.region
        rv3d = context.region_data
        mouse = np.array((event.mouse_region_x, event.mouse_region_y))
        radius = self.snap_edge_radius
        closest_edge, min_combined_dist = None, float('inf')
        edge_index = -1

        for edge in self.boundary_edges:
            if not edge.select:
                continue
            v1_co_2d, v2_co_2d = self.get_edge_2d_coordinates(edge, obj, region, rv3d)
            if v1_co_2d is None or v2_co_2d is None:
                continue
            combined_dist = self.calculate_edge_distance(mouse, v1_co_2d, v2_co_2d, radius)
            if combined_dist < min_combined_dist:
                min_combined_dist, closest_edge, edge_index = combined_dist, edge, edge.index

        self.edge_index = edge_index if closest_edge else -1

    def get_edge_2d_coordinates(self, edge, obj, region, rv3d):
        '''Get 2D coordinates of edge vertices'''
        v1_co_3d, v2_co_3d = obj.matrix_world @ edge.verts[0].co, obj.matrix_world @ edge.verts[1].co
        return view3d.location_3d_to_region_2d(region, rv3d, v1_co_3d), view3d.location_3d_to_region_2d(region, rv3d, v2_co_3d)

    def calculate_edge_distance(self, mouse, v1_co_2d, v2_co_2d, radius):
        '''Calculate the distance from mouse to edge'''
        dist_to_segment = self.distance_point_to_segment_2d(mouse, v1_co_2d, v2_co_2d)
        dist_to_v1, dist_to_v2 = np.linalg.norm(mouse - np.array(v1_co_2d)), np.linalg.norm(mouse - np.array(v2_co_2d))
        combined_dist = dist_to_segment + min(dist_to_v1, dist_to_v2)
        return combined_dist if combined_dist <= radius else float('inf')

    def distance_point_to_segment_2d(self, pt, v1, v2):
        '''Compute the distance from a point to a line segment in 2D'''
        v1, v2 = np.array(v1), np.array(v2)
        segment, point_vec = v2 - v1, pt - v1
        segment_len_squared = np.dot(segment, segment)
        if segment_len_squared == 0.0:
            return np.linalg.norm(point_vec)
        projection = np.dot(point_vec, segment) / segment_len_squared
        projection = np.clip(projection, 0, 1)
        closest_point = v1 + projection * segment
        return np.linalg.norm(pt - closest_point)

    def detect_vert(self, context, event):
        '''Detect the vertex under the mouse cursor within a snapping range'''
        obj = context.edit_object
        region = context.region
        rv3d = context.region_data
        mouse = np.array((event.mouse_region_x, event.mouse_region_y))
        radius = self.snap_vert_radius
        closest_vert, min_dist = None, float('inf')
        vert_index = -1

        for vert in self.boundary_verts:
            if vert.select:
                continue
            dist = self.calculate_vert_distance(vert, obj, region, rv3d, mouse, radius)
            if dist < min_dist:
                min_dist, closest_vert, vert_index = dist, vert, vert.index

        self.vert_index = vert_index if closest_vert else -1
        self.point = closest_vert.co.copy() if closest_vert else self.point

    def calculate_vert_distance(self, vert, obj, region, rv3d, mouse, radius):
        '''Calculate the distance from mouse to vertex'''
        v_co_2d = view3d.location_3d_to_region_2d(region, rv3d, obj.matrix_world @ vert.co)
        if v_co_2d is None:
            return float('inf')
        dist = np.linalg.norm(mouse - np.array(v_co_2d))
        return dist if dist <= radius else float('inf')

    def create_mesh(self, context):
        '''Create mesh elements based on the current selection state and detected closest edge'''
        selected_verts = [v for v in self.bm.verts if v.select]
        selected_edges = [e for e in self.bm.edges if e.select]

        if self.mode == 'QUAD':
            if not selected_verts:
                self.create_single_vertex()
            elif len(selected_verts) == 1:
                self.create_edge_from_single_vertex(selected_verts[0])
            elif selected_edges:
                self.create_face_from_edge(context)
            else:
                self.create_vertex_at_point()

        elif self.mode == 'EDGE':
            if not selected_verts:
                self.create_single_vertex()
            else:
                self.create_edges_to_point()

        self.update_mesh(context)

        # Update the boundary elements cache
        self.cache_mesh_elements()

    def create_edges_to_point(self):
        '''Create new edges to the detected point'''

        new_vert = self.bm.verts[self.vert_index] if self.vert_index != -1 else self.bm.verts.new(self.point)

        self.bm.verts.index_update()
        selected_verts = [v for v in self.bm.verts if v.select]
        for v in selected_verts:
            if next((edge for edge in v.link_edges if new_vert in edge.verts), None):
                continue
            edge = self.bm.edges.new((v, new_vert))
            edge.select = False

        new_vert.select = True

    def create_single_vertex(self):
        '''Create a single vertex at the detected point'''
        new_vert = self.bm.verts[self.vert_index] if self.vert_index != -1 else self.bm.verts.new(self.point)
        self.bm.verts.index_update()
        new_vert.select = True

    def create_edge_from_single_vertex(self, selected_vert):
        '''Create a new edge from the detected vertex to the closest edge'''
        if self.vert_index != -1:
            snapped_vert = self.bm.verts[self.vert_index]
            edge_between = next((edge for edge in selected_vert.link_edges if snapped_vert in edge.verts), None)
            if edge_between:
                edge_between.select = True
            else:
                new_vert = snapped_vert
                self.bm.edges.new((selected_vert, new_vert))
                new_vert.select = True
        else:
            new_vert = self.bm.verts.new(self.point)
            self.bm.verts.index_update()
            edge = self.bm.edges.new((selected_vert, new_vert))
            new_vert.select = True
            edge.select = True

    def create_face_from_edge(self, context):
        '''Create a new face from the detected edge'''
        if self.edge_index != -1:
            edge = self.bm.edges[self.edge_index]
            verts_to_keep_selected, edge_to_remove = self.handle_face_creation(edge)
            new_vert = self.bm.verts[self.vert_index] if self.vert_index != -1 else self.bm.verts.new(self.point)
            self.bm.verts.index_update()
            face = self.bm.faces.new((edge.verts[0], edge.verts[1], new_vert))

            self.bm.faces.ensure_lookup_table()
            self.update_face_normal(context, face)

            verts_to_keep_selected.append(new_vert)
            for v in self.bm.verts:
                if v not in verts_to_keep_selected:
                    v.select = False

            face.select = True
            if edge_to_remove:
                self.remove_existing_edge_if_needed(context, edge)

        else:
            new_vert = self.bm.verts[self.vert_index] if self.vert_index != -1 else self.bm.verts.new(self.point)
            self.bm.verts.index_update()
            new_vert.select = True

    def handle_face_creation(self, edge):
        '''Handle the creation of face'''
        verts_to_keep_selected = []
        remove_edge = len(edge.link_faces) == 1 and edge.link_faces[0].select and len(edge.link_faces[0].verts) == 3
        if remove_edge:
            verts_to_keep_selected.extend(edge.link_faces[0].verts)
        return verts_to_keep_selected, remove_edge

    def update_face_normal(self, context, face):
        '''Update the normal of the face to ensure it is facing the viewport'''
        face.normal_update()

        # Get the view direction
        rv3d = context.region_data
        view_dir = (rv3d.view_rotation @ Vector((0, 0, -1))).normalized()

        # Get the face normal in world space
        face_normal_world = context.edit_object.matrix_world.to_3x3() @ face.normal

        # Check if the face normal is facing the viewport direction
        if face_normal_world.dot(view_dir) > 0:
            bmesh.ops.reverse_faces(self.bm, faces=[face])

        self.bm.normal_update()

    def remove_existing_edge_if_needed(self, context, edge):
        '''Remove existing edge if needed'''
        bmesh.ops.dissolve_edges(self.bm, edges=[edge])
        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)

    def create_vertex_at_point(self):
        '''Create a new vertex at the detected point'''
        new_vert = self.bm.verts[self.vert_index] if self.vert_index != -1 else self.bm.verts.new(self.point)
        self.bm.verts.index_update()
        new_vert.select = True

    def update_mesh(self, context):
        '''Update the mesh after creation'''
        self.bm.normal_update()
        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)
        self.bm.select_flush_mode()

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar for the "MOVE" state.'''
        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Draw')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_CTRL')
        row.label(text='Cancel')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_LEFTBRACKET')
        row.label(text='', icon='EVENT_RIGHTBRACKET')
        row.label(text='Snap Radius')


class types:
    class theme(bpy.types.PropertyGroup):
        verts: bpy.props.FloatVectorProperty(name="verts", description="Color of the verts", size=4, subtype='COLOR', default=(0.18, 0.58, 1, 0.7), min=0.0, max=1.0)
        edges: bpy.props.FloatVectorProperty(name="edges", description="Color of the edges", size=4, subtype='COLOR', default=(0.18, 0.58, 1, 0.7), min=0.0, max=1.0)
        faces: bpy.props.FloatVectorProperty(name="faces", description="Color of the faces", size=4, subtype='COLOR', default=(0.18, 0.38, 0.6, 0.2), min=0.0, max=1.0)
        radius: bpy.props.FloatVectorProperty(name="radius", description="Color of the radius", size=4, subtype='COLOR', default=(0.1, 0.1, 0.1, 1), min=0.0, max=1.0)


types_classes = (types.theme,)
