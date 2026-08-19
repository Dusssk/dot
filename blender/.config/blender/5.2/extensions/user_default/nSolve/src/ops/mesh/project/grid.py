import math
import bpy
import bmesh

from mathutils import Vector, geometry

from .utils import project_polylines
from ...utils import infobar
from ....draw.polyline import DrawPolyline
from .....utils import view3d, addon


class NSOLVE_OT_ProjectGrid(bpy.types.Operator):
    bl_idname = "nsolve.project_grid"
    bl_label = "Project Grid"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = f"{bl_label}\n\nProject the grid over selected faces"

    bm: bmesh.types.BMesh

    face_maps: list = []
    face_maps_data: dict = {}

    segments_x: bpy.props.IntProperty(name="Segments X", description="Number of segments in X direction", default=7, min=3, max=256)
    segments_y: bpy.props.IntProperty(name="Segments Y", description="Number of segments in Y direction", default=7, min=3, max=256)

    guid: list = []
    polylines: list = []

    mouse_pos: Vector

    _callback_line: DrawPolyline
    _handle_line: int
    _callback_guid: DrawPolyline
    _handle_guid: int

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'segments_x')
        layout.prop(self, 'segments_y')

    def invoke(self, context, event):

        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        selected_faces = [f for f in self.bm.faces if f.select]

        # Step 1: Detect Continuous Regions
        self.face_maps = self.detect_continuous_regions(selected_faces)

        if not self.face_maps:
            self.report({'WARNING'}, 'No faces selected.')
            return {'CANCELLED'}

        self.face_maps_data = {}

        # Step 2: For each face map, find its outer edges, midpoint, and normal
        for index, face_map in enumerate(self.face_maps):
            outer_edges = self.find_outer_edges(face_map)
            midpoint, normal = self.calculate_midpoint_and_normal(face_map)

            # Store in face_maps_data
            self.face_maps_data[index] = {
                "face_map": face_map,
                "outer_edges": outer_edges,
                "midpoint": midpoint,
                "normal": normal
            }

        # deslect all faces
        for face in selected_faces:
            face.select = False

        # Select outer edges
        for face_map, data in self.face_maps_data.items():
            outer_edges = data["outer_edges"]
            for edge in outer_edges:
                edge.select = True

        bmesh.update_edit_mesh(obj.data)

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set('Project Grid')
        context.window.cursor_set('SCROLL_XY')

        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Project Grid", position=(50, 2))
        return {'RUNNING_MODAL'}

    def calculate_midpoint_and_normal(self, face_map):
        verts = [vert.co for face in face_map for vert in face.verts]
        midpoint = sum(verts, Vector()) / len(verts)

        normals = [face.normal for face in face_map]
        normal = sum(normals, Vector()) / len(normals)

        return midpoint, normal

    def detect_continuous_regions(self, selected_faces):
        visited = set()
        face_maps = []

        for face in selected_faces:
            if face not in visited:
                new_group = []
                stack = [face]  # Use a list as a stack

                while stack:
                    current_face = stack.pop()  # Pop from the end of the list
                    if current_face not in visited:
                        visited.add(current_face)
                        new_group.append(current_face)

                        # Add connected, selected faces to the stack
                        for edge in current_face.edges:
                            for linked_face in edge.link_faces:
                                if linked_face in selected_faces and linked_face not in visited:
                                    stack.append(linked_face)

                face_maps.append(new_group)

        return face_maps

    def find_outer_edges(self, face_group):
        edge_count = {}

        for face in face_group:
            for edge in face.edges:
                if edge not in edge_count:
                    edge_count[edge] = 0
                edge_count[edge] += 1

        # Outer edges are those that appear exactly once in the group
        outer_edges = [edge for edge, count in edge_count.items() if count == 1]

        return outer_edges

    def snap(self, context, precision=False):

        angle_increment = math.radians(15)
        if precision:
            angle_increment = math.radians(5)

        obj = context.edit_object
        midpoint = obj.matrix_world @ self.face_maps_data[0]['midpoint']
        median = view3d.location_3d_to_region_2d(context.region, context.space_data.region_3d, midpoint)

        # Calculate the 2D angle from initial to current mouse position
        angle = math.atan2(self.mouse_pos[1] - median[1], self.mouse_pos[0] - median[0])
        snap_angle_rad = angle_increment
        snapped_angle = round(angle / snap_angle_rad) * snap_angle_rad

        # Calculate the distance to maintain from start to current position
        distance = (self.mouse_pos - median).length

        # Create a direction vector from the snapped angle
        direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))

        # Update current mouse position in 2D based on the snapped direction and original distance
        snaped_mouse_pos = median + direction * distance

        return snaped_mouse_pos

    def define_grid(self, context, obj, face_map_data):
        '''Define the grid based on the face map data'''

        region = context.region
        rv3d = context.region_data

        # The correct forward vector from the camera towards the scene
        view_normal = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
        midpoint = obj.matrix_world @ face_map_data['midpoint']

        # Calculate the intersection point for the radius and direction from center
        intersect_point = view3d.region_2d_to_location_3d(region, rv3d, self.mouse_pos, midpoint)

        direction_y = (midpoint - intersect_point).normalized()  # Normalized direction (plane normal)

        # Compute X direction, perpendicular to both Y direction and face normal
        direction_x = direction_y.cross(view_normal).normalized()

        segments_x = self.segments_x
        segments_y = self.segments_y
        distance = (intersect_point - midpoint).length

        outer_edges = face_map_data['outer_edges']
        self.polylines.clear()

        # Generate grid points for Y segments
        seg_y = segments_y - 1
        for segment_y_index in range(-seg_y // 2, seg_y // 2 + 1):
            segment_midpoint_y = midpoint + direction_y * distance * segment_y_index
            self.generate_polylines(obj, segment_midpoint_y, direction_y, outer_edges)

        # Generate grid points for X segments
        seg_x = segments_x - 1
        for segment_x_index in range(-seg_x // 2, seg_x // 2 + 1):
            segment_midpoint_x = midpoint + direction_x * distance * segment_x_index
            self.generate_polylines(obj, segment_midpoint_x, direction_x, outer_edges)

    def generate_polylines(self, obj, segment_midpoint, direction, outer_edges):
        '''Generate polylines from the intersection points'''

        intersect_points = []
        for edge in outer_edges:
            p1_world = obj.matrix_world @ edge.verts[0].co
            p2_world = obj.matrix_world @ edge.verts[1].co

            # Define the plane for intersection
            intersect_point = geometry.intersect_line_plane(p1_world, p2_world, segment_midpoint, direction)
            if intersect_point and 0 <= geometry.intersect_point_line(intersect_point, p1_world, p2_world)[1] <= 1:
                intersect_points.append(intersect_point)

        # Generate polylines from the intersect points
        for i in range(0, len(intersect_points) - 1, 2):
            polyline = [intersect_points[i], intersect_points[i + 1]]
            self.polylines.append(polyline)

    def execute(self, context):

        self.polylines.clear()

        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        selected_faces = [f for f in self.bm.faces if f.select]

        # Step 1: Detect Continuous Regions
        self.face_maps = self.detect_continuous_regions(selected_faces)

        if not self.face_maps:
            self.report({'WARNING'}, 'No faces selected.')
            return {'CANCELLED'}

        self.face_maps_data = {}

        # Step 2: For each face map, find its outer edges, midpoint, and normal
        for index, face_map in enumerate(self.face_maps):
            outer_edges = self.find_outer_edges(face_map)
            midpoint, normal = self.calculate_midpoint_and_normal(face_map)

            # Store in face_maps_data
            self.face_maps_data[index] = {
                "face_map": face_map,
                "outer_edges": outer_edges,
                "midpoint": midpoint,
                "normal": normal
            }

        self.define_grid(context, context.edit_object, self.face_maps_data[0])
        project_polylines(self.polylines)

        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            obj = context.edit_object

            self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.polylines.clear()

            use_snap = context.scene.tool_settings.use_snap or event.ctrl
            if use_snap:
                if event.shift:
                    self.mouse_pos = self.snap(context, precision=True)
                else:
                    self.mouse_pos = self.snap(context)

            self.define_grid(context, obj, self.face_maps_data[0])
            self.update_drawing(context)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            project_polylines(self.polylines)
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.end(context)
            return {'CANCELLED'}

        elif event.type == 'WHEELUPMOUSE' or event.type == 'NUMPAD_PLUS' or event.type == 'EQUAL':
            if event.value == 'PRESS':
                if event.ctrl:
                    self.segments_y += 1
                self.segments_x += 1

        elif event.type == 'WHEELDOWNMOUSE' or event.type == 'NUMPAD_MINUS' or event.type == 'MINUS':
            if event.value == 'PRESS':
                if event.ctrl:
                    self.segments_y -= 1
                self.segments_x -= 1

        return {'RUNNING_MODAL'}

    def end(self, context):
        '''Cleanup and finish the operator'''

        self.bm = None
        self.face_maps = []
        self.face_maps_data = {}

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_guid, 'WINDOW')

        context.area.tag_redraw()

    def update_drawing(self, context):
        '''Update the drawing'''

        all_segments = []
        for polyline in self.polylines:
            # Iterate through each point in the polyline, skipping one to create pairs
            segments = [(polyline[i], polyline[i+1]) for i in range(0, len(polyline), 2)]
            for segment in segments:
                all_segments.append(segment)

        theme = addon.pref().theme.ops.mesh.project.grid

        color = theme.line
        self._callback_line.update_batch(all_segments, color=color)
        color = theme.guid
        self._callback_guid.update_batch(self.guid, color=color)

    def setup_drawing(self, context, points=None):
        '''Setup the drawing'''

        theme = addon.pref().theme.ops.mesh.project.grid

        points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
        color = theme.line
        self._callback_line = DrawPolyline(points, width=2.0, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

        color = theme.guid
        self._callback_guid = DrawPolyline(points, width=1.2, color=color)
        self._handle_guid = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

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


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Project Grid Line", description="Line color", default=(0.5, 0.4, 0.8, 1.0), subtype='COLOR', size=4, min=0.0, max=1.0)
        guid: bpy.props.FloatVectorProperty(name="Project Grid Guide", description="Guide color", default=(0.0, 0.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    types.theme,
)
