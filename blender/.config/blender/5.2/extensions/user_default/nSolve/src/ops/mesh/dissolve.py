import bpy
import bmesh

from mathutils import Vector

from ...draw.polyline import DrawPolyline

from ..utils import infobar
from ....utils import addon
from ....utils.nmesh import Nmesh

from ... import analytics

class NSOLVE_OT_Dissolve_Edges(bpy.types.Operator):
    bl_idname = "nsolve.dissolve_edges"
    bl_label = "Dissolve Edges Under Mouse"
    bl_description = f"{bl_label}\n\nDissolve edges under the mouse cursor"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    use_verts: bpy.props.BoolProperty(name="Dissolve Verts", description="Dissolve the vertices as well", default=True)
    use_face_split: bpy.props.BoolProperty(name="Split of face", description="Split off face corners to maintain surrounding geometry", default=False)

    detected_edge: bmesh.types.BMEdge = None

    bm: bmesh.types.BMesh = None
    nmesh: Nmesh = None

    _callback_line: DrawPolyline = None
    _handle_line: int = None

    @classmethod 
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        self.nmesh = Nmesh.from_bmesh(context, self.bm, obj)
        self.nmesh.detect_element(event, mode=(False, True, False))

        detected_edge = self.nmesh.element[1]

        edge_verts = [Vector((0, 0, 0)), Vector((0, 0, 0))]

        if detected_edge:
            edge_verts = [v.co for v in detected_edge.verts]
            self.detected_edge = detected_edge

        self.setup_drawing(context, edge_verts)

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set('Join Vertices')
        context.window.cursor_set('SCROLL_XY')
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Dissolve", position=(50, 2))

        context.window_manager.modal_handler_add(self)
        analytics.stats("nSuite: Dissolve Edges")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            self.nmesh.detect_element(event, mode=(False, True, False))
            detected_edge = self.nmesh.element[1]

            if detected_edge:
                edge_verts = [v.co for v in detected_edge.verts]
                self.update_drawing(context, edge_verts)
                self.detected_edge = detected_edge

            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            self.dissolve(self.bm, self.detected_edge)
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            self.bm.select_flush_mode()
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def dissolve(self, bm, edge):
        '''Dissolve the detected edge.'''

        if not edge:
            return

        obj = bpy.context.edit_object
        bmesh.ops.dissolve_edges(bm, edges=[edge], use_verts=self.use_verts, use_face_split=self.use_face_split)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

    def end(self, context):
        '''Clean up.'''

        self.detected_edge = None
        self.bm = None
        self.nmesh = None

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')

    def setup_drawing(self, context, verts):
        '''Setup the drawing for the line and circle'''

        theme = addon.pref().theme.ops.mesh.dissolve

        line_color = theme.line
        self._callback_line = DrawPolyline([(verts[0], verts[1])], width=1.6, color=line_color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

    def update_drawing(self, context, verts):
        '''Update the drawing with the new positions'''

        theme = addon.pref().theme.ops.mesh.dissolve
        line_color = theme.line

        obj = context.edit_object
        matrix = obj.matrix_world

        lines = [(matrix @ verts[0], matrix @ verts[1])]

        self._callback_line.update_batch(lines, line_color)

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


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Join Verts Line", description="Color of the line", size=4, subtype='COLOR', default=(1.0, 0.0, 0.0, 1.0), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
