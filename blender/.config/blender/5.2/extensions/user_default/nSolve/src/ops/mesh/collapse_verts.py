import bpy
import bmesh
from mathutils import Vector
from ....utils.view3d import location_3d_to_region_2d
from ...draw.circle import DrawCircle
from ..utils import infobar
from ....utils import addon
from ....utils.nmesh import Nmesh
from ... import analytics


class NSOLVE_OT_CollapseVerts(bpy.types.Operator):
    bl_idname = "nsolve.collapse_verts"
    bl_label = "Collapse Vertex"
    bl_description = f"{bl_label}\n\nCollapse Vertices into Selected Vertex"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    radius: bpy.props.FloatProperty(
        name="Radius",
        description="Radius of influence",
        default=30.0,
        min=0.01,
        step=100,
        precision=2
    )

    detect_vert: bpy.props.BoolProperty(
        name="Detect Vertex",
        description="Detect vertex under the cursor",
        default=True
    )

    affect_selected: bpy.props.BoolProperty(
        name="Affect Selected",
        description="Collapse only selected vertices",
        default=False
    )

    start_mouse_pos: Vector = Vector()
    bm: bmesh.types.BMesh = None
    nm: Nmesh = None
    vert: bmesh.types.BMVert = None

    verts_to_collapse_co: list = []
    verts_selected: list = []

    alt_hold: bool = False

    _callback_circle: DrawCircle
    _handle_circle: int
    _callback_verts: DrawCircle
    _handles_verts: int

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        self.alt_hold = event.alt

        self.selection_mode = context.tool_settings.mesh_select_mode[:]
        context.tool_settings.mesh_select_mode = True, False, False

        # pick mouseover object
        if self.detect_vert:
            loc = int(event.mouse_region_x), int(event.mouse_region_y)
            bpy.ops.view3d.select(location=loc)

        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)
        self.nm = Nmesh.from_bmesh(context, self.bm, obj)

        self.bm.verts.ensure_lookup_table()

        self.selected_verts_ids = [v.index for v in self.bm.verts if v.select]

        if self.detect_vert:
            self.nm.detect_element(event, mode=(True, False, False))
            self.vert = self.nm.element[1]
            if not self.vert:
                return {'CANCELLED'}
        else:
            selected_verts = [v for v in self.bm.verts if v.select]

            if len(selected_verts) != 1:
                self.report({'WARNING'}, "Exactly one vertex must be selected.")
                return {'CANCELLED'}

            self.vert = selected_verts[0]


        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        analytics.stats("nSolve: Collapse Verts")
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.merge_vertices(context)

        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse_pos = (event.mouse_region_x, event.mouse_region_y)
            self.update_drawing(context, mouse_pos)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            self.alt_hold = event.alt
            self.execute(context)
            self.end(context)
            return {'FINISHED'}

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

        context.tool_settings.mesh_select_mode = self.selection_mode

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_circle, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handles_verts, 'WINDOW')

        context.area.tag_redraw()

    def setup_drawing(self, context):
        '''Setup the drawing for the circle and vertices within the circle'''

        theme = addon.pref().theme.ops.mesh.collapse_verts

        color = theme.circle
        self._callback_circle = DrawCircle([self.vert.co], self.radius, 2.0, color, [None], context.region, context.region_data)
        self._handle_circle = bpy.types.SpaceView3D.draw_handler_add(self._callback_circle.draw, (context,), 'WINDOW', 'POST_PIXEL')

        color = theme.verts
        self._callback_verts = DrawCircle([], 12, 2.0, color, [], context.region, context.region_data)
        self._handles_verts = bpy.types.SpaceView3D.draw_handler_add(self._callback_verts.draw, (context,), 'WINDOW', 'POST_PIXEL')

    def update_drawing(self, context, mouse_pos):
        '''Update the drawing for the circle and vertices within the circle'''

        obj = context.edit_object
        matrix_world = obj.matrix_world

        # Convert mouse position to 3D space for radius calculation
        center_2d = self.convert_to_2d(context, matrix_world @ self.vert.co)
        if center_2d is None:
            return  # Early exit if conversion fails

        self.radius = (Vector(mouse_pos) - Vector(self.start_mouse_pos)).length
        self._callback_circle.update_batch([matrix_world @ self.vert.co], radius=self.radius)

        # Reset the list of vertices to collapse
        self.verts_to_collapse_co.clear()

        bpy.ops.view3d.select_circle(x=int(center_2d.x), y=int(center_2d.y), radius=int(self.radius), wait_for_input=False, mode='SET')

        self.verts_selected = [v for v in self.bm.verts if v.select]

        for v in self.verts_selected:
                self.verts_to_collapse_co.append(matrix_world @ v.co)

        bpy.ops.mesh.select_all(action='DESELECT')

        # Update the drawing for vertices within the circle
        self._callback_verts.update_batch(self.verts_to_collapse_co, radius=5)  # Adjust the radius as needed for visual clarity

        context.area.tag_redraw()

    def merge_vertices(self, context):
        '''Merge vertices within the circle'''

        obj = context.edit_object
        matrix_world = obj.matrix_world

        # Convert the circle's screen position to the 3D location in the view
        center_2d = self.convert_to_2d(context, matrix_world @ self.vert.co)
        if center_2d is None:
            return  # Can't find the 2D position of the vertex


        to_merge = self.verts_selected

        if to_merge:
            merge_co = self.vert.co.copy()

            doubles = bmesh.ops.find_doubles(self.bm, verts=self.bm.verts, keep_verts=to_merge, dist=0.00001)
            bmesh.ops.weld_verts(self.bm, targetmap=doubles['targetmap'])

            if self.alt_hold:  # If left Alt key is held
                target_merge_position = Vector((0, 0, 0))
                for vert in to_merge:
                    target_merge_position += vert.co
                target_merge_position /= len(to_merge)
            else:
                target_merge_position = merge_co

            for vert in to_merge:
                vert.co = target_merge_position

            # Use remove_doubles to merge vertices that have been moved to the same location
            bmesh.ops.remove_doubles(self.bm, verts=to_merge, dist=0.0001)  # Adjust dist as necessary


            # Update the mesh
            bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
            bpy.ops.mesh.select_all(action='DESELECT')

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

    def convert_to_2d(self, context, vert_pos):
        '''Convert 3D vertex position to 2D screen position'''

        region = context.region
        rv3d = context.region_data
        return location_3d_to_region_2d(region, rv3d, vert_pos)


class types():
    class theme(bpy.types.PropertyGroup):
        verts: bpy.props.FloatVectorProperty(name="Collapse Verts verts", description="Color of the verts", size=4, subtype='COLOR', default=(0.2, 0.2, 0.2, 0.8), min=0.0, max=1.0)
        circle: bpy.props.FloatVectorProperty(name="Collapse Verts Circle", description="Color of the circle", size=4, subtype='COLOR', default=(1.0, 0.0, 0.0, 0.8), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
