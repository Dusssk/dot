import bpy
import bmesh

from mathutils import Vector

from ..draw.face import DrawFace
from .utils import infobar
from ...utils.view3d import region_2d_to_nearest_point_on_line_3d


class NSOLVE_OT_SmartLoopCut(bpy.types.Operator):
    bl_idname = 'nsolve.smart_loop_cut'
    bl_label = 'Smart Loop Cut'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = '''Create Loop Cut along a given edge'''

    stored_select_mode: tuple

    bms: dict = {}
    geoms: dict = {}

    _callback_faceloop: DrawFace
    _handle_faceloop: int
    _callback_ngonloop: DrawFace
    _handle_ngonloop: int

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        col = layout.column()

    def invoke(self, context, event):

        context.edit_object.select_set(True)
        selected_objects = context.selected_objects

        self.stored_select_mode = context.tool_settings.mesh_select_mode[:]
        context.tool_settings.mesh_select_mode = (False, True, False)

        self.bms = {}

        bpy.ops.mesh.select_all(action='DESELECT')

        for obj in selected_objects:
            if obj.type == 'MESH':

                # Operate on this object
                bm = bmesh.from_edit_mesh(obj.data)
                geom = [v for v in bm.verts if not v.hide] + [e for e in bm.edges if not e.hide] + [f for f in bm.faces if not f.hide]

                # Store bmesh and selections
                self.bms[obj] = bm
                self.geoms[obj] = geom

        points = [(Vector((0, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 0)), Vector((0, 0, 0)))]
        color = Vector((1.0, 1.0, 0.3, 0.2))
        self._callback_faceloop = DrawFace(points, color)
        self._handle_faceloop = bpy.types.SpaceView3D.draw_handler_add(self._callback_faceloop.draw, (context,), 'WINDOW', 'POST_VIEW')
        ngon_color = Vector((1.0, 0.0, 0.0, 0.2))  # Example: red color for ngons
        self._callback_ngonloop = DrawFace([], ngon_color)  # Initialize with empty data
        self._handle_ngonloop = bpy.types.SpaceView3D.draw_handler_add(self._callback_ngonloop.draw, (context,), 'WINDOW', 'POST_VIEW')

        infobar.draw(context, event, self.infobar_hotkeys_detect, blank=True)
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Smart Loop Cut", position=(50, 2))
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            edge, edit_object, _bm = self.detect_edge(context, event)
            if edge:
                _, face_loop, ngon_loop = traverse_edge_loop(edge)

                # Update face and ngon drawing
                face_points = [[edit_object.matrix_world @ v.co for v in face.verts] for face in face_loop]
                self._callback_faceloop.update_batch(face_points)

                ngon_points = [[edit_object.matrix_world @ v.co for v in ngon.verts] for ngon in ngon_loop]
                self._callback_ngonloop.update_batch(ngon_points)

            else:
                self._callback_faceloop.update_batch([])
                self._callback_ngonloop.update_batch([])

        if event.type in {'RIGHTMOUSE', 'ESC'}:

            selected_objects = context.selected_objects

            for obj in selected_objects:
                bmesh.update_edit_mesh(obj.data)

            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def end(self, context):
        '''Clean up.'''

        infobar.remove(context)
        context.window.cursor_set('CROSSHAIR')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_faceloop, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_ngonloop, 'WINDOW')

    def execute(self, context):
        '''Execute the bisect operation.'''

        loop_cut_active_edge(context)

        return {'FINISHED'}

    def detect_edge(self, context, event):
        '''Detect the edge under the mouse cursor.'''

        context.tool_settings.mesh_select_mode = (False, True, False)
        mouse = (event.mouse_region_x, event.mouse_region_y)
        bpy.ops.view3d.select(location=(mouse[0], mouse[1]), extend=True)

        edit_object = context.edit_object
        bm = self.bms[edit_object]

        active_edge = bm.select_history.active
        if isinstance(active_edge, bmesh.types.BMEdge):
            if active_edge and active_edge in bm.edges:
                active_edge.select = False
                bm.select_history.remove(active_edge)
                context.tool_settings.mesh_select_mode = self.stored_select_mode
                return active_edge, edit_object, bm

        context.tool_settings.mesh_select_mode = self.stored_select_mode
        return None, None, None

    def infobar_hotkeys_detect(self, layout, _context, _event):
        '''Draw the infobar for the "DETECT" state.'''

        row = layout.row()
        row.label(text='Select an edge to loop cut along it, hide the mesh to cut ony chosen geometry.')

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


def subdivide_and_connect_edges(bm, edge_list):
    """Subdivide the given edges and connect the resulting vertices."""

    if not edge_list:
        return

    # Subdivide edges
    bmesh.ops.subdivide_edges(bm, edges=edge_list, cuts=1, use_grid_fill=True)


def traverse_edge_loop(start_edge):
    def is_quad(face):
        """Check if the face is a quad."""
        return len(face.edges) == 4

    def find_opposite_edge_in_quad(current_edge, current_face):
        """Find the opposite edge in the given quad face."""
        if is_quad(current_face):
            for e in current_face.edges:
                # The opposite edge does not share any vertices with the current edge
                if e != current_edge and not any(v in e.verts for v in current_edge.verts):
                    return e
        return None

    def traverse_from_face(start_edge, start_face):
        """Traverse from the given face."""
        edge_loop = []
        face_loop = [start_face]  # Include the starting face
        ngon_loop = []

        current_edge = start_edge
        current_face = start_face

        while True:
            if len(current_face.edges) > 4:  # Ngons are treated differently
                ngon_loop.append(current_face)
                break

            next_edge = find_opposite_edge_in_quad(current_edge, current_face)
            if not next_edge or next_edge == start_edge:
                break  # Break if no next edge or loop closes

            # Find the next face for traversal
            next_faces = [f for f in next_edge.link_faces if f != current_face]
            if not next_faces:  # Break if no next face
                break

            next_face = next_faces[0]

            # Update lists and continue traversal
            edge_loop.append(next_edge)
            if is_quad(next_face):
                face_loop.append(next_face)

            current_edge = next_edge
            current_face = next_face

        return edge_loop, face_loop, ngon_loop

    edge_loops, face_loops, ngon_loops = [], [], []

    # Traverse from both faces of the starting edge, if available
    for face in start_edge.link_faces[:2]:  # Limit to the first two faces (if exist)
        e_loop, f_loop, n_loop = traverse_from_face(start_edge, face)
        edge_loops.extend(e_loop)
        face_loops.extend(f_loop)
        ngon_loops.extend(n_loop)

    # Combine unique faces and edges, avoiding duplicates
    combined_edge_loop = list(dict.fromkeys(edge_loops))
    combined_face_loop = list(dict.fromkeys(face_loops))
    combined_ngon_loop = list(dict.fromkeys(ngon_loops))

    return combined_edge_loop, combined_face_loop, combined_ngon_loop


def loop_cut_active_edge(context):
    """Create a loop cut along the active edge in the mesh."""

    obj = context.edit_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    # Ensure we have an active edge
    active_edge = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMEdge) else None
    if not active_edge:
        print("No active edge selected.")
        return

    # Traverse the edge loop starting from the active edge
    edge_loop, _, _ = traverse_edge_loop(active_edge)

    # Subdivide and connect edges in the loop
    if edge_loop:
        subdivide_and_connect_edges(bm, edge_loop)
        bmesh.update_edit_mesh(me, loop_triangles=True, destructive=True)
    else:
        print("Failed to create a complete loop.")
