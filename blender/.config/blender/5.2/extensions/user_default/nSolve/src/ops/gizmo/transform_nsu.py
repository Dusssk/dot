import bpy
from mathutils import Vector
from ..utils import infobar
from ....utils import addon


class NSOLVE_OT_TransformNsuGizmo(bpy.types.Operator):
    bl_idname = "nsolve.transform_nsu_gizmo"
    bl_label = "Move nSuite Gizmo"
    bl_description = "Move the nSuite gizmo in 3D space"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    gizmo_index: bpy.props.IntProperty(
        name="Gizmo Index",
        description="Index of the gizmo to transform",
        default=0
    )

    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Mode",
        items=[
            ('TRANSLATE', 'Translate', 'Translate the gizmo'),
            ('SCALE', 'Scale', 'Scale the gizmo')
        ],
        default='TRANSLATE'
    )

    start_mouse_pos: Vector = Vector()
    start_gizmo_pos: Vector = Vector()
    start_gizmo_scale: int = 1

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def invoke(self, context, event):
        self.start_mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        area_width = context.region.width
        area_height = context.region.height

        props = addon.pref().tools.nsuite
        if len(props.nsu_gizmos_items) <= self.gizmo_index:
            return {'CANCELLED'}

        gizmo = props.nsu_gizmos_items[self.gizmo_index]
        self.start_gizmo_pos = Vector((
            (gizmo.location[0] / 100.0) * area_width,
            (gizmo.location[1] / 100.0) * area_height
        ))
        self.start_gizmo_scale = gizmo.scale

        infobar.draw(context, event, self.infobar_hotkeys, blank=True)

        # Start in translate mode by default
        self.mode = 'TRANSLATE'
        context.area.header_text_set('Transform Gizmo (Translate)')
        context.window.cursor_set('SCROLL_XY')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            if self.mode == 'TRANSLATE':
                self.set_gizmo_location(context, mouse_pos)
            elif self.mode == 'SCALE':
                self.set_gizmo_scale(context, mouse_pos)
            context.area.tag_redraw()

        elif event.type == 'LEFTMOUSE':
            self.end(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.end(context)
            return {'CANCELLED'}

        elif event.type == 'G' and event.value == 'PRESS':
            self.mode = 'TRANSLATE'
            context.area.header_text_set('Transform Gizmo (Translate)')

        elif event.type == 'S' and event.value == 'PRESS':
            self.mode = 'SCALE'
            context.area.header_text_set('Transform Gizmo (Scale)')

        elif event.type == 'F' and event.value == 'PRESS':
            props = addon.pref().tools.nsuite
            if len(props.nsu_gizmos_items) > self.gizmo_index:
                gizmo = props.nsu_gizmos_items[self.gizmo_index]
                gizmo.flip = not gizmo.flip
                context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def set_gizmo_location(self, context, mouse_pos):
        delta = mouse_pos - self.start_mouse_pos
        location = self.start_gizmo_pos + delta

        width = context.region.width
        height = context.region.height

        # Clamp the location to within the region boundaries
        location[0] = max(25, min(width - 25, location[0]))
        location[1] = max(50, min(height - 25, location[1]))

        # Calculate percentage positions
        x_percentage = (location[0] / width) * 100
        y_percentage = (location[1] / height) * 100

        nsuite = addon.pref().tools.nsuite
        if len(nsuite.nsu_gizmos_items) > self.gizmo_index:
            gizmo = nsuite.nsu_gizmos_items[self.gizmo_index]
            gizmo.location = Vector((x_percentage, y_percentage))

    def set_gizmo_scale(self, context, mouse_pos):
        delta = mouse_pos - self.start_mouse_pos
        scale_change = delta.x * 0.1  # Change this multiplier to adjust sensitivity
        new_scale = int(self.start_gizmo_scale + scale_change)

        # Clamp the scale between 8 and 256
        new_scale = max(8, min(256, new_scale))

        nsuite = addon.pref().tools.nsuite
        if len(nsuite.nsu_gizmos_items) > self.gizmo_index:
            gizmo = nsuite.nsu_gizmos_items[self.gizmo_index]
            gizmo.scale = new_scale

    def end(self, context):
        '''Clean up.'''
        infobar.remove(context)
        context.area.header_text_set(text=None)
        context.window.cursor_set('CROSSHAIR')

    def infobar_hotkeys(self, layout, _context, _event):
        '''Draw the infobar with the hotkeys.'''
        row = layout.row(align=True)
        row.label(text='', icon='MOUSE_MOVE')
        row.label(text='Move / Scale Gizmo')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_LMB')
        row.label(text='Confirm')
        row.separator(factor=12.0)
        row.label(text='', icon='MOUSE_RMB')
        row.label(text='Cancel')
        row.separator(factor=12.0)
        row.label(text='G')
        row.label(text='Translate')
        row.separator(factor=12.0)
        row.label(text='S')
        row.label(text='Scale')
        row.separator(factor=12.0)
        row.label(text='F')
        row.label(text='Flip')
