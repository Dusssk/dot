from gc import enable
import bpy
import blf
import time
from ....utils.region import fixed_width
from ....utils import addon
from .ui_manager import UIManager
from ....fonts import get_font_path


class NSOLVE_OT_InterfaceText(bpy.types.Operator):
    bl_idname = "nsolve.fading_text"
    bl_label = "Fading Text"
    bl_description = "Display fading text in the viewport"
    bl_options = {'INTERNAL'}

    text: bpy.props.StringProperty(
        name="Text",
        description="Text to display",
        default=""
    )

    position: bpy.props.FloatVectorProperty(
        name="Position",
        description="Position for the text in percentage (0-100 for both x and y)",
        size=2,
        default=(100.0, 0.0),  # Default to bottom right
        min=0.0,
        max=100.0,
        subtype='XYZ'
    )

    size: bpy.props.IntProperty(
        name="Size",
        description="Custom text size (0 to use default size)",
        default=0,
        min=0
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handle = None
        self._timer = None
        self.start_time = 0

        self.opacity = 0.0
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.text_margin = 0.0
        self.line_length = 0.0

    def register_handler(self, context):
        """Register the draw handler"""
        if self._handle is None:
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback,
                (context,),
                'WINDOW',
                'POST_PIXEL'
            )

    def unregister_handler(self, context):
        """Remove the draw handler"""
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None

    def ease_in_out_cubic(self, x):
        """Cubic easing function for smooth animation"""
        if x < 0.5:
            return 4 * x * x * x
        else:
            return 1 - pow(-2 * x + 2, 3) / 2

    def ease_in_out_quad(self, x):
        """Quadratic easing function for smooth animation"""
        if x < 0.5:
            return 2 * x * x
        else:
            return 1 - pow(-2 * x + 2, 2) / 2

    def draw_callback(self, context):
        """Draw text with fade and slide animation"""
        # Get interface options
        nsolve_prefs = addon.pref().tools.nsolve
        interface_options = nsolve_prefs.InterfaceOptions

        enable_animation = interface_options.enable_animation

        # Get animation timing from interface options
        text_duration = interface_options.text_duration
        in_time = interface_options.text_in_time * text_duration
        hold_time = text_duration - (interface_options.text_in_time + interface_options.text_out_time) * text_duration
        out_time = interface_options.text_out_time * text_duration

        # Calculate elapsed time and animation progress
        elapsed = time.time() - self.start_time

        # Calculate opacity and position based on animation phase
        self.opacity = 1.0
        self.x_offset = 0

        if enable_animation:
            if elapsed <= in_time:
                # Fade and slide in with smooth easing
                progress = elapsed / in_time
                eased_progress = self.ease_in_out_cubic(progress)
                self.opacity = eased_progress
                self.x_offset = 100 * (1 - self.ease_in_out_quad(progress))
            elif elapsed <= in_time + hold_time:
                # Hold position
                self.opacity = 1.0
                self.x_offset = 0
            else:
                # Fade and slide out phase
                progress = (elapsed - (in_time + hold_time)) / out_time
                eased_progress = self.ease_in_out_cubic(progress)
                self.opacity = 1.0 - eased_progress
                self.x_offset = -100 * self.ease_in_out_quad(progress)

        if self.opacity <= 0:
            return

        # Get proper DPI factor matching handlers.py
        ui_scale = bpy.context.preferences.view.ui_scale
        pixel_scale = bpy.context.preferences.system.pixel_size
        dpi_factor = ui_scale * pixel_scale

        # Setup text properties
        font_id = 0  # Default font ID
        if interface_options.custom_font:
            font_id = blf.load(get_font_path(interface_options.font_type))
        text_size = self.size if self.size > 0 else interface_options.text_size
        text_size = int(text_size * dpi_factor)

        # Calculate position
        region = bpy.context.region
        area_width = region.width
        area_height = region.height
        left_fix, right_fix = fixed_width(bpy.context)
        usable_width = area_width - left_fix - right_fix

        # Match handlers.py text positioning
        text_margin = 30 * dpi_factor
        line_length = interface_options.animation_line_length * dpi_factor
        margin = interface_options.margin * dpi_factor

        # Calculate text position similar to handlers.py
        right_x = left_fix + usable_width - margin
        bottom_y = margin
        text_x = right_x - line_length - text_margin - blf.dimensions(font_id, self.text)[0]
        text_y = bottom_y - (25 * dpi_factor)  # Position below main text like operator text

        # Draw text with shadow
        blf.size(font_id, text_size)
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0, 0, 0, self.opacity)
        blf.shadow_offset(font_id, int(1 * dpi_factor), int(-1 * dpi_factor))
        blf.color(font_id, 1, 1, 1, 0.8 * self.opacity)
        blf.position(font_id, text_x + self.x_offset, text_y, 0)
        blf.draw(font_id, self.text)

    def modal(self, context, event):
        if not context.area: return {'CANCELLED'}

        if event.type == 'TIMER':
            context.area.tag_redraw()

            # Get animation duration from interface options
            nsolve_prefs = addon.pref().tools.nsolve
            interface_options = nsolve_prefs.InterfaceOptions
            duration = interface_options.text_duration

            # Check if animation is complete
            if time.time() - self.start_time > duration:
                self.unregister_handler(context)
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        interface_options = addon.pref().tools.nsolve.InterfaceOptions
        if not interface_options.show_interface:
            return {'CANCELLED'}

        UIManager.set_active_text(self)

        self.register_handler(context)
        self._timer = context.window_manager.event_timer_add(0.0166, window=context.window)
        self.start_time = time.time()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self.unregister_handler(context)
        UIManager.clear_active_text(self)
