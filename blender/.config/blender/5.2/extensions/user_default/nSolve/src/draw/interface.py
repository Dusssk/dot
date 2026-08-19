import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

class DrawInterface:
    def __init__(self, region, region_data):
        self.region = region
        self.region_data = region_data
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.text_boxes = []  # List to store text box data
        self.font_id = 0  # Default font
        self.font_size = None  # Will be set from interface options
        self.padding = 5  # Padding inside boxes
        self.initial_position = Vector((10, 10))  # Initial position for the first box
        self.spacing = 10  # Space between boxes
        self.current_position = self.initial_position.copy()  # Current position for next box

    def add_text_box(self, text, position=None, text_color=(1, 1, 1, 1), box_color=(0.2, 0.2, 0.2, 0.8), is_bottom=False):
        """Add a text box to be drawn
        Args:
            text: String to display
            position: Optional (x, y) tuple for top-left position. If None, uses automatic positioning
            text_color: RGBA tuple for text color
            box_color: RGBA tuple for box color
            is_bottom: If True, uses bottom_text_size instead of text_size
        """
        if position is None:
            position = self.current_position
        else:
            position = Vector(position)

        # Add the text box
        self.text_boxes.append({
            'text': text,
            'position': position,
            'text_color': text_color,
            'box_color': box_color,
            'is_bottom': is_bottom
        })

        # Update current position for next box
        text_width, text_height = self.get_text_dimensions(text, is_bottom)
        box_width = text_width + (self.padding * 2)
        self.current_position.x = position.x + box_width + self.spacing

    def clear(self):
        """Clear all text boxes and reset position"""
        self.text_boxes.clear()
        self.current_position = self.initial_position.copy()

    def get_text_dimensions(self, text, is_bottom=False):
        """Get width and height of text"""
        # Get text size from interface options
        interface_options = addon.pref().tools.nsolve.InterfaceOptions
        font_size = interface_options.bottom_text_size if is_bottom else interface_options.text_size
        blf.size(self.font_id, font_size)
        return blf.dimensions(self.font_id, text)

    def draw(self):
        """Draw all text boxes"""
        if not self.text_boxes:
            return

        # Get interface options for text sizes
        interface_options = addon.pref().tools.nsolve.InterfaceOptions

        for box in self.text_boxes:
            text = box['text']
            position = box['position']
            text_color = box['text_color']
            box_color = box['box_color']
            is_bottom = box.get('is_bottom', False)

            # Set font size based on whether this is bottom text
            font_size = interface_options.bottom_text_size if is_bottom else interface_options.text_size
            blf.size(self.font_id, font_size)
            blf.enable(self.font_id, blf.CLIPPING)

            # Get text dimensions
            text_width, text_height = self.get_text_dimensions(text, is_bottom)

            # Calculate box dimensions with padding
            box_width = text_width + (self.padding * 2)
            box_height = text_height + (self.padding * 2)

            # Draw box
            vertices = (
                (position.x, position.y),
                (position.x + box_width, position.y),
                (position.x + box_width, position.y - box_height),
                (position.x, position.y - box_height)
            )

            indices = ((0, 1, 2), (0, 2, 3))

            self.shader.bind()
            self.shader.uniform_float("color", box_color)

            batch = batch_for_shader(
                self.shader, 'TRIS',
                {"pos": vertices},
                indices=indices
            )
            batch.draw(self.shader)

            # Draw text
            blf.position(
                self.font_id,
                position.x + self.padding,
                position.y - self.padding - text_height,
                0
            )
            blf.color(self.font_id, *text_color)
            blf.draw(self.font_id, text)

    def set_font_size(self, size):
        """Set font size for subsequent text"""
        self.font_size = size

    def set_padding(self, padding):
        """Set padding for subsequent boxes"""
        self.padding = padding

    def set_initial_position(self, x, y):
        """Set the initial position for text box layout"""
        self.initial_position = Vector((x, y))
        self.current_position = self.initial_position.copy()

    def set_spacing(self, spacing):
        """Set the spacing between text boxes"""
        self.spacing = spacing
