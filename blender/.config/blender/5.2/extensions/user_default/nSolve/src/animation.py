import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
import blf
import time
import math
from ..utils.region import fixed_width
from ..utils import addon
from ..fonts import get_font_path


class AnimationState:
    """Class to manage animation state"""
    def __init__(self):
        self.last_tool = None
        self.last_operator = None
        self.animation_start = 0
        self.banner_start = 0
        self.is_animating = False
        self.animate_banner = False

        # Corner animation state
        self.corners_done = False

        # Base/operator text animation state
        self.operator_opacity = 0.0
        self.operator_start_time = 0
        self.operator_x_offset = 0.0

        # Main text animation state
        self.main_text_x_offset = -70.0  # Starting offset for main text
        self.main_text_opacity = 0.0
        self.main_text_start_time = 0  # Track when main text animation starts
        self.should_animate_text = False  # Flag to control text animation
        self.main_text_delay = 0.0  # Delay before starting main text animation

        # Gizmo text animation state
        self.gizmo_text_opacity = 0.0
        self.gizmo_text_y_offset = 0.0
        self.gizmo_text_start_time = 0
        self.should_animate_gizmo_text = False


class ViewportHandlers:
    """Class to manage viewport handlers and drawing"""
    def __init__(self):
        self.corner_draw_handler = None
        self.gizmo_draw_handler = None
        self.timer_handler = None
        self.state = AnimationState()

    # List of modal operators that should hide the text
    hide_text_modals = (
        'NSOLVE_OT_project_mesh',
    )

    nsolve_modals = {
        'VIEW3D_OT_select_box': 'SELECT',
        'NSOLVE_OT_join_verts': 'JOIN',
        'NSOLVE_OT_merge_verts': 'MERGE',
        'TRANSFORM_OT_edge_slide': 'SLIDE',
        'TRANSFORM_OT_vert_slide': 'SLIDE',
        'NSOLVE_OT_project_line': 'LINE',
        'NSOLVE_OT_collapse_verts': 'COLLAPSE',
        'NSOLVE_OT_dissolve_edges': 'DISSOLVE',
        'NSOLVE_OT_offset_edges': 'OFFSET',
        'MESH_OT_knife_tool': 'KNIFE',

        #nsuite gizmo modals
        'NSOLVE_OT_hard_loop_cut' : 'HARD LOOP CUT',
        'MESH_OT_loopcut_slide' : 'MESH LOOP CUT',
        'NSOLVE_OT_hard_edge_slide' : 'HARD EDGE SLIDE',
        'NSOLVE_OT_bevel' : 'HARD BEVEL',
        'NSOLVE_OT_mesh_cut' : 'MESH CUT',
        'NSOLVE_OT_project_loop' : 'PROJECT LOOP',
        'NSOLVE_OT_project_circle' : 'PROJECT CIRCLE',
        'NSOLVE_OT_project_grid' : 'PROJECT GRID',
        'NSOLVE_OT_project_rake' : 'PROJECT RAKE',
        'NSOLVE_OT_hide' : 'HIDE',
    }

    def get_viewport_dimensions(self, context):
        """Calculate viewport dimensions considering panels and headers"""
        # Get the current viewport dimensions and adjust for panels
        region = bpy.context.region
        area_width = region.width
        area_height = region.height

        # Adjust for side panels
        left_fix, right_fix = fixed_width(bpy.context)
        usable_width = area_width - left_fix - right_fix

        # Calculate header heights and alignments
        tool_header_height = 0
        header_height = 0 if not bpy.context.space_data.show_region_header else 20

        tool_header_alignment = 'TOP'
        header_alignment = 'TOP'

        if bpy.context.space_data.show_region_tool_header:
            for region in bpy.context.area.regions:
                if region.type == 'TOOL_HEADER':
                    tool_header_height = region.height
                    tool_header_alignment = region.alignment
                    break

        # Calculate offsets
        top_offset = 0
        bottom_offset = 0

        if tool_header_alignment == 'TOP':
            top_offset += tool_header_height
        else:
            bottom_offset += tool_header_height

        if bpy.context.space_data.show_region_header:
            if header_alignment == 'TOP':
                top_offset += header_height
            else:
                bottom_offset += header_height

        return left_fix, right_fix, usable_width, area_height, top_offset, bottom_offset

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

    def calculate_corner_positions(self, context, interface_options):
        """Calculate corner positions with UI scale and animation"""
        # Get viewport dimensions
        left_fix, right_fix, usable_width, area_height, top_offset, bottom_offset = self.get_viewport_dimensions(context)

        # Calculate UI scale factors
        ui_scale = bpy.context.preferences.view.ui_scale
        pixel_scale = bpy.context.preferences.system.pixel_size
        dpi_factor = ui_scale * pixel_scale

        # Calculate dimensions
        line_length = interface_options.animation_line_length * dpi_factor
        line_width = interface_options.animation_line_width * dpi_factor
        base_margin = interface_options.margin * dpi_factor

        # Calculate animation progress with smooth easing
        animation_progress = min(1.0, (time.time() - self.state.animation_start) / interface_options.animation_duration)
        if animation_progress < 1.0:
            eased_progress = self.ease_in_out_quad(animation_progress)
            animation_factor = math.sin(eased_progress * math.pi * 2) * interface_options.animation_margin
        else:
            animation_factor = 0

        margin = base_margin + (animation_factor * dpi_factor)

        # Calculate positions
        left_x = left_fix + margin
        right_x = left_fix + usable_width - margin
        top_y = area_height - margin - top_offset
        bottom_y = margin + bottom_offset

        return left_x, right_x, top_y, bottom_y, line_length, line_width

    def get_active_tool_info(self):
        """Get active tool information and validate it"""
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        if not active_tool or active_tool.idname not in {'nsolve.nsolvetool', 'nsolve.nsuitetool', 'nsolve.main_tool'}:
            self.state.last_tool = None
            self.state.last_operator = None
            return None, None, None

        nsolve_prefs = addon.pref().tools.nsolve
        current_operator = nsolve_prefs.main.operator if active_tool.idname == 'nsolve.nsolvetool' else None

        return active_tool, nsolve_prefs, current_operator

    def draw_corner_lines(self, corners, line_width, color):
        """Draw L-shaped corner lines"""
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(line_width)

        for line_start, line_end in corners:
            vertices = [Vector(line_start), Vector(line_end)]
            batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
            shader.bind()
            shader.uniform_float("color", color)
            batch.draw(shader)

    def get_tool_color(self, active_tool, interface_color, current_op):
        """Get color based on active tool"""
        if active_tool.idname == 'nsolve.main_tool':
            return interface_color.main_tool
        elif active_tool.idname == 'nsolve.nsolvetool':
            color_map = {
                'SELECT': interface_color.select_color,
                'JOIN': interface_color.join_color,
                'MERGE': interface_color.merge_color,
                'SLIDE': interface_color.slide_color,
                'LINE': interface_color.line_color,
                'COLLAPSE': interface_color.collapse_color,
                'DISSOLVE': interface_color.dissolve_color,
                'OFFSET': interface_color.offset_color,
                'KNIFE': interface_color.knife_color
            }
            return color_map.get(current_op, interface_color.nsolve_tool)
        else:  # nsolve.nsuitetool
            return interface_color.nsuite_tool

    def get_text_content(self, active_tool, nsolve_prefs):
        """Get main and sub text content"""
        if active_tool.idname == 'nsolve.main_tool':
            # Check if there's an active object
            if bpy.context.active_object and bpy.context.active_object.type == 'MESH':
                return "LMB to enter nSolve for active object"
            return "Select a Mesh object"
        elif active_tool.idname == 'nsolve.nsolvetool':
            return nsolve_prefs.main.operator.capitalize()
        else:  # nsolve.nsuitetool
            return ""

    def draw_main_text(self, font_id, main_text, text_x, main_text_y, opacity, dpi_factor):
        """Draw main text with shadow"""
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0, 0, 0, opacity)
        blf.shadow_offset(font_id, int(1 * dpi_factor), int(-1 * dpi_factor))
        blf.color(font_id, 1, 1, 1, 0.8 * opacity)
        blf.position(font_id, text_x, main_text_y, 0)
        blf.draw(font_id, main_text)

    def handle_main_text_animation(self, current_time, font_id, dpi_factor, base_text_x):
        """Handle main text animation state and position"""
        # Check if enough time has passed since animation start (delay)
        animation_elapsed = current_time - self.state.animation_start

        # Only start main text animation after the delay
        if animation_elapsed >= self.state.main_text_delay:
            # Initialize animation when it should start
            if self.state.main_text_start_time == 0:
                self.state.main_text_start_time = current_time
                self.state.main_text_opacity = 0.0
                self.state.main_text_x_offset = -30.0
                self.state.should_animate_text = True

            # Calculate progress based on time since main text animation started
            text_progress = min(1.0, (current_time - self.state.main_text_start_time) / 0.3)
            eased_progress = self.ease_in_out_cubic(text_progress)

            # Update main text animation state
            self.state.main_text_x_offset = -30.0 * (1.0 - eased_progress)
            self.state.main_text_opacity = eased_progress
        else:
            # Before delay time, keep text invisible
            self.state.main_text_opacity = 0.0
            self.state.main_text_x_offset = -30.0
            self.state.main_text_start_time = 0
            self.state.should_animate_text = False

        return base_text_x + self.state.main_text_x_offset, self.state.main_text_opacity

    def handle_gizmo_text_animation(self, current_time, context):
        """Handle gizmo text animation state and position

        Returns:
        opacity: Opacity of the gizmo text
        y_offset: Y offset for animation (moving up from starting position)
        """
        # Start gizmo text animation immediately when animation begins
        if self.state.is_animating:
            # Initialize animation when started
            if self.state.gizmo_text_start_time == 0:
                self.state.gizmo_text_start_time = current_time
                self.state.gizmo_text_opacity = 0.0
                self.state.gizmo_text_y_offset = -20.0
                self.state.should_animate_gizmo_text = True

            # Animation duration of 0.4 seconds
            text_progress = min(1.0, (current_time - self.state.gizmo_text_start_time) / 0.4)
            eased_progress = self.ease_in_out_cubic(text_progress)

            # Animate opacity from 0 to 1 and y offset from -20 to 0
            opacity = eased_progress
            y_offset = -20.0 * (1.0 - eased_progress)

            # Store in state for other uses
            self.state.gizmo_text_opacity = opacity
            self.state.gizmo_text_y_offset = y_offset

            return opacity, y_offset
        elif hasattr(self.state, 'should_animate_gizmo_text') and self.state.should_animate_gizmo_text:
            # If animation has completed but we want to keep showing the gizmo text
            return 1.0, 0.0
        else:
            # Reset animation state if not animating and not showing
            self.state.gizmo_text_opacity = 0.0
            self.state.gizmo_text_y_offset = -20.0
            self.state.gizmo_text_start_time = 0
            self.state.should_animate_gizmo_text = False
            return 0.0, -20.0

    def is_modal_active(self, context):
        """Check if any modal operator is active"""
        # Check if modal_operators attribute exists (for older Blender versions)
        if not hasattr(bpy.context.window, 'modal_operators'):
            return False

        modals = bpy.context.window.modal_operators
        if not modals:
            return False

        for modal in modals:
            if modal.bl_idname in self.hide_text_modals:
                return True

        return False

    def nsolve_modal_name(self):
        """Get name of active modal nsolve operator or None"""
        # Check if modal_operators attribute exists (for older Blender versions)

        res = None
        if not hasattr(bpy.context.window, 'modal_operators'):
            return res

        modals = bpy.context.window.modal_operators

        for modal in modals:
            res = self.nsolve_modals.get(modal.bl_idname, None)
            if res:
                break

        return res

    def draw_gizmo_text_scaled(self, font_id, main_text, center_x, center_y, opacity, dpi_factor, scale):
        """Draw text with shadow, scaled according to gizmo scale

        Parameters:
        center_x, center_y: The center position of the text
        """
        # Save current font size
        current_size = blf.size(font_id, 0)

        # Ensure scale is not None
        if scale is None:
            scale = 32.0  # Default scale if none provided

        # Get text scale from preferences
        try:
            props = addon.pref().tools.nsolve.InterfaceOptions
            # Use gizmo_scale directly as the scale factor
            text_scale = props.gizmo_scale
        except (AttributeError, TypeError):
            text_scale = 3.0  # Default if preference not available

        # Use text_scale directly instead of multiplying with gizmo scale
        base_font_size = 20
        scaled_size = base_font_size * text_scale
        blf.size(font_id, int(scaled_size * dpi_factor))

        # Calculate text dimensions to center it
        text_width, text_height = blf.dimensions(font_id, main_text)

        # Calculate the starting position to center the text
        start_x = center_x - (text_width / 2)
        start_y = center_y - (text_height / 2)

        # Draw text with shadow
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, 0, 0, 0, opacity)
        blf.shadow_offset(font_id, int(1 * dpi_factor), int(-1 * dpi_factor))
        blf.color(font_id, 1, 1, 1, 0.8 * opacity)
        blf.position(font_id, start_x, start_y, 0)
        blf.draw(font_id, main_text)

        # Restore original font size if it's not None
        if current_size is not None:
            blf.size(font_id, current_size)
        else:
            # Set a default size if current_size was None
            blf.size(font_id, 12)

    def draw_gizmo_text(self, context, font_id, main_text, opacity, dpi_factor, current_time):
        """Draw text at the bottom of the nsolve gizmo with animation"""
        # Get animation state for gizmo text
        gizmo_opacity, y_offset = self.handle_gizmo_text_animation(current_time, context)

        # Apply animation opacity
        opacity = opacity * gizmo_opacity

        # If no opacity, don't bother drawing
        if opacity <= 0:
            return

        # Get active tool info
        active_tool, nsolve_prefs, current_operator = self.get_active_tool_info()
        if active_tool is None:
            return

        # Get gizmo properties from preferences
        props = addon.pref().tools.nsolve
        _location = Vector(props.main_gizmo_location)

        # Calculate the position
        region = bpy.context.region
        area_width = region.width
        area_height = region.height

        left_fix, right_fix = fixed_width(bpy.context)
        usable_width = area_width - left_fix - right_fix

        # Calculate the position at the bottom of the gizmo
        gizmo_x = left_fix + (_location.x / 100.0) * usable_width
        gizmo_y = (_location.y / 100.0) * area_height

        # Get gizmo scale and spacing
        scale = props.main_gizmo_scale
        spacing = scale * props.main_gizmo_spacing

        # Get information about the gizmo expansion state
        expand = props.expanded
        flip = props.main_gizmo_flip

        # Calculate the position based on the gizmo layout and expansion state
        text_width = blf.dimensions(font_id, main_text)[0]

        if expand:
            # Count the number of buttons in the expanded gizmo
            main_items = props.main_gizmo_list_items
            num_buttons = len(main_items) + 1  # +1 for the main nSolve button

            if flip:  # Horizontal layout
                # Position text below the last button in the row
                gizmo_text_x = gizmo_x + (num_buttons * (scale + scale * props.main_gizmo_spacing)) + (text_width) + spacing
                gizmo_text_y = gizmo_y

            else:  # Vertical layout
                last_button_y = gizmo_y - ((num_buttons - 1) * (scale + scale * props.main_gizmo_spacing))
                gizmo_text_x = gizmo_x
                gizmo_text_y = last_button_y - scale - spacing * 4  # Extra space below
        else:
            # Only two buttons when not expanded (main button + active operator)
            if flip:  # Horizontal layout
                gizmo_text_x = gizmo_x + (2 *(scale + scale * props.main_gizmo_spacing)) + (text_width) + spacing
                gizmo_text_y = gizmo_y
            else:  # Vertical layout
                last_button_y = gizmo_y - (scale) - (scale * props.main_gizmo_spacing)
                gizmo_text_x = gizmo_x
                gizmo_text_y = last_button_y - scale - spacing * 4  # Extra space below

        # Apply animation y offset
        gizmo_text_y += y_offset * dpi_factor

        # Draw the text at the gizmo location with scaling based on gizmo scale
        self.draw_gizmo_text_scaled(font_id, main_text, gizmo_text_x, gizmo_text_y, opacity, dpi_factor, scale)

    def draw_gizmo(self, context):
        """Draw the gizmo text in the viewport"""
        # Check if gizmo should be drawn
        if not addon.pref().tools.nsolve.InterfaceOptions.gizmo_enabled:
            return

        active_tool, nsolve_prefs, current_operator = self.get_active_tool_info()
        if active_tool is None:
            return

        # Only show text for nsolve.nsolvetool
        if active_tool.idname != 'nsolve.nsolvetool':
            return

        interface_options = nsolve_prefs.InterfaceOptions
        if not interface_options.show_interface:
            return

        # Get current time for animation
        current_time = time.time()

        # Get DPI scale factor
        dpi_factor = bpy.context.preferences.view.ui_scale * bpy.context.preferences.system.pixel_size

        # Setup font
        font_id = 0  # Default font ID
        if interface_options.custom_font:
            font_id = blf.load(get_font_path(interface_options.font_type))

        # Get operator name as the text
        tool_name = current_operator.capitalize() if current_operator else "nSolve"

        # Get name of running nsolve modal
        modal_name = self.nsolve_modal_name()

        if modal_name:
            tool_name = self.modal_draw_name(modal_name)

        # Get animation state
        gizmo_opacity, y_offset = self.handle_gizmo_text_animation(current_time, context)

        # Draw the gizmo text - will be visible even after animation completes
        self.draw_gizmo_text(context, font_id, tool_name, gizmo_opacity, dpi_factor, current_time)

    def draw_corners(self, context):
        """Draw L-shaped corners in the viewport"""
        # Get active tool and preferences
        active_tool, nsolve_prefs, current_operator = self.get_active_tool_info()
        if not active_tool:
            return

        interface_options = nsolve_prefs.InterfaceOptions
        interface_color = nsolve_prefs.InterfaceColor

        modal_name = self.nsolve_modal_name()
        modal_animation = interface_options.extra_animation and modal_name and modal_name != self.state.last_modal_operator
        self.state.last_modal_operator = modal_name

        # Handle animation start
        if (self.state.last_tool != active_tool.idname or
            (self.state.last_operator != current_operator and active_tool.idname == 'nsolve.nsolvetool') or modal_animation):
            if interface_options.enable_animation:
                self.start_animation(active_tool.idname, current_operator)
            if interface_options.enable_banner and current_operator:
                self.state.banner_start = time.time()
                self.state.last_tool = active_tool.idname
                self.state.last_operator = current_operator
                self.state.animate_banner = True

        if self.state.animate_banner and time.time() - self.state.banner_start >= interface_options.animation_duration:
            self.state.animate_banner = False

            main_text = self.get_text_content(active_tool, nsolve_prefs).upper()
            if modal_name:
                if modal_name == 'MESH CUT' and addon.pref().tools.nsuite.continuous_cut:
                    main_text = 'MESH MULTI CUT'
                else :
                    main_text = modal_name.upper()

            bpy.ops.nsolve.banner('INVOKE_DEFAULT', operator=main_text)

        if not interface_options.show_interface:
            return

        # Calculate positions
        left_x, right_x, top_y, bottom_y, line_length, line_width = self.calculate_corner_positions(context, interface_options)

        # Create and draw corners
        corners = [
            # Top-left corner
            [(left_x, top_y), (left_x + line_length, top_y)],
            [(left_x, top_y), (left_x, top_y - line_length)],
            # Top-right corner
            [(right_x - line_length, top_y), (right_x, top_y)],
            [(right_x, top_y), (right_x, top_y - line_length)],
            # Bottom-left corner
            [(left_x, bottom_y + line_length), (left_x, bottom_y)],
            [(left_x, bottom_y), (left_x + line_length, bottom_y)],
            # Bottom-right corner
            [(right_x, bottom_y + line_length), (right_x, bottom_y)],
            [(right_x - line_length, bottom_y), (right_x, bottom_y)]
        ]

        # Draw corners
        color = self.get_tool_color(active_tool, interface_color, current_operator)
        self.draw_corner_lines(corners, line_width, color)

        # Setup text drawing
        font_id = 0  # Default font ID
        if interface_options.custom_font:
            font_id = blf.load(get_font_path(interface_options.font_type))
        dpi_factor = bpy.context.preferences.view.ui_scale * bpy.context.preferences.system.pixel_size
        text_margin = 30 * dpi_factor

        # Get text content
        main_text = self.get_text_content(active_tool, nsolve_prefs)

        # If nsolve modal is running write its text instead
        if modal_name:
            main_text = self.modal_draw_name(modal_name)

        # Setup main text properties
        text_size = interface_options.animation_text_size
        font_size = int(text_size * dpi_factor)
        blf.size(font_id, font_size)

        # Calculate text position - center for main tool, right side for others
        if active_tool.idname == 'nsolve.main_tool':
            text_width = blf.dimensions(font_id, main_text)[0]
            base_text_x = (right_x - left_x - text_width) / 2 + left_x
            main_text_y = bottom_y + text_margin
        else:
            base_text_x = right_x - line_length - text_margin - blf.dimensions(font_id, main_text)[0]
            main_text_y = bottom_y

        # Handle main text animation and drawing
        current_time = time.time()

        # Check for active modals - hide text if any are running
        if self.is_modal_active(context):
            opacity = 0.0
            text_x = base_text_x
        # Always start with zero opacity when animation begins
        elif self.state.is_animating and current_time - self.state.animation_start < 0.1:
            text_x = base_text_x + bpy.context.region.width  # Start far offscreen
            opacity = 0.0
        elif interface_options.animation_text_in_time:
            text_x, opacity = self.handle_main_text_animation(current_time, font_id, dpi_factor, base_text_x)
        else:
            if self.state.is_animating:
                text_x = base_text_x + bpy.context.region.width  # Start far offscreen
                opacity = 0.0
            else:
                text_x = base_text_x
                opacity = 1.0

        # Only draw if we have opacity
        if opacity > 0:
            self.draw_main_text(font_id, main_text, text_x, main_text_y, opacity, dpi_factor)

        gpu.state.blend_set('NONE')

    def modal_draw_name(self, modal_name):
        if modal_name == 'MESH CUT' and addon.pref().tools.nsuite.continuous_cut:
            main_text = 'Mesh Multi Cut'
        else:
            main_text = modal_name.capitalize()
        return main_text

    def animation_timer(self):
        """Timer function to update animation"""
        nsolve_prefs = addon.pref().tools.nsolve
        interface_options = nsolve_prefs.InterfaceOptions

        if not interface_options.enable_animation:
            self.reset_animation_state()
            return None

        if self.state.is_animating:
            self.redraw_viewports()

            current_time = time.time()
            animation_duration = interface_options.animation_duration
            animation_progress = (current_time - self.state.animation_start) / animation_duration

            # Handle corner animation
            if animation_progress < 1.0:
                # Corners are still animating
                self.state.corners_done = False
            else:
                # Corners animation is complete
                self.state.corners_done = True

            # Handle operator/base text animation independently
            self.handle_operator_animation(interface_options.animation_duration, current_time)

            return 0.02  # 50fps update rate

        return None

    def start_animation(self, tool_id, operator):
        """Start a new animation sequence"""
        # Always start a new animation when operator changes
        self.state.should_animate_text = True
        self.state.animation_start = time.time()
        self.state.last_tool = tool_id
        self.state.last_operator = operator
        self.state.is_animating = True

        # Reset corner animation state
        self.state.corners_done = False

        # Reset base/operator text animation state
        self.state.operator_opacity = 0.0
        self.state.operator_x_offset = 0
        self.state.operator_start_time = 0

        # Reset main text animation state
        self.state.main_text_opacity = 0.0
        self.state.main_text_x_offset = -30.0
        self.state.main_text_start_time = 0

        # Get animation duration from preferences to set main text delay
        nsolve_prefs = addon.pref().tools.nsolve
        interface_options = nsolve_prefs.InterfaceOptions
        # Set main text delay to match corner animation duration
        self.state.main_text_delay = interface_options.animation_duration

        # Reset gizmo text animation state
        self.state.gizmo_text_opacity = 0.0
        self.state.gizmo_text_y_offset = -20.0
        self.state.gizmo_text_start_time = 0
        self.state.should_animate_gizmo_text = True

        if self.timer_handler is None:
            self.timer_handler = bpy.app.timers.register(self.animation_timer)

    def reset_animation_state(self):
        """Reset animation state to default values"""
        self.state.is_animating = False
        self.state.corners_done = True
        self.state.operator_opacity = 0.8
        self.state.operator_x_offset = 0
        self.state.main_text_opacity = 1.0
        self.state.main_text_x_offset = 0
        self.state.main_text_start_time = 0
        self.state.should_animate_text = False
        # Reset gizmo text animation state but keep it visible
        self.state.gizmo_text_opacity = 1.0
        self.state.gizmo_text_y_offset = 0
        self.state.gizmo_text_start_time = 0
        self.state.should_animate_gizmo_text = True  # Keep this true to maintain visibility

    def update_animation_state(self, corners_done, opacity, x_offset):
        """Update animation state values"""
        self.state.corners_done = corners_done
        self.state.operator_opacity = opacity
        self.state.operator_x_offset = x_offset

    def handle_operator_animation(self, fade_duration, current_time):
        """Handle operator animation sequence"""
        # Initialize operator animation if not started yet
        if self.state.operator_start_time == 0:
            self.state.operator_start_time = self.state.animation_start

        # Calculate progress based on time since animation started
        operator_progress = current_time - self.state.operator_start_time
        nsolve_prefs = addon.pref().tools.nsolve
        interface_options = nsolve_prefs.InterfaceOptions

        # Get text animation timings
        text_duration = interface_options.text_duration
        in_time = interface_options.text_in_time * text_duration
        hold_time = text_duration - (interface_options.text_in_time + interface_options.text_out_time) * text_duration
        out_time = interface_options.text_out_time * text_duration

        if operator_progress <= in_time:
            # Fade and slide in with smooth easing
            progress = operator_progress / in_time
            eased_progress = self.ease_in_out_cubic(progress)

            # Update text position and opacity
            self.state.operator_opacity = eased_progress
            self.state.operator_x_offset = 100 * (1 - self.ease_in_out_quad(progress))
        elif operator_progress <= in_time + hold_time:
            # Hold position
            self.state.operator_opacity = 1.0
            self.state.operator_x_offset = 0
        else:
            # Fade and slide out with smooth easing
            progress = (operator_progress - (in_time + hold_time)) / out_time
            eased_progress = self.ease_in_out_cubic(progress)
            self.state.operator_opacity = 1.0 - eased_progress
            self.state.operator_x_offset = -100 * self.ease_in_out_quad(progress)

        if operator_progress >= text_duration:
            # Animation complete
            self.state.is_animating = False
            self.state.operator_opacity = 0.0

    def redraw_viewports(self):
        """Force redraw of all 3D viewports"""
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
