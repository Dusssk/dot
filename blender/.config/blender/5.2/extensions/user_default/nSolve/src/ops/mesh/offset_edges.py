import bpy
import bmesh

from mathutils import Vector

from ...draw.polyline import DrawPolyline

from ..utils import infobar
from ....utils import view3d, addon

from ... import analytics


class NSOLVE_OT_Offset_Edges(bpy.types.Operator):
    bl_idname = "nsolve.offset_edges"
    bl_label = "Offset Edges"
    bl_description = f"{bl_label}\n\nOffset selected edges"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    offset: bpy.props.FloatProperty(name="Offset", description="Offset distance", default=0.1, min=0.0, precision=3)
    loop_slide: bpy.props.BoolProperty(name="Loop Slide", description="Prefer sliding along the edges to even widths", default=True)

    bm: bmesh.types.BMesh = None
    mesh: bpy.types.Mesh = None
    edges: list = []

    start_mouse_pos: Vector

    _callback_guid: DrawPolyline
    _handle_guid: int

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.prop(self, 'offset')
        layout.prop(self, 'loop_slide')

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        obj = context.edit_object
        obj.update_from_editmode()

        self.bm = bmesh.from_edit_mesh(obj.data)
        self.mesh = obj.data.copy()

        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        self.edges = [e.index for e in self.bm.edges if e.select]

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set('Join Vertices')
        context.window.cursor_set('SCROLL_XY')

        self.setup_drawing(context)

        context.window_manager.modal_handler_add(self)
        analytics.stats("nSolve: Offset Edges")
        return {'RUNNING_MODAL'}

    def execute(self, context):

        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)

        bm.edges.ensure_lookup_table()

        selected_edges = [e for e in bm.edges if e.select]
        self.offset_edges(bm, selected_edges, self.offset)

        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

            start_mouse_pos_3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, self.start_mouse_pos, Vector((0, 0, 0)))
            mouse_pos_3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, mouse_pos, Vector((0, 0, 0)))

            offset = (mouse_pos_3d - start_mouse_pos_3d).length
            self.offset = offset

            self.restore_original_mesh(context)

            self.bm.edges.ensure_lookup_table()
            edges = [self.bm.edges[i] for i in self.edges]
            self.offset_edges(self.bm, edges, offset)

            self.update_drawing([start_mouse_pos_3d, mouse_pos_3d])

            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':

            self.end(context)
            return {'FINISHED'}

        elif event.type == 'E' and event.value == 'RELEASE':
            self.loop_slide = not self.loop_slide
            self.restore_original_mesh(context)
            self.bm.edges.ensure_lookup_table()
            edges = [self.bm.edges[i] for i in self.edges]
            self.offset_edges(self.bm, edges, self.offset)

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            self.restore_original_mesh(context)
            self.bm.select_flush_mode()
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def end(self, context):
        '''Clean up.'''

        bpy.data.meshes.remove(self.mesh)

        self.bm = None
        self.mesh = None
        self.edges = []

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_guid, 'WINDOW')

        context.area.tag_redraw()

    def restore_original_mesh(self, context):
        '''Restore the original mesh data from a backup stored in self.mesh'''

        obj = context.edit_object

        bm = self.bm
        bm.clear()
        bm.from_mesh(self.mesh)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

        bpy.ops.mesh.select_all(action='DESELECT')

    def setup_drawing(self, context):
        '''Setup the drawing'''

        theme = addon.pref().theme.ops.mesh.offset_edges

        points = [(Vector((0, 0, 0)), Vector((0, 0, 0)))]

        color = theme.guid
        self._callback_guid = DrawPolyline(points, width=1.2, color=color)
        self._handle_guid = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

    def update_drawing(self, points):
        '''Update the drawing with new points'''

        theme = addon.pref().theme.ops.mesh.offset_edges

        line_segments = [(points[0], points[1])]
        self._callback_guid.update_batch(line_segments, color=theme.guid)

    def offset_edges(self, bm, edges, offset):
        '''Offset the selected edges.'''

        obj = bpy.context.edit_object
        result = bmesh.ops.bevel(bm, geom=edges, offset=offset, offset_type='OFFSET', segments=2, profile=1, affect='EDGES', clamp_overlap=False, loop_slide=self.loop_slide, mark_seam=False, mark_sharp=False, harden_normals=False, miter_outer='ARC')
        for v in result['verts']:
            v.select_set(True)
        for e in result['edges']:
            e.select_set(True)
        for f in result['faces']:
            f.select_set(True)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

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
        row.label(text='', icon='EVENT_E')
        row.label(text=f'Loop Slide: {self.loop_slide}')
        row.separator(factor=12.0)


class types():
    class theme(bpy.types.PropertyGroup):
        guid: bpy.props.FloatVectorProperty(name="Hard Edge Slide guid", description="Color of the guid", size=4, subtype='COLOR', default=(0.2, 0.2, 0.2, 1), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
