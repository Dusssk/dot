import math
import bpy
import bmesh

from mathutils import Vector, geometry

from .utils import project_polylines
from ...utils import infobar
from ....draw.polyline import DrawPolyline
from .....utils import view3d, addon


class NSOLVE_OT_ProjectCircle(bpy.types.Operator):
    bl_idname = "nsolve.project_circle"
    bl_label = "Project Circle"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}
    bl_description = f"{bl_label}\n\nProject the circle using selected geometry normal"

    bm: bmesh.types.BMesh

    segments: bpy.props.IntProperty(name="Segments", description="Number of segments", default=8, min=3, max=256)
    cut_through: bpy.props.BoolProperty(name="Cut Through", description="Cut Through the whole mesh", default=False)

    guid: list = []
    polylines: list = []

    mouse_pos: Vector = Vector()
    median: Vector
    view_normal: Vector = Vector((0, 0, 1))

    moving: bool = False
    radius: float = 0.0
    rotating: bool = False
    rotation = 0.0

    _callback_line: DrawPolyline
    _handle_line: int
    _callback_guid: DrawPolyline
    _handle_guid: int

    mouse_init: bool = True

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'segments')
        layout.prop(self, 'cut_through')

    def invoke(self, context, event):
        self.cut_through = event.alt

        obj = context.edit_object
        self.bm = bmesh.from_edit_mesh(obj.data)

        selected_verts = [v for v in self.bm.verts if v.select]

        if not selected_verts:
            self.median = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, Vector((event.mouse_region_x, event.mouse_region_y)), Vector(context.scene.cursor.location))
        else:
            self.median = sum([obj.matrix_world @ v.co for v in selected_verts], Vector()) / len(selected_verts)

        rv3d = context.space_data.region_3d
        self.view_normal = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        context.area.header_text_set(f'Project Circle:    Segments: {self.segments}')
        context.window.cursor_set('SCROLL_XY')

        self.setup_drawing(context)
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Project Circle", position=(50, 2))
        return {'RUNNING_MODAL'}

    def execute(self, context):

        self.polylines.clear()
        self.define_circle(context, self.median, self.segments, self.radius, self.view_normal)
        project_polylines(self.polylines, cut_through=self.cut_through)

        return {'FINISHED'}

    def modal(self, context, event):
        self.rotating = event.shift and not self.moving

        if (self.cut_through != event.alt):
            self.cut_through = event.alt
            infobar.draw(context, event, self.infobar_hotkeys, blank=True)
            if not self.mouse_init:
                self.update_drawing(context)
                context.area.tag_redraw()

        def update_circle():
            self.polylines.clear()
            self.define_circle(context, self.median, self.segments, self.radius, self.view_normal)
            self.update_drawing(context)
            context.area.header_text_set(f'Project Circle:    Segments: {self.segments}')
            context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':

            if not self.mouse_init:

                self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

                if self.moving:
                    self.median = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, self.mouse_pos, self.median)
                    update_circle()

                elif event.shift:
                    self.rotating = True
                    md = view3d.location_3d_to_region_2d(context.region, context.space_data.region_3d, self.median, default=self.mouse_pos)
                    dt = self.mouse_pos - md
                    self.rotation = -dt.angle_signed(Vector((1.0, 0.0)), 0.0)
                    update_circle()

                else:
                    use_snap = context.scene.tool_settings.use_snap or event.ctrl
                    if use_snap:
                        if event.shift:
                            self.mouse_pos = self.snap(context, precision=True)
                        else:
                            self.mouse_pos = self.snap(context)

                    intersect_point = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, self.mouse_pos, self.median)
                    self.radius = (intersect_point - self.median).length

                    update_circle()

        elif event.type == 'LEFTMOUSE':

            if self.mouse_init:
                if event.value == 'PRESS':
                    obj = context.edit_object
                    self.mouse_init = False

                    selected_verts = [v for v in self.bm.verts if v.select]

                    if not selected_verts:
                        self.median = view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, Vector((event.mouse_region_x, event.mouse_region_y)), Vector(context.scene.cursor.location))
                    else:
                        self.median = sum([obj.matrix_world @ v.co for v in selected_verts], Vector()) / len(selected_verts)

                    rv3d = context.space_data.region_3d
                    self.view_normal = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))

                    return {'RUNNING_MODAL'}

            else:
                project_polylines(self.polylines, cut_through=self.cut_through)
                self.end(context)
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.end(context)
            return {'CANCELLED'}

        elif event.type == 'G' and event.value == 'PRESS':
            self.moving = not self.moving

        # Segments with WHEELUPMOUSE num+ or EQUAL or S or up arrow

        elif event.type == 'WHEELUPMOUSE' or event.type == 'NUMPAD_PLUS' or event.type == 'EQUAL' or event.type == 'S':
            if event.value == 'PRESS':
                self.segments += 1
                update_circle()

        elif event.type == 'WHEELDOWNMOUSE' or event.type == 'NUMPAD_MINUS' or event.type == 'MINUS' or event.type == 'A':
            if event.value == 'PRESS':
                self.segments -= 1
                update_circle()

        elif event.type == 'F' and event.value == 'PRESS':
            active_verts = [v for v in self.bm.verts if v.select]
            len_verts = len(active_verts)
            self.segments = len_verts
            update_circle()

        return {'RUNNING_MODAL'}

    def snap(self, context, precision=False):

        angle_increment = math.radians(15)
        if precision:
            angle_increment = math.radians(5)

        median = view3d.location_3d_to_region_2d(context.region, context.space_data.region_3d, self.median)

        # Calculate the 2D angle from initial to current mouse position
        angle = math.atan2(self.mouse_pos[1] - median[1], self.mouse_pos[0] - median[0])
        snap_angle_rad = angle_increment
        snapped_angle = round(angle / snap_angle_rad) * snap_angle_rad

        # Calculate the distance to maintain from start to current position
        distance = (self.mouse_pos - median).length

        # Create a direction vector from the snapped angle
        direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))

        # Update current mouse position in 2D based on the snapped direction and original distance
        snaped_mouse_pos = median + direction * distance

        return snaped_mouse_pos

    def define_circle(self, context, center, segments, radius, normal):
        region = context.region
        rv3d = context.region_data

        if radius == 0.0:
            # Calculate the intersection point for the radius and direction from center
            intersect_point = view3d.region_2d_to_location_3d(region, rv3d, self.mouse_pos, center)
            radius = (intersect_point - center).length

        # Establishing the orthogonal basis
        view_normal = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
        up = rv3d.view_rotation @ Vector((0.0, 1.0, 0.0))
        right = up.cross(view_normal).normalized()

        # Calculate the points of the circle, ensuring they are in the plane
        angle_increment = 2 * math.pi / segments
        circle_points = []
        for i in range(segments):
            angle = i * angle_increment
            angle += self.rotation
            point = center + (math.cos(angle) * right + math.sin(angle) * up) * radius
            circle_points.append(point)

        # Closing the circle by connecting the last point to the first
        circle_points.append(circle_points[0])

        # Append the entire circle as one polyline
        self.polylines.append(circle_points)

    def end(self, context):
        '''Cleanup and finish the operator'''

        self.bm = None

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_guid, 'WINDOW')

        context.area.tag_redraw()

    def update_drawing(self, context):
        '''Update the drawing'''

        all_segments = []
        for polyline in self.polylines:
            # Iterate through each point in the polyline except the last oneA
            for i in range(len(polyline) - 1):
                # Create a segment from the current point to the next
                segment = (polyline[i], polyline[i+1])
                all_segments.append(segment)

        theme = addon.pref().theme.ops.mesh.project.circle
        color = theme.line
        if self.cut_through:
            color = list(color)
            color[3] /= 2
        self._callback_line.update_batch(all_segments, color=color)
        color = theme.guid
        self.guid = [(self.median, view3d.region_2d_to_location_3d(context.region, context.space_data.region_3d, self.mouse_pos, self.median))]
        self._callback_guid.update_batch(self.guid, color=color)

    def setup_drawing(self, context, points=None):
        '''Setup the drawing'''

        theme = addon.pref().theme.ops.mesh.project.circle

        points = points or [(Vector((0, 0, 0)), Vector((0, 0, 0)))]
        color = theme.line
        if self.cut_through:
            color = list(color)
            color[3] /= 2
        self._callback_line = DrawPolyline(points, width=2.0, color=color)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

        color = theme.guid
        self._callback_guid = DrawPolyline(points, width=1.2, color=color)
        self._handle_guid = bpy.types.SpaceView3D.draw_handler_add(self._callback_guid.draw, (context,), 'WINDOW', 'POST_VIEW')

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar hotkeys'''

        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text=f'Adjust {"Radius" if not self.rotating else "Angle"}')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_MMB')
        row.label(text='Segments')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_F')
        row.label(text='Fit Segments')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_G')
        row.label(text='Move Circle')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_ALT')
        row.label(text=rf'Cut Through:{_event.alt}')
        if not self.moving:
            row.separator(factor=12.0)
            row.label(text='', icon='EVENT_SHIFT')
            row.label(text='Rotate Circle')


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Project Circle Line", description="Line color", default=(0.5, 0.4, 0.8, 1.0), subtype='COLOR', size=4, min=0.0, max=1.0)
        guid: bpy.props.FloatVectorProperty(name="Project Circle Guide", description="Guide color", default=(0.0, 0.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    types.theme,
)
