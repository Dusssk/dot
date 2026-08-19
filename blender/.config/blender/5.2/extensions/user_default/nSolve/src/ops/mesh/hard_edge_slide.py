import bpy
import bmesh
from mathutils import Vector, geometry

from ..utils import infobar
from ...draw.polyline import DrawPolyline
from ....utils import view3d, addon

from ... import analytics


class NSOLVE_OT_HardEdgeSlide(bpy.types.Operator):
    bl_idname = "nsolve.hard_edge_slide"
    bl_label = "Hard Edge Slide"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = f"{bl_label}\n\nSlide a new edge parallel to a selected edge along a linked face"

    bm: bmesh.types.BMesh
    edge: bmesh.types.BMEdge
    start_mouse_pos: Vector
    mouse_pos: Vector

    _callback_line: DrawPolyline
    _handle_line: int
    _callback_guid: DrawPolyline
    _handle_guid: int

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        selected_edges = [e for e in self.bm.edges if e.select]

        if not selected_edges:
            self.report({'ERROR'}, "No edge selected.")
            return {'CANCELLED'}

        self.edge = selected_edges[0]

        faces = [f for f in self.edge.link_faces]

        if len(faces) < 1:
            self.report({'ERROR'}, "Selected edge has no linked faces.")
            return {'CANCELLED'}

        elif len(faces) > 2:
            self.report({'ERROR'}, "Selected edge has more than two linked faces.")
            return {'CANCELLED'}

        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Hard Edge Slide", position=(50, 2))
        analytics.stats("nSuite: Hard Edge Slide")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            self.update_drawing(context)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            self.create_edge(context)
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True

    def end(self, context):
        '''Cleanup and finish the operator'''

        self.bm = None
        self.edge = None

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_guid, 'WINDOW')
        # bpy.types.SpaceView3D.draw_handler_remove(self._handle_debug_plane, 'WINDOW')
        context.area.tag_redraw()

    def calculate_edge_info(self, obj):
        '''Calculate the midpoint and direction of the edge in world space'''

        start_world = obj.matrix_world @ self.edge.verts[0].co
        end_world = obj.matrix_world @ self.edge.verts[1].co
        midpoint_world = (start_world + end_world) / 2
        direction_world = (end_world - start_world).normalized()
        return midpoint_world, direction_world

    def get_edge_faces_bitangents(self, obj, edge_midpoint_world, edge_dir_world):
        '''Calculate the bitangents of the linked faces of the edge'''

        # Initialize storage for lines
        bitangents = []

        # Process each linked face individually
        for face in self.edge.link_faces:
            face_intersection_points_world = []

            # Iterate through vertices of the face
            for vert in face.verts:
                # Skip vertices that are part of the original edge
                if vert in self.edge.verts:
                    continue

                vert_world = obj.matrix_world @ vert.co  # Vertex position in world space
                vert_line_end_world = vert_world + edge_dir_world  # Extend in the direction of edge_dir_world

                # Calculate the intersection with the plane
                intersect_point_world = geometry.intersect_line_plane(vert_world, vert_line_end_world, edge_midpoint_world, edge_dir_world, False)

                # Check if the intersection point is valid and unique before adding
                if intersect_point_world:
                    face_intersection_points_world.append(intersect_point_world)

            # For each face, add a line from the original midpoint to the farthest intersection point
            if face_intersection_points_world:
                # Sort intersection points by their distance from the original midpoint
                sorted_points = sorted(face_intersection_points_world, key=lambda p: (p - edge_midpoint_world).length, reverse=True)
                farthest_point = sorted_points[0]
                bitangents.append((edge_midpoint_world, farthest_point))

        return bitangents

    def get_closest_line_segment(self, lines, mouse_pos_3d):
        '''Find the closest line segment to the mouse position'''

        # Identify the closest line segment to the mouse position
        closest_distance = float('inf')
        closest_segment = None
        for line in lines:
            point_on_line, fraction = geometry.intersect_point_line(mouse_pos_3d, line[0], line[1])
            if fraction < 0:
                point_on_line = line[0]  # Closest point is the start of the segment
            elif fraction > 1:
                point_on_line = line[1]  # Closest point is the end of the segment
            # Now point_on_line is guaranteed to be the closest point on the segment

            distance = (mouse_pos_3d - point_on_line).length
            if distance < closest_distance:
                closest_distance = distance
                closest_segment = line

        return closest_segment

    def calculate_intersection_points(self, obj, plane_co, plane_normal, selected_face):
        '''Calculate the intersection points of the edge with the plane'''

        intersection_points_edges = []
        for edge in selected_face.edges:
            v1_world = obj.matrix_world @ edge.verts[0].co
            v2_world = obj.matrix_world @ edge.verts[1].co

            intersect_point = geometry.intersect_line_plane(v1_world, v2_world, plane_co, plane_normal, False)
            if intersect_point and 0 <= geometry.intersect_point_line(intersect_point, v1_world, v2_world)[1] <= 1:
                intersection_points_edges.append((intersect_point, edge))
        return intersection_points_edges

    def get_line_segments(self, intersection_points):
        '''Get line segments from the intersection points'''

        line_segments = []
        for i in range(0, len(intersection_points), 2):
            if i + 1 < len(intersection_points):
                line_segments.append((intersection_points[i], intersection_points[i + 1]))

        return line_segments

    def update_drawing(self, context):
        obj = context.active_object
        region = context.region
        rv3d = context.region_data

        mouse_pos = self.mouse_pos

        theme = addon.pref().theme.ops.mesh.hard_edge_slide

        # Use already defined functions for calculating world space info and getting bitangents
        edge_midpoint_world, edge_dir_world = self.calculate_edge_info(obj)
        bitangents = self.get_edge_faces_bitangents(obj, edge_midpoint_world, edge_dir_world)

        mouse_pos_3d = view3d.region_2d_to_location_3d(region, rv3d, Vector(mouse_pos), edge_midpoint_world)
        closest_segment = self.get_closest_line_segment(bitangents, mouse_pos_3d)

        if closest_segment:
            closest_line_vector = closest_segment[1] - closest_segment[0]
            plane_co = view3d.region_2d_to_nearest_point_on_line_3d(region, rv3d, Vector(mouse_pos), closest_segment[0], closest_line_vector)

            selected_face = self.edge.link_faces[0] if closest_segment == bitangents[0] else self.edge.link_faces[1]
            plane_normal = edge_dir_world.cross(obj.matrix_world.to_3x3() @ selected_face.normal).normalized()

            if plane_co:
                intersection_points_edges = self.calculate_intersection_points(obj, plane_co, plane_normal, selected_face)
                intersection_points = [point for point, _ in intersection_points_edges]

                line_segments = self.get_line_segments(intersection_points)
                if line_segments:
                    self._callback_line.update_batch(line_segments, color=theme.line)

        if bitangents:
            self._callback_guid.update_batch(bitangents, color=theme.guid)
        else:
            print("Not enough intersection points to draw bitangent lines.")

    def setup_drawing(self, context, points=None):
        '''Setup the drawing'''

        theme = addon.pref().theme.ops.mesh.hard_edge_slide

        points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
        color = theme.line
        self._callback_line = DrawPolyline(points, width=1.0, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

        color = theme.guid
        self._callback_guid = DrawPolyline(points, width=0.8, color=color)
        self._handle_guid = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

    def create_edge(self, context):
        '''Create a new edge parallel to the selected edge'''

        obj = context.edit_object
        region = context.region
        rv3d = context.region_data

        mouse_pos = self.mouse_pos

        # Use already defined functions for calculating world space info and getting bitangents
        edge_midpoint_world, edge_dir_world = self.calculate_edge_info(obj)
        bitangents = self.get_edge_faces_bitangents(obj, edge_midpoint_world, edge_dir_world)

        mouse_pos_3d = view3d.region_2d_to_location_3d(region, rv3d, Vector(mouse_pos), edge_midpoint_world)
        closest_segment = self.get_closest_line_segment(bitangents, mouse_pos_3d)

        if closest_segment:
            closest_line_vector = closest_segment[1] - closest_segment[0]
            plane_co = view3d.region_2d_to_nearest_point_on_line_3d(region, rv3d, Vector(mouse_pos), closest_segment[0], closest_line_vector)

            selected_face = self.edge.link_faces[0] if closest_segment == bitangents[0] else self.edge.link_faces[1]
            plane_normal = edge_dir_world.cross(obj.matrix_world.to_3x3() @ selected_face.normal).normalized()

            if plane_co:
                intersection_points_edges = self.calculate_intersection_points(obj, plane_co, plane_normal, selected_face)
                # Create a mapping of original edges to their newly created vertices at intersection points
                created_verts = []

                for intersect_point, edge in intersection_points_edges:
                    # Transform the intersection point back to the object's local space
                    intersect_point_local = obj.matrix_world.inverted() @ intersect_point

                    result = bmesh.utils.edge_split(edge, edge.verts[0], 0.5)
                    result[1].co = intersect_point_local
                    created_verts.append(result[1])

                if created_verts:
                    vert_pairs = [(created_verts[i], created_verts[i+1]) for i in range(0, len(created_verts), 2)]
                    for vert_pair in vert_pairs:
                        bmesh.ops.connect_vert_pair(self.bm, verts=vert_pair)

                # Update mesh to reflect changes
                bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust Radius')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Hard Edge Slide Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 1.0), min=0.0, max=1.0)
        guid: bpy.props.FloatVectorProperty(name="Hard Edge Slide guid", description="Color of the guid", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 0.5), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
