import bpy
import bmesh

from mathutils import Vector

from ...draw.polyline import DrawPolyline
from ..utils import infobar
from ....utils import addon, view3d, scene
from ....utils.nmesh import Nmesh

from ... import analytics


class NSOLVE_OT_HardLoopCut(bpy.types.Operator):
    bl_idname = "nsolve.hard_loop_cut"
    bl_label = "Hard Loop Cut"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = f"{bl_label}\n\nCreate Loop Cut along a given edge"

    state: str = 'DETECT'
    orientation: str = 'NORMAL'

    bms: dict = {}
    nms: dict = {}
    geoms: dict = {}
    stored_select_mode: tuple
    edge_points: list = []

    move_init: Vector = None
    move: bpy.props.FloatProperty(name="Move", description="Offset from selected edge center", default=0.0, step=1, precision=4, subtype='DISTANCE')

    plane_co: Vector = Vector((0, 0, 0))
    plane_no: bpy.props.FloatVectorProperty(name="Normal", description="Move vector", default=(0, 0, 0), min=-1, max=1, subtype='XYZ')
    plane_co_init: Vector = Vector((0, 0, 0))
    plane_no_init: Vector = Vector((0, 0, 0))

    merge_dist: bpy.props.FloatProperty(name='Merge Distance', description="Distance for merging doubles into loop", default=0.001, min=0.0)
    segments: bpy.props.IntProperty(name="Segments", description="Number of cuts", default=1, min=1, max=12)
    spacing: float = 0.0

    release_confirm: bpy.props.BoolProperty(name="Release Confirm", default=True)
    confirm_value: str = 'PRESS'

    _callback_line: DrawPolyline
    _handle_line: int
    _callback_guid: DrawPolyline
    _handle_guid: int

    orientations = [
        ('GLOBAL X', Vector((1, 0, 0))),
        ('LOCAL X', Vector((1, 0, 0))),
        ('GLOBAL Y', Vector((0, 1, 0))),
        ('LOCAL Y', Vector((0, 1, 0))),
        ('GLOBAL Z', Vector((0, 0, 1))),
        ('LOCAL Z', Vector((0, 0, 1))),
        ('NORMAL', None)
    ]
    current_orientation = 6
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        col = layout.column()
        col.prop(self, 'move')
        col.prop(self, 'plane_no')
        col.prop(self, 'merge_dist')
        col.prop(self, 'segments')

    def invoke(self, context, event):

        context.edit_object.select_set(True)
        selected_objects = context.selected_objects

        # self.confirm_value = 'PRESS' if self.release_confirm else 'RELEASE'

        self.move = 0.0
        self.bms = {}
        self.nms = {}

        bpy.ops.mesh.select_all(action='DESELECT')

        for obj in selected_objects:
            if obj.type == 'MESH':

                # Operate on this object
                bm = bmesh.from_edit_mesh(obj.data)
                geom = [v for v in bm.verts if not v.hide] + [e for e in bm.edges if not e.hide] + [f for f in bm.faces if not f.hide]

                # Store bmesh and selections
                self.bms[obj] = bm
                self.geoms[obj] = geom
                self.nms[obj] = Nmesh.from_bmesh(context, bm, obj)

        points = [(Vector((0, 0, 0)), Vector((0, 0, 0)))]

        theme = addon.pref().theme.ops.mesh.hard_loop_cut
        color = theme.line
        self._callback_line = DrawPolyline(points, width=1.0, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')
        color = theme.guid
        self._callback_guid = DrawPolyline(points, width=1.2, color=color)
        self._handle_guid = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

        infobar.draw(context, event, self.infobar_hotkeys_detect, blank=True)
        context.area.header_text_set(f'Loop Rake: {self.move:.4f} | Orientation: {self.orientations[self.current_orientation][0]}')
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Hard Loop Cut|orientation {self.orientations[self.current_orientation][0]}", position=(50, 2), color=(0.8, 0.7, 0.26, 0.8))
        analytics.stats("nSuite: Hard Loop Cut")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            if self.state == 'DETECT':
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                scene.set_active_object(context, mouse_pos)

                edge, edit_object, bm = self.detect_edge(context, event)
                if edge:

                    self.edge_points = [(edit_object.matrix_world @ edge.verts[0].co, edit_object.matrix_world @ edge.verts[1].co)]

                    self.plane_co_init = (edge.verts[0].co + edge.verts[1].co) / 2
                    self.plane_no_init = (edge.verts[1].co - edge.verts[0].co).normalized()

                    self.plane_co = self.plane_co_init
                    if self.orientation == 'NORMAL':
                        self.plane_no = self.plane_no_init

                    self.update(context, edit_object, bm)

                else:
                    theme = addon.pref().theme.ops.mesh.hard_loop_cut
                    color = theme.line
                    self._callback_line.update_batch([Vector((0, 0, 0)), Vector((0, 0, 0))], color=color)

            elif self.state == 'MOVE':

                edit_object = context.edit_object
                bm = self.bms[edit_object]

                # Transform self.plane_co_init and self.plane_no to global space
                global_plane_co_init = edit_object.matrix_world @ self.plane_co_init

                plane_no = self.plane_no

                if self.orientation == 'NORMAL':
                    plane_no = (edit_object.matrix_world.to_3x3() @ self.plane_no).normalized()

                # Now use these global vectors for calculating the closest point on the line
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                region = context.region
                rv3d = context.region_data
                closest_point_on_line = view3d.region_2d_to_nearest_point_on_line_3d(region, rv3d, mouse_pos, global_plane_co_init, plane_no)

                if closest_point_on_line:
                    # Convert the closest point back to local space before using it
                    local_closest_point = edit_object.matrix_world.inverted() @ closest_point_on_line

                    if self.move_init is None:
                        self.move_init = self.plane_co_init - local_closest_point

                    adjusted_closest_point = local_closest_point + self.move_init
                    self.plane_co = adjusted_closest_point

                    # Determine the direction to adjust the move
                    self.calculate_offset_from_plane_co()
                    context.area.header_text_set(f'Loop Rake: {self.move:.4f} | Orientation: {self.orientations[self.current_orientation][0]}')

                self.update(context, edit_object, bm)

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            if self.state == 'MOVE':

                self.cut(context)
                self.end(context)

                return {'FINISHED'}

            elif self.state == 'DETECT':
                if self.edge_points:

                    theme = addon.pref().theme.ops.mesh.hard_loop_cut
                    color = theme.guid
                    self._callback_guid.update_batch(self.edge_points, color=color)
                    self.state = 'MOVE'

                    infobar.draw(context, event, self.infobar_hotkeys_move, blank=True)

                else:
                    self.end(context)
                    return {'CANCELLED'}

        # wheel brackets aor arrows
        elif event.type == 'WHEELUPMOUSE' or event.type == 'NUMPAD_PLUS' or event.type == 'RIGHT_BRACKET' or event.type == 'UP_ARROW':
            if event.value == 'PRESS':
                if self.segments < 12:
                    self.segments += 1
                    self.update(context, context.edit_object, self.bms[context.edit_object])
                    context.area.header_text_set(f'Segments: {self.segments} | Loop Rake: {self.move:.4f} | Orientation: {self.orientations[self.current_orientation][0]}')

        elif event.type == 'WHEELDOWNMOUSE' or event.type == 'NUMPAD_MINUS' or event.type == 'LEFT_BRACKET' or event.type == 'DOWN_ARROW':
            if event.value == 'PRESS':
                if self.segments > 1:
                    self.segments -= 1
                    self.update(context, context.edit_object, self.bms[context.edit_object])
                    context.area.header_text_set(f'Segments: {self.segments} | Loop Rake: {self.move:.4f} | Orientation: {self.orientations[self.current_orientation][0]}')

        elif event.type in {'X', 'Y', 'Z', 'N', 'W'} and event.value == 'PRESS':
            edit_object = context.edit_object
            bm = self.bms[edit_object]

            if event.type == 'Z':
                if self.orientation == 'GLOBAL':
                    self.orientation = 'LOCAL'
                    self.plane_no = Vector((0, 0, 1))
                    self.current_orientation = 5
                else:
                    self.orientation = 'GLOBAL'
                    plane_no = edit_object.matrix_world.transposed() @ Vector((0, 0, 1))
                    self.plane_no = plane_no.normalized()  # self.plane_no is capped, so normalize before setting!
                    self.current_orientation = 4

            elif event.type == 'X':
                if self.orientation == 'GLOBAL':
                    self.orientation = 'LOCAL'
                    self.plane_no = Vector((1, 0, 0))
                    self.current_orientation = 1
                else:
                    self.orientation = 'GLOBAL'
                    plane_no = edit_object.matrix_world.transposed() @ Vector((1, 0, 0))
                    self.plane_no = plane_no.normalized()
                    self.current_orientation = 0

            elif event.type == 'Y':
                if self.orientation == 'GLOBAL':
                    self.orientation = 'LOCAL'
                    plane_no = Vector((0, 1, 0))
                    self.current_orientation = 3
                else:
                    self.orientation = 'GLOBAL'
                    plane_no = edit_object.matrix_world.transposed() @ Vector((0, 1, 0))
                    self.plane_no = plane_no.normalized()
                    self.current_orientation = 2

            elif event.type == 'N':
                self.orientation = 'NORMAL'
                self.plane_no = self.plane_no_init
                self.current_orientation = 6

            elif event.type == 'W':
                self.current_orientation = (self.current_orientation + 1) % len(self.orientations)
                self.orientation, plane_vector = self.orientations[self.current_orientation]

                if self.orientation.startswith('GLOBAL'):
                    plane_no = edit_object.matrix_world.transposed() @ plane_vector
                    self.plane_no = plane_no.normalized()
                elif self.orientation.startswith('LOCAL'):
                    self.plane_no = plane_vector
                elif self.orientation == 'NORMAL':
                    self.plane_no = self.plane_no_init

            context.area.header_text_set(f'Loop Rake: {self.move:.4f} | Orientation: {self.orientations[self.current_orientation][0]}')
            self.update(context, edit_object, bm)

        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':

            if self.state == 'MOVE':

                self.move = 0.0
                self.plane_co = self.plane_co_init

                self.cut(context)
                self.end(context)

                return {'FINISHED'}

            elif self.state == 'DETECT':

                selected_objects = context.selected_objects

                for obj in selected_objects:
                    bmesh.update_edit_mesh(obj.data)

                self.end(context)
                return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def update(self, context, edit_object, bm):
        '''Update the bisect operation based on the current state.'''

        # Create a temporary copy of the bmesh for the update process
        bm_temp = bm.copy()

        # Calculate edge length from the initial edge points
        edge_length = (self.edge_points[0][1] - self.edge_points[0][0]).length

        # Calculate the spacing based on edge length and segments
        self.spacing = edge_length / (self.segments + 1)

        # Use the locked plane position
        initial_plane_co = self.plane_co.copy()
        all_results = []

        # Calculate the center offset for symmetrical distribution
        mid_index = (self.segments - 1) / 2

        for i in range(self.segments):
            # Calculate offset, negative for segments before the middle, positive for after
            offset = (i - mid_index) * self.spacing
            current_plane_co = initial_plane_co + (self.plane_no * offset)

            # Update the list of geometry to reflect the current state of the temporary bmesh
            geom_temp = [v for v in bm_temp.verts if not v.hide] + [e for e in bm_temp.edges if not e.hide] + [f for f in bm_temp.faces if not f.hide]

            # Perform the bisect operation on the temporary bmesh
            result = self.bisect(context, current_plane_co, self.plane_no, bm_temp, geom_temp)
            all_results.append(result)

        # Update the visual representation with all results
        self.update_bisect_callback(edit_object, all_results)

        # Free the temporary bmesh to avoid memory leaks
        bm_temp.free()

        context.area.tag_redraw()

    def cut(self, context):
        '''Execute the bisect operation.'''
        edit_object = context.edit_object
        bm = self.bms[edit_object]

        # Calculate edge length from the initial edge points
        edge_length = (self.edge_points[0][1] - self.edge_points[0][0]).length

        # Calculate the spacing based on edge length and segments
        self.spacing = edge_length / (self.segments + 1)

        # Use the locked plane position
        initial_plane_co = self.plane_co.copy()
        all_results = []

        # Calculate the center offset for symmetrical distribution
        mid_index = (self.segments - 1) / 2

        for i in range(self.segments):
            # Calculate offset, negative for segments before the middle, positive for after
            offset = (i - mid_index) * self.spacing
            current_plane_co = initial_plane_co + (self.plane_no * offset)

            # Update the geometry list to reflect the current state of the bmesh
            geom = [v for v in bm.verts if not v.hide] + [e for e in bm.edges if not e.hide] + [f for f in bm.faces if not f.hide]

            # Perform the bisect operation using the calculated plane position
            result = self.bisect(context, current_plane_co, self.plane_no, bm, geom)
            all_results.append(result)

            # Select the newly created edges
            for edge in result['geom_cut']:
                if isinstance(edge, bmesh.types.BMEdge) and edge.is_valid:
                    edge.select = True

            # Merge vertices if necessary
            if self.merge_dist:
                cut_verts = [v for v in result['geom_cut'] if isinstance(v, bmesh.types.BMVert)]
                neighbor = set()

                for v in cut_verts:
                    for e in v.link_edges:
                        neighbor.update(e.verts)

                doubles = bmesh.ops.find_doubles(bm, verts=list(neighbor), keep_verts=cut_verts, dist=self.merge_dist)['targetmap']
                bmesh.ops.weld_verts(bm, targetmap=doubles)

            # After each bisect, update the bmesh to ensure the next bisect works on the updated geometry
            bmesh.update_edit_mesh(edit_object.data, destructive=True)

        bm.select_flush(True)
        bmesh.update_edit_mesh(edit_object.data)

        # Update the drawing to reflect all cuts
        self.update_bisect_callback(edit_object, all_results)

    def update_bisect_callback(self, edit_object, results):
        '''Update the drawing callback with new points.'''
        
        if not isinstance(results, list):
            results = [results]  # Ensure results are in a list

        edge_points = []
        for result in results:
            # Ensure the result is valid and contains the expected data
            if isinstance(result, dict) and 'geom_cut' in result:
                for e in result['geom_cut']:
                    # Check if the BMEdge is still valid
                    if isinstance(e, bmesh.types.BMEdge) and e.is_valid:
                        edge_points.append((edit_object.matrix_world @ e.verts[0].co.copy(), edit_object.matrix_world @ e.verts[1].co.copy()))
            else:
                print("Unexpected result format:", result)

        if edge_points:
            theme = addon.pref().theme.ops.mesh.hard_loop_cut
            color = theme.line
            self._callback_line.update_batch(edge_points, color=color)

    def calculate_offset_from_plane_co(self):
        '''Calculate the move based on the current plane_co and the initial plane_co.'''

        difference_vector = self.plane_co - self.plane_co_init

        # The projection formula is: proj_v_on_u = (v . u / u . u) * u
        # But since plane_no should be a unit vector (normalized), u . u = 1, simplifying the formula
        projection_length = difference_vector.dot(self.plane_no)
        self.move = projection_length

    def adjust_plane_co(self, plane_no):
        '''Adjust the plane_co based on the move.'''

        movement_vector = plane_no * self.move
        self.plane_co = self.plane_co_init + movement_vector

    def execute(self, context):
        '''Execute the bisect operation.'''

        bpy.ops.mesh.select_all(action='DESELECT')

        edit_object = context.edit_object
        bm = bmesh.from_edit_mesh(edit_object.data)

        # Detect the edge under the cursor or use the stored edge
        if not self.edge_points:
            edge, _, bm = self.detect_edge(context, None)
            if edge:
                self.edge_points = [(edit_object.matrix_world @ edge.verts[0].co, edit_object.matrix_world @ edge.verts[1].co)]
                self.plane_co_init = (edge.verts[0].co + edge.verts[1].co) / 2
                self.plane_no_init = (edge.verts[1].co - edge.verts[0].co).normalized()
                self.plane_co = self.plane_co_init
                if self.orientation == 'NORMAL':
                    self.plane_no = self.plane_no_init

        # Calculate edge length and set spacing
        edge_length = (self.edge_points[0][1] - self.edge_points[0][0]).length
        self.spacing = edge_length / (self.segments + 1)

        # Adjust the initial plane position based on the self.move offset
        self.plane_co = self.plane_co_init + (self.plane_no * self.move)

        # Use the locked plane position
        initial_plane_co = self.plane_co.copy()
        all_results = []

        # Calculate the center offset for symmetrical distribution
        mid_index = (self.segments - 1) / 2

        for i in range(self.segments):
            # Calculate offset, negative for segments before the middle, positive for after
            offset = (i - mid_index) * self.spacing
            current_plane_co = initial_plane_co + (self.plane_no * offset)

            # Update the geometry list to reflect the current state of the bmesh
            geom = [v for v in bm.verts if not v.hide] + [e for e in bm.edges if not e.hide] + [f for f in bm.faces if not f.hide]

            # Perform the bisect operation using the calculated plane position
            result = self.bisect(context, current_plane_co, self.plane_no, bm, geom)
            all_results.append(result)

            # Select the newly created edges
            for edge in result['geom_cut']:
                if isinstance(edge, bmesh.types.BMEdge):
                    edge.select = True

            # Merge vertices if necessary
            if self.merge_dist:
                cut_verts = [v for v in result['geom_cut'] if isinstance(v, bmesh.types.BMVert)]
                neighbor = set()

                for v in cut_verts:
                    for e in v.link_edges:
                        neighbor.update(e.verts)

                doubles = bmesh.ops.find_doubles(bm, verts=list(neighbor), keep_verts=cut_verts, dist=self.merge_dist)['targetmap']
                bmesh.ops.weld_verts(bm, targetmap=doubles)

            # After each bisect, update the bmesh to ensure the next bisect works on the updated geometry
            bmesh.update_edit_mesh(edit_object.data, destructive=True)

        bm.select_flush(True)
        bmesh.update_edit_mesh(edit_object.data)

        # Update the drawing to reflect all cuts
        self.update_bisect_callback(edit_object, all_results)

        return {'FINISHED'}

    def end(self, context):
        '''Clean up.'''

        self.bms.clear()
        self.geoms.clear()
        self.nms.clear()

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_guid, 'WINDOW')

        context.area.tag_redraw()

    def detect_edge(self, context, event):
        '''Detect the edge under the mouse cursor.'''

        edit_object = context.edit_object
        bm = self.bms[edit_object]

        self.nms[edit_object].detect_element(event, mode=(False, True, False))
        element = self.nms[edit_object].element

        if element[0]:
            if isinstance(element[1], bmesh.types.BMEdge):
                return element[1], edit_object, bm

        return None, None, None

    def bisect(self, context, plane_co, plane_no, bm, geom):
        '''Cut the mesh using the bisect_plane.'''
        result = bmesh.ops.bisect_plane(
            bm,
            geom=geom,
            plane_co=plane_co,
            plane_no=plane_no,
            clear_outer=False,
            clear_inner=False
        )

        if 'geom_cut' not in result:
            raise ValueError("Bisect operation did not return expected 'geom_cut' data")

        bmesh.update_edit_mesh(context.edit_object.data, destructive=True)

        return result

    def infobar_hotkeys_detect(self, layout, _context, _event):
        '''Draw the infobar for the "DETECT" state.'''

        row = layout.row()
        row.label(text='Select an edge to loop cut along it, hide the mesh to cut only chosen geometry.')

        row = layout.row()
        row.label(text='Hotkeys: X, Y, Z, N, W')

    def infobar_hotkeys_move(self, layout, _context, _event):
        '''Draw the infobar for the "MOVE" state.'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Adjust')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=8.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_X')
        row.label(text='X Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_Y')
        row.label(text='Y Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_Z')
        row.label(text='Z Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_N')
        row.label(text='Normal Axis')
        row.separator(factor=8.0)
        row.label(text='', icon='EVENT_W')
        row.label(text='Cycle Axis')
        row.separator(factor=8.0)


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Hard Loop Cut Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 0.9), min=0.0, max=1.0)
        guid: bpy.props.FloatVectorProperty(name="Hard Loop Cut guid", description="Color of the guid", size=4, subtype='COLOR', default=(1.0, 1.0, 0.3, 0.5), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
