import bpy
import bmesh

from mathutils import Vector, Matrix

from .utils import project_polyline_indexed
from ...utils import infobar
from ....draw.polyline import DrawPolyline
from ....draw.points import DrawPoints
from .....utils import view3d, addon


class NSOLVE_OT_ProjectLoop(bpy.types.Operator):
    bl_idname = "nsolve.project_loop"
    bl_label = "Project Loop"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = f"{bl_label}\n\nSlide a new edge parallel to a selected edge along a linked face"

    debug: bool = False

    mode: bpy.props.EnumProperty(items=(('SLIDE', 'Slide', 'Slide along the loop'), ('EXTEND', 'Extend', 'Extend the verts of the loop'), ('OFFSET', "Offset", "Slide and Extend the verts of the loop")), name='Mode', default='SLIDE')

    orientation: bpy.props.EnumProperty(items=(('GLOBALX', 'Global X', 'Global X orientation'),
                                               ('GLOBALY', 'Global Y', 'Global Y orientation'),
                                               ('GLOBALZ', 'Global Z', 'Global Z orientation'),
                                               ('LOCALX', 'Local X', 'Local X orientation'),
                                               ('LOCALY', 'Local Y', 'Local Y orientation'),
                                               ('LOCALZ', 'Local Z', 'Local Z orientation'),
                                               ('FACEB', 'Face Bitangent', 'Face Bitangent orientation')),
                                        name='Orientation', default='FACEB')

    state: str = 'SET'
    last_stat: str = 'SET'

    matrix_transform: Matrix = Matrix()
    mouse_pos_delta: Vector = Vector((0, 0))
    distance: float = 0.0
    distance_delta: float = 0.0

    side: str = 'side_a'

    bm: bmesh.types.BMesh

    mouse_pos: Vector = Vector((0, 0))
    start_mouse_pos: Vector = Vector((0, 0))
    start_position: Vector = Vector((0, 0, 0))
    mouse_prev = Vector((0.0, 0.0))
    input_plane_mat = Matrix()
    start_input3d = Vector((0, 0, 0))

    edge: bmesh.types.BMEdge
    edges: list = []
    closed_loop: bool = False
    edge_data: dict = {}

    polylines: list = []
    polylines_id: list = []
    tweek_ids: list[int] = []
    tweak_back: list[Vector] = []
    base_verts: set[int] = set()
    tweakable_id: list[int]

    vert_radius = 1.0
    vert_color = 0.4, 0.6, 0.4, 0.7

    _callback_polyline: DrawPolyline
    _handle_line: int
    _callback_guid: DrawPolyline
    _handle_bitangent: int
    _callback_points: DrawPoints
    _handle_points: int

    _debug_callback_tangents: DrawPolyline
    _debug_handle_tangents: int
    _debug_callback_verts_bitangents: DrawPolyline
    _debug_handle_verts_bitangents: int

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def check_continuous_loop(self, selected_edges):
        '''Check if the selected edges form a continuous loop'''

        edge_vertex_counts = {}
        for edge in selected_edges:
            for vert in edge.verts:
                if vert not in edge_vertex_counts:
                    edge_vertex_counts[vert] = 1
                else:
                    edge_vertex_counts[vert] += 1

        # Find end vertices (vertices with only one connected selected edge)
        end_verts = [vert for vert, count in edge_vertex_counts.items() if count == 1]

        # Valid continuous loop conditions: 0 end vertices (closed loop) or 2 end vertices (open loop)
        if len(end_verts) in [0, 2]:
            return True, end_verts
        else:
            return False, []

    def order_selected_edges(self, selected_edges, end_verts):
        '''Order the selected edges based on the end vertices'''

        # Start with an edge that contains an end vertex or any edge if it's a closed loop
        start_edge = None
        if end_verts:
            for edge in selected_edges:
                if end_verts[0] in edge.verts:
                    start_edge = edge
                    break
        else:
            start_edge = selected_edges[0]

        ordered_edges = [start_edge]
        current_edge = start_edge
        while len(ordered_edges) < len(selected_edges):
            next_edge = None
            for vert in current_edge.verts:
                for edge in vert.link_edges:
                    if edge in selected_edges and edge not in ordered_edges:
                        next_edge = edge
                        break
                if next_edge:
                    break

            if not next_edge: break

            ordered_edges.append(next_edge)
            current_edge = next_edge

        return ordered_edges

    def organize_faces_by_previous_edge(self, current_edge, previous_edge_data):
        '''Organize the faces based on the previous edge's data'''

        # Initialize placeholders for the faces and their similarity measures
        closest_normal_similarity = -1  # Start with the lowest possible dot product value
        closest_face = None
        closest_side = None

        # Iterate over the current edge's linked faces
        for current_face in current_edge.link_faces:
            # Calculate dot product (similarity) with both previous self.side faces
            dot_with_side_a = current_face.normal.dot(previous_edge_data['side_a'].normal)
            dot_with_side_b = current_face.normal.dot(previous_edge_data['side_b'].normal)

            # Determine the higher similarity for the current face
            if dot_with_side_a > closest_normal_similarity:
                closest_normal_similarity = dot_with_side_a
                closest_face = current_face
                closest_side = 'side_a'
            if dot_with_side_b > closest_normal_similarity:
                closest_normal_similarity = dot_with_side_b
                closest_face = current_face
                closest_side = 'side_b'

        if len(current_edge.link_faces) > 1:
            # The other face is simply the one that's not closest_face
            other_face = next(face for face in current_edge.link_faces if face != closest_face)

            # Assign faces to sides based on the closest match
            if closest_side == 'side_a':
                side_a_face = closest_face
                side_b_face = other_face
            else:
                side_a_face = other_face
                side_b_face = closest_face

        else:
            side_a_face = closest_face
            side_b_face = closest_face

        # Calculate midpoint and direction as before
        shared_vertex = next((v for v in current_edge.verts if v in previous_edge_data['edge'].verts), None)
        direction = (next(v for v in current_edge.verts if v != shared_vertex).co - shared_vertex.co).normalized()
        midpoint = (current_edge.verts[0].co + current_edge.verts[1].co) / 2

        return side_a_face, side_b_face, midpoint, direction, current_edge

    def get_initial_edge_data(self, first_edge, second_edge=None):
        '''Get the initial data for the first edge'''

        # Check if there's a second edge to determine the unshared vertex for the initial direction
        if second_edge:
            unshared_vertex = None
            for vert in first_edge.verts:
                if vert not in second_edge.verts:
                    unshared_vertex = vert
                    break

            # Assuming unshared_vertex is the starting point, determine direction towards the other vertex in the edge
            if unshared_vertex:
                other_vertex = next(vert for vert in first_edge.verts if vert != unshared_vertex)
                direction = (other_vertex.co - unshared_vertex.co).normalized()
            else:
                # This case should not happen when there's a second edge
                direction = (first_edge.verts[1].co - first_edge.verts[0].co).normalized()
        else:
            # If there is no second edge, just pick the first vertex as the start
            direction = (first_edge.verts[1].co - first_edge.verts[0].co).normalized()

        # Initial midpoint
        midpoint = (first_edge.verts[0].co + first_edge.verts[1].co) / 2

        # Faces assignment
        faces = list(first_edge.link_faces)

        if len(faces) == 1:
            side_a_face = side_b_face = faces[0]
        else:
            side_a_face, side_b_face = faces[0], faces[1]

        return side_a_face, side_b_face, midpoint, direction, first_edge

    def get_edges_data(self, edges):
        '''Get the data for the selected edges'''

        edges_data = {}
        for i, edge in enumerate(edges):
            if i == 0:
                # Special handling for the first edge with consideration for the direction towards the second edge
                second_edge = edges[1] if len(edges) > 1 else None  # Ensure there is a second edge
                side_a_face, side_b_face, midpoint, direction, _edge = self.get_initial_edge_data(edge, second_edge)
                edges_data[edge] = {
                    'side_a': side_a_face,
                    'side_b': side_b_face,
                    'mid': midpoint,
                    'direction': direction,
                    'edge': _edge,
                    'bitangent': None,
                }
            else:
                previous_edge_data = edges_data[edges[i-1]]
                side_a_face, side_b_face, midpoint, direction, edge = self.organize_faces_by_previous_edge(edge, previous_edge_data)
                edges_data[edge] = {
                    'side_a': side_a_face,
                    'side_b': side_b_face,
                    'mid': midpoint,
                    'direction': direction,
                    'edge': edge,
                    'bitangent': None,
                }
        return edges_data

    def check_edge_connectivity(self, selected_edges):
        """
        Check if each edge in selected_edges is connected to more than 2 other edges from selected_edges.
        Returns True if the condition is met for all edges, False otherwise.
        """
        # Map vertices to their connected selected edges using a standard dict
        vertex_to_edges = {}
        for edge in selected_edges:
            for vert in edge.verts:
                vert_index = vert.index
                if vert_index not in vertex_to_edges:
                    vertex_to_edges[vert_index] = [edge]
                else:
                    vertex_to_edges[vert_index].append(edge)

        # Check if any selected edge is connected to more than 2 other selected edges
        for edge in selected_edges:
            connected_edges_count = sum(
                1 for vert in edge.verts for connected_edge in vertex_to_edges.get(vert.index, []) if connected_edge != edge)
            if connected_edges_count > 2:
                # Found an edge connected to more than 2 other selected edges
                return False
        return True  # All edges pass the check

    def invoke(self, context, event):
        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        selected_edges = [e for e in self.bm.edges if e.select]
        if not selected_edges:
            self.report({'ERROR'}, "No edge selected.")
            return {'CANCELLED'}

        # Use the new method to check edge connectivity
        if not self.check_edge_connectivity(selected_edges):
            self.report({'ERROR'}, "Selected edges do not form a continuous loop.")
            return {'CANCELLED'}

        # Check if selected edges form a continuous loop
        is_continuous, end_verts = self.check_continuous_loop(selected_edges)
        if not is_continuous:
            self.report({'ERROR'}, "Selected edges do not form a continuous loop.")
            return {'CANCELLED'}

        # return if any of the ange has less then 2 faces
        for edge in selected_edges:
            if len(edge.link_faces) < 1:
                self.report({'ERROR'}, "Edges of Selected edgeloop need to have at least 1 face.")
                return {'CANCELLED'}

        # Get selected edges in order
        self.edges = self.order_selected_edges(selected_edges, end_verts)
        if len(self.edges) > 2:

            first_edge_verts = set(v.index for v in self.edges[0].verts)
            last_edge_verts = set(v.index for v in self.edges[-1].verts)

            if first_edge_verts & last_edge_verts:
                self.closed_loop = True

        # Attempt to set self.edge as the last edge in the selection history
        last_selected_edge = None
        for elem in reversed(self.bm.select_history):
            if isinstance(elem, bmesh.types.BMEdge) and elem.select:
                last_selected_edge = elem
                break

        self.edge = last_selected_edge if last_selected_edge else selected_edges[-1]
        self.edge = self.edge if self.edge in self.edges else self.edges[0]
        self.edge_data = self.get_edges_data(self.edges)

        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        theme = addon.pref().theme.ops.mesh.project.loop
        self.vert_radius = theme.vert_radius
        self.vert_color = theme.vert_color

        region = context.region
        rv3d = context.region_data

        self.start_position = view3d.region_2d_to_location_3d(region, rv3d, self.start_mouse_pos, self.edge_data[self.edge]['mid'])

        self.polylines = []
        self.polylines_id = []
        self.update_edgedata_bitangents(context)

        if self.mode == 'SLIDE' or self.mode == 'OFFSET':
            self.define_loop(context, self.distance)
        if self.mode == 'EXTEND' or self.mode == 'OFFSET':
            self.define_tangents(context, self.distance)

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        if self.mode == 'SLIDE':
            context.area.header_text_set('Project Loop,    mode: Slide')
        elif self.mode == 'EXTEND':
            context.area.header_text_set('Project Loop,    mode: Extend')
        elif self.mode == 'OFFSET':
            context.area.header_text_set('Project Loop,    mode: Offset')

        context.window.cursor_set('SCROLL_XY')

        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Project Loop", position=(50, 2))
        return {'RUNNING_MODAL'}

    def get_offset(self, context, mouse_pos, start_mouse_pos, reference_point_3d):
        '''Get the delta for move in 3D space'''

        # Get the region and RV3D from the context
        region = context.region
        rv3d = context.region_data

        # Convert the start and current mouse positions to 3D space
        start_mouse_pos_3d = view3d.region_2d_to_location_3d(region, rv3d, start_mouse_pos, reference_point_3d)
        mouse_pos_3d = view3d.region_2d_to_location_3d(region, rv3d, mouse_pos, reference_point_3d)

        # Calculate the delta in 3D space
        offset_3d = mouse_pos_3d - start_mouse_pos_3d
        matrix = Matrix.Translation(offset_3d)

        return matrix

    def modal(self, context, event):
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        if event.type == 'MOUSEMOVE':

            self.update_edgedata_bitangents(context)
            obj = context.edit_object
            edge_bitangent = self.edge_data[self.edge]['bitangent']
            bitangent = self.set_orientation(context, edge_bitangent)


            distance = self.get_distance(context, mouse_pos, self.start_position, bitangent)
            if self.state == 'SET':
                self.distance = distance - self.distance_delta
                self.mouse_pos = mouse_pos - self.mouse_pos_delta
            elif self.state == 'MOVE':
                self.distance_delta = distance - self.distance
                self.mouse_pos_delta = mouse_pos - self.mouse_pos
                self.matrix_transform = self.get_offset(context, mouse_pos, self.mouse_pos, self.start_position)
            elif self.state == 'TWEAK':
                self.tweek_ids.clear()

                for i in self.tweakable_id:
                    v3d = self.polylines[i]
                    v2d = view3d.location_3d_to_region_2d(context.region, context.space_data.region_3d, v3d, default=None)

                    if not v2d: continue

                    d = v2d - mouse_pos
                    if d.length < self.vert_radius:
                        self.tweek_ids.append(i)

            elif self.state == 'TWEAK_GRAB':
                for i, back in zip(self.tweek_ids, self.tweak_back):
                    v3d = self.polylines[i]
                    input3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, mouse_pos, self.input_plane_mat.translation)

                    self.polylines[i] = back + input3d - self.start_input3d

            if self.state not in {'TWEAK', 'TWEAK_GRAB'}:
                self.polylines.clear()
                self.polylines_id.clear()

                if self.mode == 'SLIDE' or self.mode == 'OFFSET':
                    self.define_loop(context, self.distance)
                if self.mode == 'EXTEND' or self.mode == 'OFFSET':
                    self.define_tangents(context, self.distance)

            self.update_drawing(context, self.distance)
            context.area.tag_redraw()

            self.mouse_prev = mouse_pos

        elif event.type == 'LEFTMOUSE':
            if self.state == 'TWEAK':
                if event.value == 'PRESS':
                    if self.tweak_grab_prep(context, mouse_pos):
                        self.state = 'TWEAK_GRAB'

            elif self.state =='TWEAK_GRAB':
                if event.value == 'RELEASE':
                    self.state = 'TWEAK'

            else:
                project_polyline_indexed(self.polylines, self.polylines_id)
                self.end(context)

                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.end(context)
            return {'CANCELLED'}

        elif event.type == 'F' and event.value == 'PRESS':
            if self.orientation == 'FACEB':
                self.side = 'side_b' if self.side == 'side_a' else 'side_a'
            else:
                self.orientation = 'FACEB'
            infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'X' and event.value == 'PRESS':
            self.orientation = 'LOCALX' if self.orientation == 'GLOBALX' else 'GLOBALX'
            infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'Y' and event.value == 'PRESS':
            self.orientation = 'LOCALY' if self.orientation == 'GLOBALY' else 'GLOBALY'
            infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'Z' and event.value == 'PRESS':
            self.orientation = 'LOCALZ' if self.orientation == 'GLOBALZ' else 'GLOBALZ'
            infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'W' and event.value == 'PRESS':
            orientations = ['GLOBALX', 'GLOBALY', 'GLOBALZ', 'LOCALX', 'LOCALY', 'LOCALZ', 'FACEB']
            self.orientation = orientations[(orientations.index(self.orientation) + 1) % len(orientations)]
            infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'G' and event.value == 'PRESS':
            if not self.state.startswith('TWEAK'):
                self.state = 'MOVE' if self.state != 'MOVE' else 'SET'
                infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'D' and event.value == 'PRESS':
            if not self.state.startswith('TWEAK'):
                modes = ['SLIDE', 'EXTEND', 'OFFSET']
                self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
                text = 'Slide' if self.mode == 'SLIDE' else 'Extend' if self.mode == 'EXTEND' else 'Offset'
                context.area.header_text_set(f'Project Loop,    mode: {text}')

                infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        elif event.type == 'TAB' and event.value == 'PRESS':
            if self.state == 'TWEAK':
                self.state = 'SET'
                infobar.draw(context, event, self.infobar_hotkeys, blank=True)

                self.polylines.clear()
                self.polylines_id.clear()

                if self.mode == 'SLIDE' or self.mode == 'OFFSET':
                    self.define_loop(context, self.distance)
                if self.mode == 'EXTEND' or self.mode == 'OFFSET':
                    self.define_tangents(context, self.distance)

            elif self.state != 'TWEAK_GRAB':

                self.state = 'TWEAK'
                self.remove_doubles()
                infobar.draw(context, event, self.infobar_hotkeys, blank=True)

            self.update_drawing(context, self.distance)
            context.area.tag_redraw()

        elif event.type in {'SPACE', 'RET'} and event.value == 'PRESS':
            if self.state == 'TWEAK':
                project_polyline_indexed(self.polylines, self.polylines_id)
                self.end(context)

                return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True

    def end(self, context):
        '''Cleanup and finish the operator'''

        self.bm = None
        self.edge = None
        self.edges = []
        self.edge_data = {}

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_bitangent, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_points, 'WINDOW')

        if self.debug:
            bpy.types.SpaceView3D.draw_handler_remove(self._debug_handle_verts_bitangents, 'WINDOW')
            bpy.types.SpaceView3D.draw_handler_remove(self._debug_handle_tangents, 'WINDOW')

        context.area.tag_redraw()

    def calculate_vertex_bitangents_pairs(self):
        '''Calculate the bitangents for the vertices'''

        vert_bitangents = []

        if len(self.edges) == 1:
            vert_bitangents = [(self.edges[0].verts[0], self.edge_data[self.edges[0]]['bitangent']), (self.edges[0].verts[1], self.edge_data[self.edges[0]]['bitangent'])]
            return vert_bitangents

        # Determine the vertex in the first edge that is not in the second edge
        unique_vertex = next((v for v in self.edges[0].verts if v not in self.edges[1].verts), None)

        if unique_vertex:
            linked_self_edges = [e for e in unique_vertex.link_edges if e in self.edges]
            avg_bitangent = sum((self.edge_data[e]['bitangent'] for e in linked_self_edges), Vector()).normalized()
            vert_bitangents.append((unique_vertex, avg_bitangent))

        # Now, append the other vertex from the first edge, ensuring it's not the unique_vertex
        for v in self.edges[0].verts:
            if v != unique_vertex:
                avg_bitangent = sum((self.edge_data[self.edges[0]]['bitangent'], self.edge_data[self.edges[1]]['bitangent']), Vector()).normalized()
                vert_bitangents.append((v, avg_bitangent))

        for edge in self.edges[1:]:
            for vert in edge.verts:
                # Check if vert is not in the list of vertices already processed
                if vert not in (v for v, _ in vert_bitangents):
                    linked_self_edges = [e for e in vert.link_edges if e in self.edges]
                    avg_bitangent = sum((self.edge_data[e]['bitangent'] for e in linked_self_edges), Vector()).normalized()
                    vert_bitangents.append((vert, avg_bitangent))

        return vert_bitangents

    def get_distance(self, context, mouse_pos, point, direction):
        '''Get the distance from the edge to the mouse position'''

        region = context.region
        rv3d = context.region_data

        mouse_pos_fixed = view3d.region_2d_to_nearest_point_on_line_3d(region, rv3d, mouse_pos, point, direction)

        if mouse_pos_fixed is None:
            return 0

        vector_to_mouse = point - mouse_pos_fixed
        on_positive_side = vector_to_mouse.dot(direction) <= 0  # True if mouse is on the positive self.side of bitangent

        # Adjust distance based on self.side
        distance = vector_to_mouse.length * (1 if on_positive_side else -1)

        return distance

    def update_edgedata_bitangents(self, context):
        '''Update the bitangents for the edges'''

        obj = context.edit_object

        normal_matrix = obj.matrix_world.inverted().transposed()

        for edge in self.edges:
            edge_data = self.edge_data[edge]
            edge_dir_world = normal_matrix @ edge_data['direction']

            selected_face = edge_data[self.side]
            face_normal_world = normal_matrix @ selected_face.normal

            bitangent = edge_dir_world.cross(face_normal_world).normalized()
            edge_data['bitangent'] = bitangent

    def define_loop(self, context, distance):
        '''Define the polyline loop'''

        obj = context.edit_object

        vertex_bitangents_pairs = self.calculate_vertex_bitangents_pairs()

        for vert, vert_bitangent in vertex_bitangents_pairs:
            vert_world_pos = obj.matrix_world @ vert.co
            bitangent = self.set_orientation(context, vert_bitangent)
            point_along_bitangent = vert_world_pos + bitangent * distance

            point_offsted = self.matrix_transform @ point_along_bitangent

            self.polylines.append(point_offsted)

        for i in range(1, len(vertex_bitangents_pairs)):
            self.polylines_id.append((i-1, i))

        if self.closed_loop:
            self.polylines_id.append((0, len(vertex_bitangents_pairs) - 1))

    def define_tangents(self, context, distance):
        '''Define the tangent edges for the vertices'''

        obj = context.edit_object
        vertex_bitangents_pairs = self.calculate_vertex_bitangents_pairs()

        if not self.closed_loop:
            vertex_bitangents_pairs = vertex_bitangents_pairs[1:-1]

        edge_start = len(self.polylines)
        self.base_verts.clear()

        for vert, vert_bitangent in vertex_bitangents_pairs:
            vert_world_pos = obj.matrix_world @ vert.co
            bitangent = self.set_orientation(context, vert_bitangent)
            point_along_bitangent = vert_world_pos + bitangent * distance

            vert_world_offsted = self.matrix_transform @ vert_world_pos
            point_offsted = self.matrix_transform @ point_along_bitangent

            self.polylines.append(vert_world_offsted)
            self.polylines.append(point_offsted)
            self.polylines_id.append((edge_start, edge_start + 1))
            self.base_verts.add(edge_start)

            edge_start += 2


    def set_orientation(self, context, bitangent):
        '''Set the orientation'''

        obj = context.edit_object
        orientation_vector = bitangent

        if self.orientation == 'GLOBALX':
            orientation_vector = Vector((1, 0, 0))
        elif self.orientation == 'GLOBALY':
            orientation_vector = Vector((0, 1, 0))
        elif self.orientation == 'GLOBALZ':
            orientation_vector = Vector((0, 0, 1))
        elif self.orientation == 'LOCALX':
            orientation_vector = obj.matrix_world.to_3x3() @ Vector((1, 0, 0))
        elif self.orientation == 'LOCALY':
            orientation_vector = obj.matrix_world.to_3x3() @ Vector((0, 1, 0))
        elif self.orientation == 'LOCALZ':
            orientation_vector = obj.matrix_world.to_3x3() @ Vector((0, 0, 1))

        return orientation_vector

    def update_drawing(self, context, distance):
        '''Update the drawing'''

        distance_sign = 1 if distance >= 0 else -1

        obj = context.edit_object

        edge_data = self.edge_data[self.edge]
        edge_midpoint_world = obj.matrix_world @ edge_data['mid']
        edge_bitangent = edge_data['bitangent']
        bitangent = self.set_orientation(context, edge_bitangent)

        guid = []
        guid.append((edge_midpoint_world, edge_midpoint_world + bitangent * distance))

        if self.debug:
            edges_along_bitangents = []

        for edge in self.edges:
            edge_data = self.edge_data[edge]
            edge_midpoint_world = obj.matrix_world @ edge_data['mid']
            edge_bitangent = edge_data['bitangent']
            bitangent = self.set_orientation(context, edge_bitangent)

            if self.debug:
                midpoint_along_bitangent = edge_midpoint_world + bitangent * 0.2 * distance_sign
                edges_along_bitangents.append((edge_midpoint_world, midpoint_along_bitangent))

        theme = addon.pref().theme.ops.mesh.project.loop
        color = theme.line

        self._callback_polyline.update_batch(self.polylines, color=color, flat=True, indices=self.polylines_id)
        color = self.get_color()
        self._callback_guid.update_batch(guid, color=color)


        if self.state.startswith('TWEAK'):
            self._callback_points.update_batch([self.polylines[i] for i in self.tweakable_id])

        else:
            self._callback_points.update_batch([])

        if self.debug:
            vertex_bitangents_pairs = self.calculate_vertex_bitangents_pairs()
            edges_along_vertex_bitangents = [(obj.matrix_world @ vert.co, obj.matrix_world @ vert.co + bitangent * 0.5 * distance_sign) for vert, bitangent in vertex_bitangents_pairs]
            self._debug_callback_verts_bitangents.update_batch(edges_along_vertex_bitangents, color=Vector((0.0, 1.0, 0.0, 1.0)))
            self._debug_callback_tangents.update_batch(edges_along_bitangents, color=Vector((1.0, 0.0, 0.0, 1.0)))

    def get_color(self):
        '''Get the color based on the orientation'''

        theme = addon.pref().theme.ops.mesh.project.loop

        color = theme.guid
        if self.orientation == 'GLOBALX':
            color = (1.0, 0.2, 0.322, 0.8)
        elif self.orientation == 'GLOBALY':
            color = (0.545, 0.863, 0.0, 0.8)
        elif self.orientation == 'GLOBALZ':
            color = (0.157, 0.565, 1.0, 0.8)
        elif self.orientation == 'LOCALX':
            color = (1.0, 0.2, 0.322, 0.8)
        elif self.orientation == 'LOCALY':
            color = (0.545, 0.863, 0.0, 0.8)
        elif self.orientation == 'LOCALZ':
            color = (0.157, 0.565, 1.0, 0.8)

        return color

    def setup_drawing(self, context, points=None):
        '''Setup the drawing'''

        theme = addon.pref().theme.ops.mesh.project.loop

        points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
        color = theme.line
        self._callback_polyline = DrawPolyline(points, width=1.8, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_polyline.draw, (context,), 'WINDOW', 'POST_VIEW')

        color = theme.guid
        self._callback_guid = DrawPolyline(points, width=1.2, color=color)
        self._handle_bitangent = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

        color = self.vert_color
        points = []
        self._callback_points = DrawPoints(points, size=self.vert_radius * 1.8, color=color)
        self._handle_points = bpy.types.SpaceView3D.draw_handler_add(self._callback_points.draw, (context,), 'WINDOW', 'POST_VIEW')

        if self.debug:
            self._debug_callback_verts_bitangents = DrawPolyline([], width=1.2, color=Vector((0.0, 1.0, 0.0, 1.0)))
            self._debug_handle_verts_bitangents = bpy.types.SpaceView3D.draw_handler_add(self._debug_callback_verts_bitangents.draw, (context,), 'WINDOW', 'POST_VIEW')
            self._debug_callback_tangents = DrawPolyline(points, width=1.2, color=Vector((1.0, 0.0, 0.0, 1.0)))
            self._debug_handle_tangents = bpy.types.SpaceView3D.draw_handler_add(self._debug_callback_tangents.draw, (context,), 'WINDOW', 'POST_VIEW')

    def remove_doubles(self):
        '''Remove double vertices form polylines'''
        bm = bmesh.new()

        for v in self.polylines:
            bm.verts.new(v)

        bm.verts.ensure_lookup_table()

        for i, j in self.polylines_id:
            v1 = bm.verts[i]
            v2 = bm.verts[j]
            bm.edges.new((v1, v2))

        base_verts = set(bm.verts[i] for i in range(len(bm.verts)) if i in self.base_verts)
        bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v not in base_verts], dist=0.0001)

        self.tweakable_id = []

        self.polylines.clear()
        self.polylines_id.clear()

        for i, v in enumerate(bm.verts):
            self.polylines.append(v.co.copy())
            if v not in base_verts:
                self.tweakable_id.append(i)

        for e in bm.edges:
            self.polylines_id.append((e.verts[0].index, e.verts[1].index))

        bm.free()

    def tweak_grab_prep(self, context, mouse_pos) -> bool:
        '''Prep states for grab. Returns false if grab has no selection to work with'''
        if not self.tweek_ids: return False

        self.tweak_back.clear()
        vec = Vector()

        for i in self.tweek_ids:
            vec += self.polylines[i]
            self.tweak_back.append(self.polylines[i])

        vec /= len(self.tweek_ids)
        self.input_plane_mat = context.space_data.region_3d.view_matrix.inverted()
        self.input_plane_mat.translation = vec
        self.start_input3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, mouse_pos, self.input_plane_mat.translation)

        return True


    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''

        factor = 8
        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust')
        row.separator(factor=factor)

        if not self.state.startswith('TWEAK'):
            row.label(text='', icon='MOUSE_LMB')
            row.label(text='Confirm')
            row.separator(factor=factor)

        else:
            row.label(text='/', icon='EVENT_SPACEKEY')
            row.label(text='', icon='EVENT_RETURN')
            row.label(text='Confirm')
            row.separator(factor=factor)

        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=factor)

        if not self.state.startswith('TWEAK'):
            row.label(text='', icon='EVENT_D')
            row.label(text='Change Mode')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_F')
            if self.orientation == 'FACEB':
                row.label(text='Flip Direction')
            else:
                row.label(text='Face')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_X')
            if self.orientation == 'GLOBALX':
                row.label(text='Local X')
            else:
                row.label(text='Global X')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_Y')
            if self.orientation == 'GLOBALY':
                row.label(text='Local Y')
            else:
                row.label(text='Global Y')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_Z')
            if self.orientation == 'GLOBALZ':
                row.label(text='Local Z')
            else:
                row.label(text='Global Z')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_G')
            if self.state == 'MOVE':
                row.label(text='Set')
            else:
                row.label(text='Move')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_W')
            row.label(text='Cycle Orientation')
            row.separator(factor=factor)
            row.label(text='', icon='EVENT_TAB')
            row.label(text='Tweak')

        else:
            row.label(text='', icon='EVENT_TAB')
            row.label(text='Cancel Tweak')


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Loop Line", description="Line color", default=(0.5, 0.4, 0.8, 1.0), subtype='COLOR', size=4, min=0.0, max=1.0)
        guid: bpy.props.FloatVectorProperty(name="Loop Guide", description="Guide color", default=(0.0, 0.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        vert_color: bpy.props.FloatVectorProperty(name="Vertex", description="Vertex color", default=(0.3, 0.6, 0.3, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        vert_radius: bpy.props.FloatProperty(name="Vertex Radius", description="Radius of vertex in pixels", default=8, min=1, step=100)

types_classes = (
    types.theme,
)
