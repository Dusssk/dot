import os

def get_available_fonts():
    """Get all available TTF fonts in the fonts directory"""
    base_dir = os.path.dirname(__file__)
    font_files = [f for f in os.listdir(base_dir) if f.endswith('.ttf')]
    
    # Create font mapping
    fonts = {}
    font_items = []
    
    for font_file in font_files:
        # Convert filename to enum name (e.g., 'Genos-Bold.ttf' -> 'GENOS_BOLD')
        name_parts = os.path.splitext(font_file)[0].split('-')
        enum_name = f"{name_parts[0].upper()}_{name_parts[1].upper()}"
        
        # Create display name (e.g., 'Genos Bold')
        display_name = f"{name_parts[0]} {name_parts[1]}"
        
        # Add to fonts dictionary
        fonts[enum_name] = font_file
        
        # Add to items list for EnumProperty
        font_items.append((enum_name, display_name, f"Use {display_name} font"))
    
    return fonts, font_items

# Generate font mappings
FONT_FILES, FONT_ITEMS = get_available_fonts()

def get_font_path(font_type):
    """Get the path to the font file based on the font type"""
    base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, FONT_FILES[font_type])
