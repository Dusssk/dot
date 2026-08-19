import bpy
import bmesh
from mathutils import Vector, kdtree
from ....utils.view3d import location_3d_to_region_2d, region_2d_to_location_3d
from ...draw.circle import DrawCircle
from ...draw.sphere import DrawSphere
from ..utils import infobar
from ....utils import addon
from ....utils.nmesh import Nmesh

class NSOLVE_OT_Hide(bpy.types.Operator):
    bl_idname = "nsolve.hide"
    bl_label = "Hide mesh"
    bl_description = f"{bl_label}\n\nHide vertices within a circle"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    radius: bpy.props.FloatProperty(
        name="Radius",
        description="Radius of influence",
        default=30.0,
        min=0.01,
        step=100,
        precision=2
    )

    reverse: bpy.props.BoolProperty(
        name="Reverse",
        description="Reverse the selection",
        default=True
    )

    volume: bpy.props.BoolProperty(
        name="Volume",
        description="Hide using Sphere",
        default=False
    )

    start_mouse_pos: Vector = Vector()
    bm: bmesh.types.BMesh = None
    nm: Nmesh = None
    vert: bmesh.types.BMVert = None

    start_loc: Vector = Vector()

    hidden_verts: list = []

    verts_to_hide: list = []
    verts_selected: list = []

    alt_hold: bool = False

    _callback_circle: DrawCircle
    _callback_sphere: DrawSphere
    _handle_circle: int
    _handle_sphere: int
    _kd: kdtree.KDTree = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        self.alt_hold = event.alt

        self.selection_mode = context.tool_settings.mesh_select_mode[:]
        context.tool_settings.mesh_select_mode = True, False, False

        loc = int(event.mouse_region_x), int(event.mouse_region_y)
        bpy.ops.view3d.select(location=loc)

        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)
        self.nm = Nmesh.from_bmesh(context, self.bm, obj)

        self.bm.verts.ensure_lookup_table()

        # Create KD-tree for volume selection
        size = len(self.bm.verts)
        self._kd = kdtree.KDTree(size)
        matrix_world = obj.matrix_world
        for i, v in enumerate(self.bm.verts):
            self._kd.insert(matrix_world @ v.co, i)
        self._kd.balance()

        self.hidden_verts = [v for v in self.bm.verts if v.hide]

        self.nm.detect_element(event, mode=(True, False, True))

        if not self.nm.element:
            return {'CANCELLED'}

        if self.nm.element[0] == 'VERT':
            self.vert = self.nm.element[1]
            if not self.vert:
                return {'CANCELLED'}
            self.start_loc = self.vert.co

        elif self.nm.element[0] == 'FACE':
            self.start_loc = self.nm.element[2]

        else:
            return {'CANCELLED'}

        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            self.update_drawing(context, mouse_pos)

            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            self.alt_hold = event.alt
            self.end(context)
            return {'FINISHED'}

        elif event.type == 'V' and event.value == 'PRESS':
            self.volume = not self.volume
            mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            self.update_drawing(context, mouse_pos)
            context.area.tag_redraw()

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.end(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def draw(self, _context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, "radius")

    def end(self, context):
        '''Cleanup and finish the operator'''

        self.bm = None
        self.nm = None
        self.vert = None
        self._kd = None

        context.tool_settings.mesh_select_mode = self.selection_mode

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_sphere, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_circle, 'WINDOW')

        context.area.tag_redraw()

    def setup_drawing(self, context):
        '''Setup the drawing for the circle and vertices within the circle'''

        theme = addon.pref().theme.ops.mesh.hide

        color = theme.sphere
        self._callback_sphere = DrawSphere(self.start_loc, self.radius, color, None)
        self._handle_sphere = bpy.types.SpaceView3D.draw_handler_add(self._callback_sphere.draw, (context,), 'WINDOW', 'POST_VIEW')

        color = theme.circle
        self._callback_circle = DrawCircle([], self.radius, 2.0, color, [None], context.region, context.region_data)
        self._handle_circle = bpy.types.SpaceView3D.draw_handler_add(self._callback_circle.draw, (context,), 'WINDOW', 'POST_PIXEL')

    def update_drawing(self, context, mouse_pos):
        '''Update the drawing for the circle and vertices within the circle'''

        obj = context.edit_object
        matrix_world = obj.matrix_world

        # Convert mouse position to 3D space for radius calculation
        center_2d = self.convert_to_2d(context, matrix_world @ self.start_loc)
        if center_2d is None:
            return  # Early exit if conversion fails
        
        self.radius = (Vector(mouse_pos) - Vector(self.start_mouse_pos)).length

        self.verts_to_hide.clear()

        bpy.ops.mesh.reveal()
        if not self.reverse:
            for v in self.hidden_verts:
                v.hide_set(True)

        if self.volume and self._kd:
            # Use KD-tree for spherical selection
            center_3d = matrix_world @ self.start_loc
            mouse_3d = region_2d_to_location_3d(context.region, context.region_data, mouse_pos, center_3d)
            radius_3d = (mouse_3d - center_3d).length
            self._callback_sphere.update_batch(center=center_3d, radius=radius_3d)
            self._callback_circle.update_batch([], radius=self.radius)
            for (co, index, dist) in self._kd.find_range(center_3d, radius_3d):
                vert = self.bm.verts[index]
                self.verts_to_hide.append(vert)
        else:
            # Use original circle-based selection
            self._callback_sphere.update_batch(Vector(), radius=0)
            self._callback_circle.update_batch([matrix_world @ self.start_loc], radius=self.radius)
            bpy.ops.view3d.select_circle(x=int(center_2d.x), y=int(center_2d.y), radius=int(self.radius), wait_for_input=False, mode='SET')
            self.verts_selected = [v for v in self.bm.verts if v.select]
            self.verts_to_hide.extend(self.verts_selected)

            bpy.ops.mesh.select_all(action='DESELECT')

        if self.reverse:
            verts = [v for v in self.bm.verts if v not in self.verts_to_hide]
            # Hide vertices and their connected faces
            for v in verts:
                v.hide_set(True)
                # Hide all faces connected to this vertex
                for f in v.link_faces:
                    f.hide_set(True)
        else:
            # Hide selected vertices and their connected faces
            for v in self.verts_to_hide:
                v.hide_set(True)
                # Hide all faces connected to this vertex
                for f in v.link_faces:
                    f.hide_set(True)

        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        context.area.tag_redraw()

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
        row.label(text='', icon='EVENT_V')
        row.label(text='Volume')

    def convert_to_2d(self, context, vert_pos):
        '''Convert 3D vertex position to 2D screen position'''

        region = context.region
        rv3d = context.region_data
        return location_3d_to_region_2d(region, rv3d, vert_pos)


class types():
    class theme(bpy.types.PropertyGroup):
        circle: bpy.props.FloatVectorProperty(name="Collapse Verts Circle", description="Color of the circle", size=4, subtype='COLOR', default=(0.8, 0.8, 0.0, 0.8), min=0.0, max=1.0)
        sphere: bpy.props.FloatVectorProperty(name="Collapse Verts Sphere", description="Color of the sphere", size=4, subtype='COLOR', default=(0.8, 0.8, 0.0, 0.04), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
