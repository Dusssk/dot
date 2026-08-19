import bpy
import blf
import gpu
import time
from gpu_extras.batch import batch_for_shader
from ....utils.region import fixed_width
from ....utils import addon
from .ui_manager import UIManager
from ....fonts import get_font_path


class NSOLVE_OT_InterfaceHeader(bpy.types.Operator):
    bl_idname = "nsolve.interface_header"
    bl_label = "Interface Header"
    bl_description = "Display animated header interface in the viewport"
    bl_options = {'INTERNAL'}

    text: bpy.props.StringProperty(
        name="Text",
        description="Text content in format 'header|line1|line2'",
        default=""
    )

    position: bpy.props.FloatVectorProperty(
        name="Position",
        description="Position for the interface in percentage (0-100 for both x and y)",
        size=2,
        default=(50.0, 50.0),
        min=0.0,
        max=100.0,
        subtype='XYZ'
    )

    color: bpy.props.FloatVectorProperty(
        name="Color",
        description="Color for the interface",
        size=4,
        default=(0.0, 0.0, 0.0, 0.0),
        min=0.0,
        max=1.0,
        subtype='COLOR'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._handle = None
        self._timer = None
        self.start_time = 0
        
        self.lines = []
        self.header = ""
        self.alpha = 0.0

        # Animation offsets
        self.corner_h_offset = 0
        self.corner_v_offset = 0
        self.header_offset = -100
        self.separator_offset = -100
        self.text_offset = 100
        
        # Box dimensions
        self.box_width = 0
        self.box_height = 0
        self.corner_size = 32

    def parse_text(self):
        """Parse the text input into header and lines"""
        parts = self.text.split('|')
        self.header = parts[0] if parts else ""
        self.lines = parts[1:] if len(parts) > 1 else []

    def calculate_box_dimensions(self, context, font_id, header_size, text_size):
        """Calculate box dimensions based on text content"""
        # Get header text width
        blf.size(font_id, header_size)
        header_width = blf.dimensions(font_id, self.header)[0]
        
        max_width = header_width
        
        # Calculate text lines width with line text size
        blf.size(font_id, text_size)
        for line in self.lines:
            width = blf.dimensions(font_id, line)[0]
            max_width = max(max_width, width)
        
        # Add padding with respect to text sizes
        self.box_width = max_width + self.corner_size * 4
        
        # Calculate height based on text sizes
        # Header section height + spacing + lines section height
        header_section = header_size + self.corner_size
        line_spacing = text_size * 2
        lines_section = (len(self.lines) * line_spacing) if self.lines else 0
        self.box_height = header_section + self.corner_size + lines_section + self.corner_size

    def draw_line(self, shader, x1, y1, x2, y2, color):
        """Draw a line using GPU shader"""
        vertices = ((x1, y1), (x2, y2))
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices})

        shader.uniform_float("color", color)
        batch.draw(shader)

    def draw_corner(self, shader, x, y, is_top_right, color, h_offset, v_offset):
        """Draw a corner with animation"""
        size = self.corner_size
        if is_top_right:
            # Top right corner - lines extend left and down
            x1 = x
            y1 = y
            
            # Horizontal line sliding from right to left
            x2 = x - (size - h_offset if h_offset > 0 else size + h_offset)
            self.draw_line(shader, x1, y1, x2, y1, color)
            
            # Vertical line sliding from top to bottom
            y2 = y - (size - v_offset if v_offset > 0 else size + v_offset)
            self.draw_line(shader, x1, y1, x1, y2, color)
        else:
            # Bottom left corner - lines extend right and up
            x1 = x
            y1 = y
            
            # Horizontal line sliding from left to right
            x2 = x + (size - h_offset if h_offset > 0 else size + h_offset)
            self.draw_line(shader, x1, y1, x2, y1, color)
            
            # Vertical line sliding from bottom to top
            y2 = y + (size - v_offset if v_offset > 0 else size + v_offset)
            self.draw_line(shader, x1, y1, x1, y2, color)

    def draw_callback(self, context):
        """Draw interface with animations"""
        # Get interface options
        nsolve_prefs = addon.pref().tools.nsolve
        interface_options = nsolve_prefs.InterfaceOptions

        enable_header_animation = interface_options.enable_header_animation
        
        # Get animation timing from interface options
        header_duration = interface_options.header_duration
        header_in_time = interface_options.header_in_time
        header_out_time = interface_options.header_out_time
        header_headertext_size = interface_options.header_headertext_size
        header_linetext_size = interface_options.header_linetext_size
        header_line_width = interface_options.header_line_width

        # Calculate animation progress
        elapsed = time.time() - self.start_time
        
        # Calculate alpha and offsets based on animation phase

        self.alpha = 1.0
        self.corner_h_offset = 0
        self.corner_v_offset = 0
        self.header_offset = 0
        self.separator_offset = 0
        self.text_offset = 0

        if enable_header_animation:
            if elapsed < header_in_time:
                # Fade in phase
                progress = elapsed / header_in_time
                self.alpha = progress
                self.corner_h_offset = self.corner_size * (1 - progress)
                self.corner_v_offset = self.corner_size * (1 - progress)
                self.header_offset = -100 * (1 - progress)
                self.separator_offset = -100 * (1 - progress)
                self.text_offset = 100 * (1 - progress)
            elif elapsed > (header_duration - header_out_time):
                # Fade out phase
                progress = (elapsed - (header_duration - header_out_time)) / header_out_time
                self.alpha = 1.0 - progress
                self.corner_h_offset = -self.corner_size * progress
                self.corner_v_offset = -self.corner_size * progress
                self.header_offset = 100 * progress
                self.separator_offset = 100 * progress
                self.text_offset = -100 * progress
            else:
                # Fully visible phase
                self.alpha = 1.0
                self.corner_h_offset = 0
                self.corner_v_offset = 0
                self.header_offset = 0
                self.separator_offset = 0
                self.text_offset = 0

        if self.alpha <= 0:
            return

        # Get interface options and scaling factors
        ui_scale = context.preferences.view.ui_scale
        pixel_scale = context.preferences.system.pixel_size
        dpi_factor = ui_scale * pixel_scale

        # Setup region dimensions and offsets
        region = context.region
        area_width = region.width
        area_height = region.height
        left_fix, right_fix = fixed_width(context)
        usable_width = area_width - left_fix - right_fix

        # Calculate base position
        font_id = 0  # Default font ID
        if interface_options.custom_font:
            font_id = blf.load(get_font_path(interface_options.font_type))
        header_size = int(header_headertext_size * dpi_factor)
        text_size = int(header_linetext_size * dpi_factor)
        line_width = header_line_width * dpi_factor

        # Calculate box dimensions with different text sizes
        self.calculate_box_dimensions(context, font_id, header_size, text_size)

        # Calculate center position
        x_base = left_fix + (usable_width * (self.position[0] / 100.0))
        y_base = area_height * (self.position[1] / 100.0)
    
        # Adjust base position to account for box dimensions
        x_base -= self.box_width / 2
        y_base += self.box_height / 2

        # Setup shader
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        # Draw settings
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(line_width)

        shader.bind()

        # Draw corners


        line_color = (0.8, 0.8, 0.8, 0.8 * self.alpha)

        self.draw_corner(shader, x_base, y_base, False, line_color, 
                        self.corner_h_offset, self.corner_v_offset)  # Bottom left
        self.draw_corner(shader, x_base + self.box_width, y_base + self.box_height, 
                        True, line_color, self.corner_h_offset, self.corner_v_offset)  # Top right

        # Draw header with header text size
        blf.size(font_id, header_size)
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0, 0, 0, self.alpha)
        blf.shadow_offset(font_id, int(1 * dpi_factor), int(-1 * dpi_factor))
        blf.color(font_id, 0.9, 0.9, 0.9, 0.8 * self.alpha)
        header_x = x_base + self.corner_size * 2 + self.header_offset
        header_y = y_base + self.box_height - self.corner_size - header_size/2
        blf.position(font_id, header_x, header_y, 0)
        blf.draw(font_id, self.header)

        # Draw separator line with custom line width
        separator_y = y_base + self.box_height - (self.corner_size * 2 + header_size/2)
        gpu.state.line_width_set(line_width)

        if self.color[3] > 0.0:
            line_color = self.color

        self.draw_line(
            shader,
            x_base + self.corner_size + self.separator_offset, separator_y,
            x_base + self.box_width - self.corner_size, separator_y,
            line_color
        )

        # Draw text lines with line text size and proper spacing
        blf.size(font_id, text_size)
        line_spacing = text_size * 2  # 20% extra space between lines
        for i, line in enumerate(self.lines):
            text_y = separator_y - (line_spacing * (i + 1))
            text_x = x_base + self.corner_size * 2 + self.text_offset
            blf.position(font_id, text_x, text_y, 0)
            blf.draw(font_id, line)

        # Reset Draw settings
        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1)

    def modal(self, context, event):
        if event.type == 'TIMER':
            context.area.tag_redraw()

            # Get animation duration from interface options
            nsolve_prefs = addon.pref().tools.nsolve
            interface_options = nsolve_prefs.InterfaceOptions
            total_duration = interface_options.header_duration

            # Check if animation is complete
            current_time = time.time() - self.start_time
            if current_time > total_duration:
                self.unregister_handler(context)
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        interface_options = addon.pref().tools.nsolve.InterfaceOptions
        if not interface_options.show_header:
            return {'CANCELLED'}

        if self._handle is not None:
            self.unregister_handler(context)

        UIManager.set_active_header(self)
        self.parse_text()

        self.register_handler(context)
        self._timer = context.window_manager.event_timer_add(0.0166, window=context.window)
        self.start_time = time.time()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._handle is not None:
            self.unregister_handler(context)
        UIManager.clear_active_header(self)

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


classes = (
    NSOLVE_OT_InterfaceHeader,
)
