import math
import bpy
import bmesh

from mathutils import Vector, Quaternion

from ....draw.polyline import DrawPolyline

from .utils import project_polylines
from ...utils import infobar
from .....utils import addon, view3d


class NSOLVE_OT_ProjectLine(bpy.types.Operator):
    bl_idname = "nsolve.project_line"
    bl_label = "Project Line"
    bl_description = f"{bl_label}\n\nProject a line between the selected points to the mesh"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    cut_through: bpy.props.BoolProperty(name="Cut Through", description="Cut through the mesh", default=False)
    draw_text: bpy.props.StringProperty(default="nSuite")

    bm: bmesh.types.BMesh = None
    points: list = []
    start_mouse_pos: tuple = None
    depth: Vector = None

    mouse_init: bpy.props.BoolProperty(name="Mouse Init", default=True)

    alt: bool = False

    _callback_line: DrawPolyline = None
    _handle_line: int = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        if self.mouse_init:
            obj = context.edit_object
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.start_mouse_pos = mouse_pos
            self.depth = self.get_depth(context, obj)
            mouse_pos_3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, mouse_pos, self.depth)
            self.points = [mouse_pos_3d, mouse_pos_3d]

        self.setup_drawing(context)

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        cut_through = "Cut Through: True" if self.cut_through else "Cut Through: False"
        context.area.header_text_set(f'Project Line:    {cut_through}')
        context.window.cursor_set('SCROLL_XY')

        context.window_manager.modal_handler_add(self)
        if self.draw_text: bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text=self.draw_text)
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Project Line", position=(50, 2))
        self.draw_text = "nSuite"
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        if event.type == 'LEFT_ALT' and (event.value == 'PRESS' or event.value == 'RELEASE'):
            self.cut_through = not self.cut_through
            cut_through = "Cut Through: True" if self.cut_through else "Cut Through: False"
            context.area.header_text_set(f'Project Line:    {cut_through}')
            self.update_drawing(self.points)
            context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':

            if not self.mouse_init:
                obj = context.edit_object
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                self.start_mouse_pos = mouse_pos
                normal = context.space_data.region_3d.view_rotation @ Vector((0.0, 0.0, -1.0))
                self.depth = view3d.location2d_to_origin3d(event.mouse_region_x, event.mouse_region_y) + normal * 0.1
                mouse_pos_3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, mouse_pos, self.depth)
                self.points = [mouse_pos_3d, mouse_pos_3d]


            else:
                mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

                use_snap = context.scene.tool_settings.use_snap or event.ctrl
                if use_snap:
                    if event.shift:
                        mouse_pos = self.snap(context, mouse_pos, precision=True)
                    else:
                        mouse_pos = self.snap(context, mouse_pos)

                mouse_pos_3d = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, mouse_pos, self.depth)

                self.points = [self.points[0], mouse_pos_3d]
                self.update_drawing(self.points)
                context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            if not self.mouse_init:
                if event.value == 'PRESS':
                    self.mouse_init = True
                    return {'RUNNING_MODAL'}
            else:
                polylines = [self.points]
                project_polylines(polylines, cut_through=self.cut_through)
                self.end(context)
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:

            self.bm.select_flush_mode()
            self.end(context)
            return {'CANCELLED'}

        elif event.type == 'C' and event.value == 'PRESS':
            self.cut_through = not self.cut_through
            cut_through = "Cut Through: True" if self.cut_through else "Cut Through: False"
            context.area.header_text_set(f'Project Line:    {cut_through}')

        return {'RUNNING_MODAL'}

    def snap(self, context, mouse_pos, precision=False):

        angle_increment = math.radians(15)
        if precision:
            angle_increment = math.radians(5)

        # Calculate the 2D angle from initial to current mouse position
        angle = math.atan2(mouse_pos[1] - self.start_mouse_pos[1], mouse_pos[0] - self.start_mouse_pos[0])
        snap_angle_rad = angle_increment
        snapped_angle = round(angle / snap_angle_rad) * snap_angle_rad

        # Calculate the distance to maintain from start to current position
        distance = (mouse_pos - self.start_mouse_pos).length

        # Create a direction vector from the snapped angle
        direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))

        # Update current mouse position in 2D based on the snapped direction and original distance
        snaped_mouse_pos = self.start_mouse_pos + direction * distance

        return snaped_mouse_pos

    def get_depth(self, context, obj):
        '''Find the nearest point on the object to the view location.'''

        rv3d = context.region_data

        # Get the view matrix and invert it to obtain the view location
        view_location = rv3d.view_matrix.inverted().translation

        # Calculate the object's bounding box corners in world space
        obj_matrix_world = obj.matrix_world
        bbox_corners = [obj_matrix_world @ Vector(corner) for corner in obj.bound_box]

        # Find the center of the bounding box
        bbox_center = sum(bbox_corners, Vector((0.0, 0.0, 0.0))) / 8

        # Calculate the direction from the center towards the view location
        direction_to_view = (view_location - bbox_center).normalized()

        # Calculate the bounding box dimensions and find the maximum
        bbox_dimensions = obj.dimensions
        max_dimension = max(bbox_dimensions)

        point_in_front = bbox_center + direction_to_view * max_dimension

        return point_in_front

    def end(self, context):
        '''Clean up.'''

        self.bm = None
        self.points = []

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')

        context.area.tag_redraw()

    def setup_drawing(self, context):
        '''Setup the drawing for the line and circle'''

        theme = addon.pref().theme.ops.mesh.project.line

        points = [Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0))]

        line_color = theme.line
        self._callback_line = DrawPolyline([points[0], points[1]], width=1.6, color=line_color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

    def update_drawing(self, points):
        '''Update the drawing with the new positions'''

        width = 3.2 if self.cut_through else 1.6
        self._callback_line.update_batch([points], width=width)

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar with the hotkeys.'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Draw')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_C')
        row.label(text='Cut Through')
        row.separator(factor=12.0)


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Project Line", description="Color of the line", size=4, subtype='COLOR', default=(0.57, 0.87, 1.0, 1.0), min=0.0, max=1.0)


types_classes = (
    types.theme,
)
