import blf
from ...utils.region import fixed_width
from ...utils import addon

def draw_text(context, text, position, color=(1, 1, 1, 1), size=None, shadow=True):
    """Draw text in the viewport
    Args:
        context: Blender context
        text: Text to draw
        position: (x, y) position in pixels
        color: (r, g, b, a) color tuple
        size: Font size (uses addon preferences if None)
        shadow: Whether to draw text shadow
    """
    # Get interface options if size not specified
    if size is None:
        nsolve_prefs = addon.pref().tools.nsolve
        interface_options = nsolve_prefs.InterfaceOptions
        size = interface_options.text_size
    
    # Setup font
    font_id = 0
    blf.size(font_id, size)
    
    # Draw text
    if shadow:
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 5, 0, 0, 0, 1)
    
    blf.color(font_id, *color)
    blf.position(font_id, position[0], position[1], 0)
    blf.draw(font_id, text)
    
    if shadow:
        blf.disable(font_id, blf.SHADOW)
