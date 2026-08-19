import os
from .parser import MarkdownParser
from .layout import LayoutEngine
from .draw import DrawingUtils

__all__ = ['MarkdownRenderer', 'MarkdownParser', 'LayoutEngine', 'DrawingUtils']


class MarkdownRenderer:
    def __init__(self):
        # Color scheme
        self.color_main = (0.6, 0.6, 0.6, 1.0)  # Main text - gray
        self.color_main_variation = (0.7, 0.7, 0.7, 1.0)  # Lighter gray
        self.color_accent = (1.0, 0.7, 0.2, 1.0)  # Orange
        self.color_accent_variation = (0.8, 0.6, 0.2, 1.0)  # Lighter orange
        self.color_background = (0.12, 0.12, 0.12, 1.0)  # Dark gray
        self.color_code_background = (0.17, 0.17, 0.17, 1.0)  # Slightly more visible for code blocks
        self.color_code_text = (0.85, 0.85, 0.85, 1.0)  # Brighter text for code blocks

        # Content size and margin settings
        self.max_content_width = 700  # Maximum content width in pixels
        self.margin_size_x = 0.2  # Percentage of viewport for horizontal margins
        self.margin_size_y = 0.14  # Percentage of viewport for vertical margins
        self.margin_inner = 0  # Inner spacing between content and background box
        self._background_corners_size = 36  # Size of the background corners in pixels

        self._layout_instructions = []
        self._cached_text = None
        self._cached_filepath = None
        self._cached_mtime = None
        self._is_drawing = False
        self._margin = 20
        
        # Font and spacing configuration
        self._default_font_size = 14  # Set default font size to 8px
        self._code_font_size = 8  # Set code font size to 8px
        self._heading_sizes = {
            1: 32,  # H1 - slightly reduced for better spacing
            2: 24,  # H2
            3: 20,  # H3
            4: 16,  # H4
        }
        
        # Consistent spacing values
        self._line_spacing = 8  # Base line spacing - increased for better readability
        self._paragraph_spacing = self._line_spacing  # Now equal to line spacing
        self._heading_spacing = self._line_spacing  # Now equal to line spacing
        self._section_spacing = self._line_spacing  # Now equal to line spacing
        self._last_element_type = None

        # List to store link regions for click detection
        self._links = []
        # Track current cursor state
        self._is_cursor_over_link = False

        self._font_paths = self._load_fonts()
        self.parser = MarkdownParser(self)
        self.layout = LayoutEngine(self)
        self.draw = DrawingUtils(self)

    @property
    def cached_text(self):
        return self._cached_text

    @cached_text.setter
    def cached_text(self, value):
        self._cached_text = value

    @property
    def cached_filepath(self):
        return self._cached_filepath

    @cached_filepath.setter
    def cached_filepath(self, value):
        self._cached_filepath = value

    @property
    def cached_mtime(self):
        return self._cached_mtime

    @cached_mtime.setter
    def cached_mtime(self, value):
        self._cached_mtime = value

    @property
    def font_paths(self):
        return self._font_paths

    def _load_fonts(self):
        current_dir = os.path.dirname(__file__)
        fonts_dir = os.path.join(current_dir, "fonts")
        font_paths = {
            'regular': os.path.join(fonts_dir, "RobotoMono-Regular.ttf"),
            'semibold': os.path.join(fonts_dir, "RobotoMono-Regular.ttf"),  # Fallback to Regular
            'bold': os.path.join(fonts_dir, "RobotoMono-Bold.ttf"),
            'extrabold': os.path.join(fonts_dir, "RobotoMono-Bold.ttf")  # Fallback to Bold
        }
        return font_paths

    @property
    def filepath(self):
        return self._cached_filepath

    @filepath.setter
    def filepath(self, value):
        self._cached_filepath = value
        self._cached_text = None
        self._cached_mtime = None

    @property
    def draw_handle(self):
        return self._is_drawing

    @draw_handle.setter
    def draw_handle(self, value):
        self._is_drawing = bool(value)

    @property
    def background_corners_size(self):
        return self._background_corners_size

    @background_corners_size.setter
    def background_corners_size(self, value):
        self._background_corners_size = value

    @property
    def links(self):
        return self._links

    def clear_links(self):
        """Clear the links list before re-parsing"""
        self._links.clear()

    def add_link(self, url, x, y, width, height):
        """Add a link region to the links list"""
        self._links.append({
            'url': url,
            'x': x,
            'y': y,
            'width': width,
            'height': height
        })

    def get_link_at_position(self, x, y):
        """Check if there's a link at the given position with improved hit detection
        
        This function implements a more generous hit detection algorithm that
        considers the click to be within the link if it's close enough to it.
        """
        # Additional tolerance for click detection (px)
        tolerance = 2
        
        for link in self._links:
            # Calculate the boundaries of the link with added tolerance
            min_x = link['x'] - tolerance
            max_x = link['x'] + link['width'] + tolerance
            min_y = link['y'] - link['height'] - tolerance
            max_y = link['y'] + tolerance
            
            if min_x <= x <= max_x and min_y <= y <= max_y:
                return link['url']
        return None
        
    def is_mouse_over_link(self, x, y):
        """Check if mouse is over a link and return True if it is
        
        This is used for cursor changes when hovering over links
        """
        return self.get_link_at_position(x, y) is not None

    def update_cursor_for_link(self, context, x, y):
        """Updates cursor appearance based on whether mouse is hovering over a link"""
        is_over_link = self.is_mouse_over_link(x, y)
        
        # Only change cursor if state changed to avoid unnecessary cursor changes
        if is_over_link != self._is_cursor_over_link:
            if is_over_link:
                context.window.cursor_modal_set('HAND')
            else:
                context.window.cursor_modal_set('DEFAULT')
            self._is_cursor_over_link = is_over_link
        
        return is_over_link

    def draw_callback(self, context, scroll_offset=0):
        """Main draw callback for the viewport"""
        self.clear_links()  # Clear links before parsing and drawing
        return self.draw.draw_callback(context, scroll_offset)

    def parse_markdown(self, filepath):
        """Proxy to parser component"""
        return self.parser.parse_markdown(filepath)

    def compute_layout(self, blocks, start_x, start_y, max_width):
        """Proxy to layout component"""
        return self.layout.compute_layout(blocks, start_x, start_y, max_width)

    # Getter methods for layout engine
    def get_layout_instructions(self):
        return self._layout_instructions

    def get_font_size(self):
        return self._default_font_size

    def get_heading_font_size(self, level):
        return self._heading_sizes.get(level, self._default_font_size)

    def get_line_spacing(self):
        return self._line_spacing

    def get_paragraph_spacing(self):
        return self._paragraph_spacing

    def get_heading_spacing(self):
        return self._heading_spacing

    def get_section_spacing(self):
        return self._section_spacing

    def get_code_font_size(self):
        return self._code_font_size

    def clear_layout(self):
        self._layout_instructions.clear()

    def add_layout_instruction(self, instruction):
        """Add a layout instruction with proper element spacing"""
        current_type = instruction.get('type')

        # Add extra spacing based on content type transitions
        if self._last_element_type:
            if current_type == 'heading':
                # Add extra space before headings
                instruction['y'] -= self._heading_spacing
            elif self._last_element_type == 'image' and current_type in ['text', 'heading']:
                # Add extra space after images when followed by text content
                instruction['y'] -= self._section_spacing
            elif self._last_element_type == 'heading' and current_type != 'heading':
                # Add extra space after headings
                instruction['y'] -= self._heading_spacing
            
        self._layout_instructions.append(instruction)
        self._last_element_type = current_type
