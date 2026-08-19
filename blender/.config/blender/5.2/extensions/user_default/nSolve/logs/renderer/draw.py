import os
import math
import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader


class DrawingUtils:
    def __init__(self, renderer):
        self.renderer = renderer
        self._setup_fonts()
        self._image_cache = {}

    def get_image(self, image_path):
        """Public method to load and retrieve images"""
        return self._load_image(image_path)

    def _setup_fonts(self):
        # Initialize all font IDs with regular font as fallback
        self.regular_font_id = 0
        self.semibold_font_id = 0
        self.bold_font_id = 0
        self.extrabold_font_id = 0

        # Load fonts if available
        if os.path.exists(self.renderer.font_paths['regular']):
            self.regular_font_id = blf.load(self.renderer.font_paths['regular'])

        if os.path.exists(self.renderer.font_paths['semibold']):
            self.semibold_font_id = blf.load(self.renderer.font_paths['semibold'])
        else:
            self.semibold_font_id = self.regular_font_id

        if os.path.exists(self.renderer.font_paths['bold']):
            self.bold_font_id = blf.load(self.renderer.font_paths['bold'])
        else:
            self.bold_font_id = self.regular_font_id

        if os.path.exists(self.renderer.font_paths['extrabold']):
            self.extrabold_font_id = blf.load(self.renderer.font_paths['extrabold'])
        else:
            self.extrabold_font_id = self.bold_font_id  # Fallback to bold if extrabold not available

    def get_heading_font_id(self, level):
        """Get font ID for heading based on level
        Args:
            level: Heading level (1-6)
        Returns:
            Font ID to use for this heading level
        """
        if level == 1:
            return self.extrabold_font_id
        elif level == 2:
            return self.bold_font_id
        elif level == 3:
            return self.semibold_font_id
        else:
            return self.regular_font_id

    def get_font_id(self, line_type='text', style='normal'):
        """Get font ID based on line type and style"""
        if line_type == 'heading' or style == 'bold':
            return self.bold_font_id
        return self.regular_font_id

    def draw_line(self, content, x, y, indent_count=0, line_type='text', style='normal'):
        """Draw a line with pixel-based indentation
        Args:
            content: Text content to draw
            x: Base x position
            y: Y position
            indent_count: Number of indentation levels
            line_type: Type of line (heading, text, etc)
            style: Text style (normal, bold)
        """
        # Get appropriate font and draw
        font_id = self.get_font_id(line_type, style)
        # Calculate x position with pixel-based indent
        x_pos = x + self.renderer.layout.get_indent_pixels(indent_count)
        # Draw stripped content at calculated position
        blf.position(font_id, x_pos, y, 0)
        blf.draw(font_id, content.strip())

    def _create_rounded_corner_points(self, corner_x, corner_y, radius, start_angle, segments=8):
        """Create a list of points for a rounded corner starting from base corner point"""
        points = []
        angle_step = math.pi / 2 / segments

        # Generate arc points
        for i in range(segments + 1):
            angle = start_angle + i * angle_step
            x = corner_x + radius * math.cos(angle)
            y = corner_y + radius * math.sin(angle)
            points.append((x, y))

        return points

    def draw_background(self, context):
        """Draw the background for the centered content rectangle with rounded corners"""
        region = context.region
        width, height = region.width, region.height

        # Calculate content width without any extra margins
        content_width = min(self.renderer.max_content_width, width)
        # Calculate margins based on max width
        margin_x = (width - content_width) / 2
        margin_y = height * self.renderer.margin_size_y
        content_height = height - (margin_y * 2)

        # Use the background_corners_size property for radius
        radius = self.renderer.background_corners_size

        # Base rectangle corners for background
        top_right = (margin_x + content_width, margin_y + content_height)
        top_left = (margin_x, margin_y + content_height)
        bottom_left = (margin_x, margin_y)
        bottom_right = (margin_x + content_width, margin_y)

        # Center point for triangulation
        center = (margin_x + content_width/2, margin_y + content_height/2)
        vertices = [center]  # Start with center vertex

        # Create corner points with rounding
        corners = [
            (top_right, 0),              # Top right - start at 0 radians
            (top_left, math.pi/2),       # Top left - start at 90 degrees
            (bottom_left, math.pi),      # Bottom left - start at 180 degrees
            (bottom_right, 1.5*math.pi)  # Bottom right - start at 270 degrees
        ]

        indices = []
        prev_end_idx = -1

        # Process each corner
        for (corner_x, corner_y), start_angle in corners:
            # Get points for this rounded corner
            corner_points = self._create_rounded_corner_points(
                corner_x, corner_y, radius, start_angle)

            # Add points to vertex list
            start_idx = len(vertices)
            vertices.extend(corner_points)
            end_idx = len(vertices) - 1

            # Create triangles between pairs of corner points and center
            for i in range(start_idx, end_idx):
                indices.append((0, i, i + 1))

            # Connect to previous corner if not first corner
            if prev_end_idx >= 0:
                indices.append((0, prev_end_idx, start_idx))

            prev_end_idx = end_idx

        # Connect last corner to first corner
        first_corner_start = 1  # Index where first corner starts
        indices.append((0, prev_end_idx, first_corner_start))

        # Draw the triangles
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

        shader.bind()
        shader.uniform_float("color", self.renderer.color_background)
        batch.draw(shader)

    def draw_text_layout(self):
        """Draw all text from layout instructions"""
        gpu.state.blend_set('ALPHA')

        # Draw code line backgrounds first
        for instr in self.renderer.get_layout_instructions():
            if instr['type'] == 'code_line_bg':
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                x, y = int(instr['x']), int(instr['y'])  # Ensure integer positions
                width, height = int(instr['width']), int(instr['height'])

                # Draw rectangle with exact pixel alignment
                vertices = (
                    (x, y),
                    (x + width, y),
                    (x, y - height),
                    (x + width, y - height)
                )

                batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": vertices})
                shader.bind()
                shader.uniform_float("color", instr['color'])
                batch.draw(shader)

        # Draw text content after backgrounds
        for instr in self.renderer.get_layout_instructions():
            if instr['type'] in ['text', 'code']:
                font_id = instr.get('font_id', 0)
                # Always use code font size for code blocks
                font_size = instr.get('font_size', self.renderer.get_code_font_size() if instr['type'] == 'code' else self.renderer.get_font_size())
                blf.size(font_id, font_size)

                # Use accent color for links, otherwise use the specified color or main color
                if instr.get('is_link', False):
                    blf.color(font_id, *self.renderer.color_accent)
                else:
                    blf.color(font_id, *instr.get('color', self.renderer.color_main))

                # Ensure pixel-perfect text positioning
                blf.position(font_id, int(instr['x']), int(instr['y']), 0)
                blf.draw(font_id, instr['text'])

        gpu.state.blend_set('NONE')

    def _load_image(self, image_path):
        """Load and cache an image for drawing"""
        if image_path in self._image_cache:
            return self._image_cache[image_path]

        if os.path.exists(image_path):
            try:
                image = bpy.data.images.load(image_path, check_existing=True)
                # Ensure alpha channel is enabled
                image.alpha_mode = 'STRAIGHT'
                self._image_cache[image_path] = image
                return image
            except Exception as e:
                print(f"Failed to load image: {e}")
                return None
        return None

    def draw_image(self, x, y, image_path, max_width):
        """Draw an image at the specified position with max width constraint"""
        image = self._load_image(image_path)
        if not image:
            return y

        # Calculate dimensions maintaining aspect ratio
        aspect = image.size[1] / image.size[0]
        width = min(max_width, image.size[0])
        height = width * aspect

        # Enable alpha blending
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')

        # Create textured rectangle with corrected vertex and UV order for proper orientation
        vertices = (
            (x, y), (x + width, y),
            (x, y - height), (x + width, y - height)
        )
        uvs = ((0, 1), (1, 1), (0, 0), (1, 0))

        shader = gpu.shader.from_builtin('IMAGE')
        batch = batch_for_shader(shader, 'TRI_STRIP', {
            "pos": vertices,
            "texCoord": uvs,
        })

        # Create GPU texture
        if image.gl_load():
            gpu.state.blend_set('NONE')
            return y

        texture = gpu.texture.from_image(image)

        shader.bind()
        shader.uniform_sampler("image", texture)
        batch.draw(shader)

        # Reset GPU state
        gpu.state.blend_set('NONE')

        return y - height

    def draw_callback(self, context, scroll_offset=0):
        """Main draw callback for the viewport"""
        gpu.state.blend_set('ALPHA')

        region = context.region
        margin_x = region.width * self.renderer.margin_size_x
        margin_y = region.height * self.renderer.margin_size_y

        # Calculate content width respecting max width constraint
        content_width = min(self.renderer.max_content_width, region.width)
        if content_width < region.width:
            margin_x = (region.width - content_width) / 2

        content_height = region.height - (margin_y * 2)

        # Space between content and scrollbar
        scrollbar_spacing = 15  # Increased spacing between content and scrollbar
        scrollbar_width = 10

        # Determine if we need a scrollbar (we'll calculate this properly after layout)
        needs_scrollbar = True  # Assume we need it initially

        # Adjust content width to account for scrollbar and spacing if needed
        if needs_scrollbar:
            effective_content_width = content_width - scrollbar_width - scrollbar_spacing
        else:
            effective_content_width = content_width

        # Draw background first
        self.draw_background(context)

        # Setup scissor region matching background exactly
        gpu.state.scissor_test_set(True)
        gpu.state.scissor_set(
            int(margin_x),
            int(margin_y),
            int(effective_content_width),
            int(content_height)
        )

        # Calculate start positions at the exact edges of background
        start_x = margin_x
        start_y = region.height - margin_y + scroll_offset

        # Parse and layout content
        blocks = self.renderer.parse_markdown(self.renderer.filepath)
        total_height = self.renderer.compute_layout(blocks, start_x, start_y, effective_content_width)

        # Now we know for sure if we need a scrollbar
        needs_scrollbar = total_height > content_height

        # Draw content in order:
        # 1. Code block backgrounds first
        for instr in self.renderer.get_layout_instructions():
            if instr['type'] == 'code_line_bg':
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                x, y = int(instr['x']), int(instr['y'])
                width, height = int(instr['width']), int(instr['height'])

                # Adjust background to align with text baseline
                y_offset = height * 0.45  # Move background up slightly more
                y = y + y_offset
                height = height * 0.7  # Reduce height slightly to better match text

                # Draw rectangle with exact pixel alignment
                vertices = (
                    (x, y),
                    (x + width, y),
                    (x, y - height),
                    (x + width, y - height)
                )

                batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": vertices})
                shader.bind()
                shader.uniform_float("color", instr['color'])
                batch.draw(shader)

        # 2. Text and other elements after backgrounds
        for instr in self.renderer.get_layout_instructions():
            if instr['type'] in ['text', 'code']:
                font_id = instr.get('font_id', 0)
                # Use code font size for code blocks
                font_size = instr.get('font_size', self.renderer.get_code_font_size() if instr['type'] == 'code' else self.renderer.get_font_size())
                blf.size(font_id, font_size)

                # Use accent color for links, otherwise use the specified color or main color
                if instr.get('is_link', False):
                    blf.color(font_id, *self.renderer.color_accent)
                else:
                    blf.color(font_id, *instr.get('color', self.renderer.color_main))

                # Ensure pixel-perfect text positioning
                blf.position(font_id, int(instr['x']), int(instr['y']), 0)
                blf.draw(font_id, instr['text'])

        # 3. Draw horizontal rules and images last
        for instr in self.renderer.get_layout_instructions():
            if instr['type'] == 'hr':
                gpu.state.line_width_set(2.0)
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                y = instr['y']
                vertices = [(instr['x'], y), (instr['x'] + instr['width'], y)]
                batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
                shader.bind()
                shader.uniform_float("color", instr['color'])
                batch.draw(shader)
                gpu.state.line_width_set(1.0)
            elif instr['type'] == 'image':
                self.draw_image(instr['x'], instr['y'], instr['path'], instr['max_width'])

        # Reset GPU state
        gpu.state.scissor_test_set(False)
        gpu.state.blend_set('NONE')

        # Draw scrollbar if content is scrollable
        visible_height = content_height
        if needs_scrollbar:
            self.draw_scrollbar(
                context,
                margin_x + effective_content_width + scrollbar_spacing,  # Position scrollbar with spacing from content
                margin_y,
                scrollbar_width,
                content_height,
                total_height,
                scroll_offset
            )

        return total_height

    def draw_scrollbar(self, context, x, y, width, viewport_height, content_height, scroll_offset):
        """Draw a scrollbar on the right side of the content

        Args:
            context: Blender context
            x: X position of scrollbar (left edge)
            y: Y position of scrollbar (bottom edge)
            width: Width of scrollbar
            viewport_height: Height of visible viewport
            content_height: Total height of content
            scroll_offset: Current scroll offset
        """
        if content_height <= viewport_height:
            return  # No need for scrollbar

        # Calculate scrollbar metrics
        scrollbar_height = viewport_height

        # Calculate thumb size and position
        # The thumb size is proportional to the visible portion of content
        visible_ratio = min(1.0, viewport_height / content_height)
        thumb_height = max(40, scrollbar_height * visible_ratio)  # Minimum size for usability

        # Calculate thumb position based on scroll offset
        # The scroll_offset is negative when scrolling down
        max_scroll = abs(content_height - viewport_height)
        scroll_ratio = 0 if max_scroll == 0 else min(1.0, scroll_offset / max_scroll)

        # Calculate thumb position - adjust for the thumb height
        thumb_y = y + scrollbar_height - thumb_height - (scroll_ratio * (scrollbar_height - thumb_height))

        # Draw scrollbar background
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        # Draw scrollbar background (track)
        vertices = (
            (x, y),
            (x + width, y),
            (x, y + scrollbar_height),
            (x + width, y + scrollbar_height)
        )

        batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": vertices})
        shader.bind()
        track_color = self.renderer.color_background
        shader.uniform_float("color", track_color)
        batch.draw(shader)

        # Draw scrollbar thumb
        vertices = (
            (x, thumb_y),
            (x + width, thumb_y),
            (x, thumb_y + thumb_height),
            (x + width, thumb_y + thumb_height)
        )

        batch = batch_for_shader(shader, 'TRI_STRIP', {"pos": vertices})
        shader.bind()
        thumb_color = (0.5, 0.5, 0.5, 0.8)  # Darker gray with more opacity
        shader.uniform_float("color", thumb_color)
        batch.draw(shader)