import bpy
import bmesh
from mathutils import Vector
from ...draw.polyline import DrawPolyline
from ...draw.circle import DrawCircle
from ..utils import infobar
from ....utils import addon, view3d, scene
from ....utils.nmesh import Nmesh
from ... import analytics


class NSOLVE_OT_JoinVerts(bpy.types.Operator):
    bl_idname = "nsolve.join_verts"
    bl_label = "Join Vertices Under Mouse"
    bl_description = f"{bl_label}\n\nConnect selected vertex with the one under the cursor"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    multi: bpy.props.BoolProperty(
        name="multi",
        description="Connect multiple vertices",
        default=False
    )

    snap_mode: bpy.props.BoolVectorProperty(name="Snap Mode", description="Snap to different points on the element", size=6, default=(True, False, False, False, False, False))

    nmesh: Nmesh = None
    element: tuple = None
    bbox: Vector = None

    bm: bmesh.types.BMesh = None
    verts: list = []

    snap: str = 'NONE'

    edge_mid: Vector = None
    edge_perp: Vector = None
    face_mid: Vector = None

    cut_through = False

    prev_select_mode: tuple

    _callback_line: DrawPolyline = None
    _handle_line: int = None
    _callback_init_circle: DrawCircle = None
    _handle_init_circle: int = None
    _callback_circle: DrawCircle = None
    _handle_circle: int = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):

        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        scene.set_active_object(context, mouse_pos)

        obj = context.edit_object
        obj.update_from_editmode()
        self.bbox = bbox_center(obj)
        self.bm = bmesh.from_edit_mesh(obj.data)
        self.nmesh = Nmesh.from_bmesh(context, self.bm, obj)
        self.nmesh.detect_element(event, mode=(True, False, False))
        self.element = self.nmesh.element

        if self.multi:
            self.verts = [v for v in self.bm.verts if v.select]
        else:
            if self.element[0] == 'VERT':
                self.verts = [self.element[1]]
            else:
                self.verts = []

        if len(self.verts) < 1:
            bpy.ops.view3d.select_box('INVOKE_DEFAULT')
            return {'FINISHED'}

        self.setup_drawing(context, self.verts)

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set('Join Vertices')
        context.window.cursor_set('SCROLL_XY')

        context.window_manager.modal_handler_add(self)
        analytics.stats("nSolve: Join")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        draw_update = self.cut_through != event.alt
        self.cut_through = event.alt

        def no_snap():
            self.snap = 'NONE'
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            region = context.region
            rv3d = context.region_data
            depth_vec = context.edit_object.matrix_world @ self.verts[0].co
            vert = view3d.region_2d_to_location_3d(region, rv3d, mouse_pos, depth_vec)
            self.update_drawing(context, False, self.verts, vert)

        if event.type == 'MOUSEMOVE':
            obj = context.edit_object

            mode = (self.snap_mode[0], self.snap_mode[1] or self.snap_mode[3] or self.snap_mode[4], self.snap_mode[2] or self.snap_mode[5])
            self.nmesh.detect_element(event, mode=mode)
            self.element = self.nmesh.element

            if self.element[0]:
                if self.element[0] == 'VERT' and self.snap_mode[0]:
                    self.snap = 'VERT'
                    self.update_drawing(context, True, self.verts, obj.matrix_world @ self.element[1].co)
                elif self.element[0] == 'EDGE' and (self.snap_mode[1] or self.snap_mode[3] or self.snap_mode[4]):
                    self.edge_mid = (self.element[1].verts[0].co + self.element[1].verts[1].co) / 2
                    self.edge_perp = self.perpendicular_point(self.verts[0].co, self.element[1].verts[0].co, self.element[1].verts[1].co)
                    point_on_edge = self.element[2]

                    edge_mid_to_region_2d = view3d.location_3d_to_region_2d(context.region, context.region_data, obj.matrix_world @ self.edge_mid, default=obj.matrix_world @ self.bbox)
                    edge_perp_to_region_2d = view3d.location_3d_to_region_2d(context.region, context.region_data, obj.matrix_world @ self.edge_perp, default=obj.matrix_world @ self.bbox)
                    point_on_edge_to_region_2d = view3d.location_3d_to_region_2d(context.region, context.region_data, obj.matrix_world @ point_on_edge, default=obj.matrix_world @ self.bbox)

                    distance_to_mid = (edge_mid_to_region_2d - point_on_edge_to_region_2d).length
                    distance_to_perp = (edge_perp_to_region_2d - point_on_edge_to_region_2d).length

                    if self.snap_mode[3] and distance_to_mid < 30:
                        self.snap = 'EDGE_MID'
                        point_on_edge = self.edge_mid
                    elif self.snap_mode[4] and distance_to_perp < 30:
                        self.snap = 'EDGE_PERP'
                        point_on_edge = self.edge_perp
                    else:
                        self.snap = 'EDGE'

                    self.update_drawing(context, True, self.verts, obj.matrix_world @ point_on_edge)
                elif self.element[0] == 'FACE' and (self.snap_mode[2] or self.snap_mode[5]):
                    self.face_mid = self.element[1].calc_center_median()
                    point_on_face = self.element[2]

                    face_mid_to_region_2d = view3d.location_3d_to_region_2d(context.region, context.region_data, self.face_mid, default=obj.matrix_world @ self.bbox)
                    point_on_face_to_region_2d = view3d.location_3d_to_region_2d(context.region, context.region_data, point_on_face, default=obj.matrix_world @ self.bbox)

                    distance_to_mid = (face_mid_to_region_2d - point_on_face_to_region_2d).length

                    if self.snap_mode[5] and distance_to_mid < 30:
                        self.snap = 'FACE_MID'
                        point_on_face = self.face_mid
                    else:
                        self.snap = 'FACE'

                    self.update_drawing(context, True, self.verts, obj.matrix_world @ point_on_face)
                else:
                    no_snap()
            else:
                no_snap()

            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            obj = context.edit_object
            if self.verts:
                if self.snap == 'VERT':
                    self.connect_vertices(context, self.bm, self.verts, self.element[1])
                elif self.snap == 'EDGE':
                    self.connect_vertices_to_edge(context, self.bm, self.verts, self.element[1], self.element[2])
                elif self.snap == 'FACE':
                    self.connect_vertices_to_face(context, self.bm, self.verts, self.element[1], self.element[2])
                elif self.snap == 'EDGE_MID':
                    self.connect_vertices_to_edge(context, self.bm, self.verts, self.element[1], self.edge_mid)
                elif self.snap == 'EDGE_PERP':
                    self.connect_vertices_to_edge(context, self.bm, self.verts, self.element[1], self.edge_perp)
                elif self.snap == 'FACE_MID':
                    self.connect_vertices_to_face(context, self.bm, self.verts, self.element[1], self.face_mid)
                else:
                    self.line_knife(context, event)

            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.bm.select_flush_mode()
            self.end(context)
            return {'CANCELLED'}

        elif draw_update and self.snap =='NONE':
            no_snap()
            context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def line_knife(self, context, event):
        v = self.verts[0]
        c1 = context.edit_object.matrix_world @ v.co
        mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        region = context.region
        rv3d = context.region_data
        c2 = view3d.region_2d_to_location_3d(region, rv3d, mouse_pos, c1)

        line = c1, c2

        from .project.utils import project_polylines
        project_polylines(((line,)), cut_through=self.cut_through)


    def end(self, context):
        '''Clean up.'''

        if self.nmesh:
            self.nmesh.finish()

        self.element = None
        self.bm = None
        self.verts = []

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_circle, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_init_circle, 'WINDOW')

        context.area.tag_redraw()

    def setup_drawing(self, context, verts):
        '''Setup the drawing for the line and circle'''

        obj = context.edit_object
        theme = addon.pref().theme.ops.mesh.join_verts

        line_color = theme.line
        self._callback_line = DrawPolyline([(verts[0].co, verts[0].co)], width=1.6, color=line_color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

        circle_color = theme.circle
        self._callback_circle = DrawCircle([], radius=12, width=1.6, color=circle_color, hide=[None], region=context.region, region_data=context.region_data)
        self._handle_circle = bpy.types.SpaceView3D.draw_handler_add(self._callback_circle.draw, (context,), 'WINDOW', 'POST_PIXEL')

        circle_color = (0.0, 0.0, 0.0, 1.0)
        self._callback_init_circle = DrawCircle([obj.matrix_world @ verts[0].co], radius=8, width=1.6, color=circle_color, hide=[None], region=context.region, region_data=context.region_data)
        self._handle_init_circle = bpy.types.SpaceView3D.draw_handler_add(self._callback_init_circle.draw, (context,), 'WINDOW', 'POST_PIXEL')

    def update_drawing(self, context, hit, verts, end_pos):
        '''Update the drawing with the new positions'''

        theme = addon.pref().theme.ops.mesh.join_verts

        if hit:
            line_color = theme.line
            points = [end_pos]
            width = 1.6
        else:
            line_color = (0.9, 0.9, 0.9, 1.0) if self.cut_through else (0.0, 0.0, 0.0, 1.0)
            points = []
            width = 1

        matrix_world = context.edit_object.matrix_world
        lines = [(matrix_world @ vert.co, end_pos) for vert in verts]
        self._callback_line.update_batch(lines, line_color, width)
        self._callback_circle.update_batch(points)

    def connect_vertices(self, context, bm, verts, end_vert):
        '''Connect all selected vertices to the end vertex.'''

        # Ensure the end vertex is valid
        if not end_vert:
            return

        end_vert.select = True
        # Connect each selected vertex to the end vertex
        for vert in verts:
            if vert != end_vert:
                result = bmesh.ops.connect_vert_pair(bm, verts=[vert, end_vert])
                if result:
                    if not result['edges']:
                        result = bmesh.ops.connect_verts(bm, verts=[vert, end_vert])

                    if result:
                        for e in result['edges']:
                            e.select = True

        # Update the mesh to reflect the changes
        bm.select_flush_mode()
        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)

    def connect_vertices_to_edge(self, context, bm, verts, edge, point):
        '''Connect all selected vertices to the edge at the closest point.'''

        verts_indices = [v.index for v in verts]

        # Subdivide the edge with one cut
        result = bmesh.ops.subdivide_edges(bm, edges=[edge], cuts=1)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        # Retrieve the new vertex from the operation result
        new_vert = next((elem for elem in result['geom_inner'] if isinstance(elem, bmesh.types.BMVert)), None)

        verts = [v for v in bm.verts if v.index in verts_indices]

        if new_vert:
            new_vert.co = point  # Move the new vertex to the closest point on the edge
            new_vert.select = True

            # Connect each selected vertex to the new vertex created on the edge
            for vert in verts:
                if vert != new_vert and vert.is_valid:
                    result = bmesh.ops.connect_vert_pair(bm, verts=[vert, new_vert])
                    if result:
                        for e in result['edges']:
                            e.select = True

        # Update the mesh to reflect the changes
        bm.select_flush_mode()
        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)

    def connect_vertices_to_face(self, context, bm, verts, face, point):
        '''Connect all selected vertices to the face at the given point.'''

        verts_indices = [v.index for v in verts]
        face_edges_indices = [e.index for e in face.edges]

        # Create a new vertex at the given point on the face
        new_vert = bm.verts.new(point)
        bm.verts.ensure_lookup_table()

        # Remove the original face
        bmesh.ops.delete(bm, geom=[face], context='FACES_ONLY')

        # bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)

        verts = [v for v in bm.verts if v.index in verts_indices]
        face_edges = [e for e in bm.edges if e.index in face_edges_indices]

        # Connect the new vertex to two vertices of the original face
        bm.edges.new((face_edges[0].verts[0], new_vert))

        # Rebuild the faces
        new_faces = []
        for edge in face_edges:
            new_face = bm.faces.new((edge.verts[0], edge.verts[1], new_vert))
            new_faces.append(new_face)

        new_vert.select = True

        bmesh.ops.recalc_face_normals(bm, faces=new_faces)

        # Connect each selected vertex to the new vertex created on the face
        for vert in verts:
            if vert != new_vert and vert.is_valid:
                result = bmesh.ops.connect_vert_pair(bm, verts=[vert, new_vert])
                if result:
                    for e in result['edges']:
                        e.select = True

        # Update the mesh to reflect the changes
        bm.select_flush_mode()
        bm.normal_update()
        bmesh.update_edit_mesh(context.edit_object.data, loop_triangles=True, destructive=True)

    def perpendicular_point(self, p1, e1, e2):
        '''Calculate the perpendicular point from p1 to the edge e1-e2 in world space.'''

        # Calculate the direction vector of the edge in world space
        edge_dir = e2 - e1
        # Compute the vector from p1 to the start of the edge in world space
        point_to_edge_start = p1 - e1
        # Project this vector onto the edge's direction vector in world space
        projected_vector = point_to_edge_start.project(edge_dir)
        # Find the closest point on the edge to the original point in world space
        closest_point_on_edge = e1 + projected_vector

        # Transform the closest point back to local space
        closest_point_on_edge_local = closest_point_on_edge

        return closest_point_on_edge_local

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar with the hotkeys.'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Pick Vert')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_ALT')
        row.label(text=f'Fallback Cut Through: {"ON" if self.cut_through else "OFF"}')
        row.separator(factor=12.0)


def bbox_center(obj):
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    bbox_center = sum(bbox_corners, Vector()) / 8
    return bbox_center


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Join Verts Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 1.0, 0.0, 1.0), min=0.0, max=1.0)
        circle: bpy.props.FloatVectorProperty(name="Join Verts Circle", description="Color of the circle", size=4, subtype='COLOR', default=(1.0, 1.0, 0.0, 1.0), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
