import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector

from ...draw.line import DrawLine
from ...draw.polyline_dotted import DrawPolylineDotted
from ...draw.gradient import DrawGradient

from ..utils import infobar
from ....utils import view3d, addon

from ... import analytics


class NSOLVE_OT_MeshCut(bpy.types.Operator):
    bl_idname = "nsolve.mesh_cut"
    bl_label = "Mesh Cut"
    bl_description = f"{bl_label}\n\nCut the mesh"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR'}

    start_mouse_pos: Vector = Vector((0.0, 0.0))
    mouse_pos: Vector = Vector((0.0, 0.0))

    mode: bpy.props.EnumProperty(name="Mode", items=[('CUT', 'Cut', 'Cut'), ('SLICE', 'Slice', 'Slice')], default='CUT')
    move: bpy.props.FloatProperty(name="Move", description="Offset form selected edge center", default=0.0, step=1, precision=4, subtype='DISTANCE')

    init: bool = False
    continuous: bool = False

    flip: bpy.props.BoolProperty(
        name="Flip",
        description="Flip the cut direction",
        default=False)

    _callback_dotted_line: DrawPolylineDotted
    _handle_dotted_line: int
    _callback_line: DrawLine
    _handle_line: int
    _callback_gradient: DrawGradient
    _handle_gradient: int

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, 'move')

    def invoke(self, context, event):

        bpy.ops.ed.undo_push()

        nsuite = addon.pref().tools.nsuite
        self.continuous = nsuite.continuous_cut

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)
        text = 'Mesh Cut' if self.mode == 'CUT' else 'Mesh Slice'
        context.area.header_text_set(text)
        context.window.cursor_set('SCROLL_XY')
        self.setup_drawing(context)

        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"{text}", position=(50, 2))
        analytics.stats("nSuite: Cut")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()

        # Draw fading text
        if event.type == 'MOUSEMOVE':

            if not self.init:
                self.move = 0.0
                self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

            else:
                self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

                use_snap = context.scene.tool_settings.use_snap or event.ctrl
                if use_snap:
                    if event.shift:
                        self.mouse_pos = self.snap(context, precision=True)
                    else:
                        self.mouse_pos = self.snap(context)

                self.update_drawing(context)
                context.area.tag_redraw()

        elif event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}

        elif event.type == 'F' and event.value == 'PRESS':
            self.flip = not self.flip
            context.area.tag_redraw()
            self.update_drawing(context)
            return {'RUNNING_MODAL'}

        elif event.type == 'X' and event.value == 'PRESS':
            if self.mode == 'SLICE':
                self.mode = 'CUT'
                context.area.header_text_set('Mesh Cut')

            else:
                self.mode = 'SLICE'
                context.area.header_text_set('Mesh Slice')
            self.update_drawing(context)
            context.area.tag_redraw()

        elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            return {'PASS_THROUGH'}

        elif event.type == 'LEFTMOUSE':
            if not self.init:
                if event.value == 'PRESS':
                    self.init = True
                    return {'RUNNING_MODAL'}
            else:
                self.execute(context)
                bpy.ops.ed.undo_push()

                if not self.continuous:
                    self.end(context)
                    return {'FINISHED'}

                self.init = False
                self._callback_gradient.update_batch(points=[(0, 0), (0, 0), (0, 0), (0, 0)])
                self._callback_line.update_batch(points=(Vector((0, 0, 0)), Vector((0, 0, 0))))
                self._callback_dotted_line.update_batch(points=(Vector((0, 0, 0)), Vector((0, 0, 0))))
                context.area.tag_redraw()

        elif event.type in {'RIGHTMOUSE', 'ESC', 'SPACE', 'RET'}:
            self.end(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def snap(self, context, precision=False):

        angle_increment = math.radians(15)
        if precision:
            angle_increment = math.radians(5)

        # Calculate the 2D angle from initial to current mouse position
        angle = math.atan2(self.mouse_pos[1] - self.start_mouse_pos[1], self.mouse_pos[0] - self.start_mouse_pos[0])
        snap_angle_rad = angle_increment
        snapped_angle = round(angle / snap_angle_rad) * snap_angle_rad

        # Calculate the distance to maintain from start to current position
        distance = (self.mouse_pos - self.start_mouse_pos).length

        # Create a direction vector from the snapped angle
        direction = Vector((math.cos(snapped_angle), math.sin(snapped_angle)))

        # Update current mouse position in 2D based on the snapped direction and original distance
        snaped_mouse_pos = self.start_mouse_pos + direction * distance

        return snaped_mouse_pos

    def end(self, context):
        '''Clean up.'''

        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

        bpy.types.SpaceView3D.draw_handler_remove(self._handle_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_dotted_line, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle_gradient, 'WINDOW')
        context.area.tag_redraw()

    def setup_drawing(self, context):
        '''Setup the drawing for the line'''

        theme = addon.pref().theme.ops.mesh.cut

        start_pos, end_pos = Vector((0, 0)), Vector((0, 0))
        dotted_color = theme.guid
        self._callback_dotted_line = DrawPolylineDotted([start_pos, end_pos], width=1.4, color=dotted_color)
        self._handle_dotted_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_dotted_line.draw, (context,), 'WINDOW', 'POST_PIXEL')

        start_pos, end_pos = Vector((0, 0, 0)), Vector((0, 0, 0))
        color = theme.line if self.mode == 'CUT' else theme.slice_line
        self._callback_line = DrawLine((start_pos, end_pos), width=1.6, color=color, depth=True)
        self._handle_line = bpy.types.SpaceView3D.draw_handler_add(self._callback_line.draw, (context,), 'WINDOW', 'POST_VIEW')

        new_points = [(0, 0), (0, 0), (0, 0), (0, 0)]  # New corner points for the rectangle
        gradient_color = theme.gradient if self.mode == 'CUT' else theme.slice_gradient
        new_colors = [gradient_color, gradient_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)]  # New colors
        self._callback_gradient = DrawGradient(new_points, new_colors)
        self._handle_gradient = bpy.types.SpaceView3D.draw_handler_add(self._callback_gradient.draw, (context,), 'WINDOW', 'POST_PIXEL')

    def update_drawing(self, context):
        '''Update the drawing for the line'''

        if not self.init: return

        region = context.region
        region_data = context.space_data.region_3d

        obj = context.edit_object
        obj.update_from_editmode()
        center_point = bbox_center(obj)  # or center_of_mass(obj)
        largest_dimension = get_largest_dimension(obj)

        # Calculate the view normal
        view_normal = region_data.view_rotation @ Vector((0.0, 0.0, -1.0))

        # Offset along the view normal based on the largest object dimension
        offset = view_normal * largest_dimension

        # Calculate the points in 3D space, offset from the object location
        point1 = view3d.region_2d_to_location_3d(region, region_data, self.start_mouse_pos, center_point + offset)
        point2 = view3d.region_2d_to_location_3d(region, region_data, self.mouse_pos, center_point + offset)

        theme = addon.pref().theme.ops.mesh.cut

        dotted_color = theme.guid
        self._callback_dotted_line.update_batch((self.start_mouse_pos, self.mouse_pos), dotted_color)
        color = theme.line if self.mode == 'CUT' else theme.slice_line
        self._callback_line.update_batch((point1, point2), color)

        perp_distance = 250
        direction = (self.mouse_pos - self.start_mouse_pos).normalized()
        if self.flip:
            perp_vector = Vector((direction.y, -direction.x))  # Flip direction
        else:
            perp_vector = Vector((-direction.y, direction.x))  # Original direction
        point3 = self.mouse_pos + perp_vector * perp_distance
        point4 = self.start_mouse_pos + perp_vector * perp_distance
        new_points = [self.start_mouse_pos, self.mouse_pos, point3, point4]
        gradient_color = theme.gradient if self.mode == 'CUT' else theme.slice_gradient
        colors = [gradient_color, gradient_color, (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)]  # New colors
        self._callback_gradient.update_batch(points=new_points, colors=colors)

    def execute(self, context):
        region = context.region
        region_data = context.space_data.region_3d

        obj = context.edit_object
        obj.update_from_editmode()
        center_point = bbox_center(obj)  # or center_of_mass(obj)

        # Calculate the 3D space position of the start and current mouse positions
        point1 = view3d.region_2d_to_location_3d(region, region_data, self.start_mouse_pos, center_point)
        point2 = view3d.region_2d_to_location_3d(region, region_data, self.mouse_pos, center_point)

        # Calculate the tangent vector from point1 to point2
        tangent = (point2 - point1).normalized()

        view_direction = view3d.region_2d_to_vector_3d(region, region_data, self.start_mouse_pos)

        # The plane's normal is the cross product of the tangent and the view direction
        plane_no_global = tangent.cross(view_direction).normalized()

        # Proceed with bisecting using the calculated plane coordinates in local space
        selected = context.selected_objects
        for obj in selected:
            if obj.type != 'MESH':
                continue

            # Convert global coordinates to the object's local space
            plane_no_local = obj.matrix_world.transposed() @ plane_no_global
            plane_no_local.normalize

            move_vector = plane_no_local * self.move
            plane_co_local = (obj.matrix_world.inverted() @ point1) + move_vector

            if self.mode == 'CUT':
                self.bisect_mesh_with_plane(obj, plane_co_local, plane_no_local, self.flip)
            else:
                self.slice_mesh_with_plane(obj, plane_co_local, plane_no_local)

        return {'FINISHED'}

    def slice_mesh_with_plane(self, obj, plane_co, plane_no):
        '''Slice the mesh with the given plane, retaining both sides.'''

        bm = bmesh.from_edit_mesh(obj.data)

        # Step 1: Bisect without clearing any geometry
        result = bmesh.ops.bisect_plane(
            bm,
            geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
            plane_co=plane_co,
            plane_no=plane_no,
            clear_outer=False,
            clear_inner=False
        )

        # Ensure the new geometry from the bisect is properly updated
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=False)

        # Step 2: Use the "geom_cut" to find the boundary edges created by the bisect
        split_edges = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]

        # Step 3: Split the mesh along the bisect edges
        bmesh.ops.split_edges(bm, edges=split_edges)

        # Refresh the bmesh to account for new topology changes
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # Step 4: Fill the open boundaries created by the split to form two separate closed meshes
        fill_edges = [e for e in bm.edges if e.is_boundary]
        bmesh.ops.edgeloop_fill(bm, edges=fill_edges)

        # Finalize the update
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

    def bisect_mesh_with_plane(self, obj, plane_co, plane_no, flip):
        '''Bisect the mesh with the given plane.'''

        bm = bmesh.from_edit_mesh(obj.data)

        if flip:
            plane_no = -plane_no

        geom_cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=plane_co, plane_no=plane_no, clear_outer=True, clear_inner=False)
        for geom in geom_cut['geom_cut']:
            geom.select = True

        bmesh.ops.contextual_create(bm, geom=geom_cut['geom_cut'], mat_nr=0)

        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

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
        row.label(text='', icon='EVENT_F')
        row.label(text='Flip Direction')
        row.separator(factor=12.0)
        row.label(text='', icon='EVENT_X')
        row.label(text='Change Mode')


def get_largest_dimension(obj):
    '''Return the largest dimension of the object.'''

    dimensions = obj.dimensions
    return max(dimensions.x, dimensions.y, dimensions.z)


def bbox_center(obj):
    local_bbox_center = 0.125 * sum((Vector(b) for b in obj.bound_box), Vector())
    global_bbox_center = obj.matrix_world @ local_bbox_center
    return global_bbox_center


class types():
    class theme(bpy.types.PropertyGroup):
        line: bpy.props.FloatVectorProperty(name="Cut", description="Cut Line color", default=(1.0, 0.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        slice_line: bpy.props.FloatVectorProperty(name="Slice", description="Slice Line color", default=(1.0, 1.0, 0.0, 0.8), subtype='COLOR', size=4, min=0.0, max=1.0)
        guid: bpy.props.FloatVectorProperty(name="Cut Guide", description="Guide color", default=(0.0, 0.0, 0.0, 0.7), subtype='COLOR', size=4, min=0.0, max=1.0)
        gradient: bpy.props.FloatVectorProperty(name="Cut Gradient ", description="Cut Gradient color", default=(1.0, 0.0, 0.0, 0.15), subtype='COLOR', size=4, min=0.0, max=1.0)
        slice_gradient: bpy.props.FloatVectorProperty(name="Slice Gradient", description="Slice gradient color", default=(1.0, 1.0, 0.0, 0.15), subtype='COLOR', size=4, min=0.0, max=1.0)


types_classes = (
    types.theme,
)
