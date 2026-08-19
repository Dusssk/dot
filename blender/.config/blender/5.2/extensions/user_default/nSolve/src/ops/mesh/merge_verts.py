import bpy
import bmesh

from mathutils import Vector

from ...draw.polyline import DrawPolyline
from ...draw.circle import DrawCircle

from ..utils import infobar
from ....utils import addon
from ....utils.nmesh import Nmesh

from ... import analytics


class NSOLVE_OT_MergeVerts(bpy.types.Operator):
    bl_idname = "nsolve.merge_verts"
    bl_label = "Merge Vertices"
    bl_description = f"{bl_label}\n\nMerge selected vertex with the one closest to the mouse cursor"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    multi: bpy.props.BoolProperty(
        name="multi",
        description="Merge multiple vertices",
        default=False
    )

    center_merge: bpy.props.BoolProperty(
        name="Center Merge",
        description="Merge at center by default",
        default=False
    )

    merge_weld: bpy.props.BoolProperty(
        name="Merge Closest",
        description="Merge closest vertex (experiemental)",
        default=False
    )

    merge_weld_dist: bpy.props.FloatProperty(
        name="Merge Closest Distance",
        description="Merge closest vertex distance",
        default=0.1,
        min=0.01,
    )

    verts: dict = {}
    start_mouse_pos: Vector
    selected_verts: set
    detected_vert: bmesh.types.BMVert = None
    bm: bmesh.types.BMesh
    nm: Nmesh = None

    alt: bool = False

    _callback_line: DrawPolyline
    _handle_line: int
    _callback_circle: DrawCircle
    _handle_circle: int

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)
        self.nm = Nmesh.from_bmesh(context, self.bm, obj)

        self.verts.clear()

        if not self.multi:
            bpy.ops.mesh.select_all(action='DESELECT')
            self.nm.detect_element(event, mode=(True, False, False))
            if not self.nm.element[1]:
                return {'CANCELLED'}
            self.nm.element[1].select = True

        self.selected_verts = {v for v in self.bm.verts if v.select}

        if len(self.selected_verts) < 1:
            return {'CANCELLED'}

        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        analytics.stats("nSolver: Merge Vertices")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        self.alt = self.center_merge != event.alt

        if event.type == 'MOUSEMOVE':
            self.nm.detect_element(event, mode=(True, False, False))
            if self.nm.element[1]:
                self.detected_vert = self.nm.element[1]

                self.update_drawing(context)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            if self.detected_vert:
                self.merge_vertices(context)
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def end(self, context):
        '''Cleanup and finish the operator'''

        self.verts = {}
        self.selected_verts = set()
        self.bm = None
        self.nm = None
        self.detected_vert = None

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_circle, 'WINDOW')

        context.area.tag_redraw()

    def setup_drawing(self, context):
        '''Setup the drawing for the line and circle'''

        points = [(Vector((0, 0, 0)), Vector((0, 0, 0)))]

        theme = addon.pref().theme.ops.mesh.merge_verts

        color = theme.line
        self._callback_line = DrawPolyline(points, width=1.6, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

        points = [Vector((0, 0, 0))]  # Initial point for the circle
        radius = 12  # Example radius
        width = 1.6  # Line width for the circle
        color = theme.circle
        self._callback_circle = DrawCircle(points, radius, width, color, [None], context.region, context.region_data)
        self._handle_circle = bpy.types.SpaceView3D.draw_handler_add(self._callback_circle.draw, (context,), 'WINDOW', 'POST_PIXEL')

    def update_drawing(self, context):
        '''Update the drawing for the line and circle'''

        theme = addon.pref().theme.ops.mesh.merge_verts

        line_points = [(context.edit_object.matrix_world @ sv.co, context.edit_object.matrix_world @ self.detected_vert.co) for sv in self.selected_verts]

        vets_to_merge = list(self.selected_verts)
        if self.detected_vert not in self.selected_verts:
            vets_to_merge.append(self.detected_vert)

        merge_point = self.detected_vert.co

        if self.alt:
            merge_point = sum([v.co for v in vets_to_merge], Vector()) / len(vets_to_merge)

        circle_points = [context.edit_object.matrix_world @ merge_point]

        color = theme.line
        self._callback_line.update_batch(line_points, color=color)
        self._callback_circle.update_batch(circle_points)

    def merge_vertices(self, context):
        '''Merge the selected vertices'''

        obj = context.edit_object
        vets_to_merge = list(self.selected_verts)
        if self.detected_vert not in self.selected_verts:
            vets_to_merge.append(self.detected_vert)

        merge_point = self.detected_vert.co

        if self.alt:
            merge_point = sum([v.co for v in vets_to_merge], Vector()) / len(vets_to_merge)

        bmesh.ops.pointmerge(self.bm, verts=vets_to_merge, merge_co=merge_point)

        if self.merge_weld:
            selected_verts = [v for v in self.bm.verts if v.select]
            faces = selected_verts[0].link_faces
            verts = list(set(v for f in faces for v in f.verts))
            bmesh.ops.remove_doubles(self.bm, verts=verts, dist=self.merge_weld_dist)

        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''

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


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Merge Verts Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 0.0, 0.0, 1.0), min=0.0, max=1.0)
        circle: bpy.props.FloatVectorProperty(name="Merge Verts Circle", description="Color of the circle", size=4, subtype='COLOR', default=(0.0, 0.0, 0.0, 1.0), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
