import blf


class LayoutEngine:
    def __init__(self, renderer):
        self.renderer = renderer
        self.pixels_per_indent = 12  # Fixed number of pixels per indent level
        self.base_line_height = self.renderer.get_font_size() + self.renderer.get_line_spacing()
        self.link_padding = 4  # Padding around links to make them easier to click

    def get_indent_pixels(self, indent_count):
        """Convert indent count to pixels"""
        return self.pixels_per_indent * indent_count

    def layout_paragraph(self, text, x, y, max_width, font_size=16, indent_count=0):
        """Layout a paragraph with word wrapping and indentation
        Args:
            indent_count: Number of indent levels (each level is pixels_per_indent pixels)
        """
        lines = []
        line_spacing = self.renderer.get_line_spacing()
        first_line = True  # Track if this is the first line
        
        # Calculate indent offset in pixels using fixed pixel width
        indent_width = self.pixels_per_indent * indent_count

        # Split text into physical lines first (handle explicit line breaks)
        physical_lines = text.split('\n')
        
        for physical_line in physical_lines:
            if not physical_line.strip():
                # Empty line, just add the spacing
                if not first_line:
                    y -= line_spacing
                first_line = False
                continue
                
            segments = self.renderer.parser.parse_emphasis(physical_line)
            current_line = []
            current_width = indent_width
            line_x = x + indent_width

            for segment in segments:
                if len(segment) == 2:  # Normal text or bold
                    style, text = segment
                    words = text.split()
                    font_id = self.renderer.draw.get_font_id(style)
                    blf.size(font_id, font_size)

                    for word in words:
                        word_width = blf.dimensions(font_id, word + " ")[0]

                        if current_width + word_width > max_width:
                            # Line is full, start new line
                            if current_line:
                                lines.append((current_line, line_x, y))
                                if not first_line:
                                    y -= line_spacing
                                first_line = False
                                current_line = []
                                current_width = indent_width
                                line_x = x + indent_width

                        current_line.append((word + " ", style))
                        current_width += word_width
                elif len(segment) == 3:  # Link with URL
                    style, text, url = segment
                    words = text.split()
                    font_id = self.renderer.draw.get_font_id(style)
                    blf.size(font_id, font_size)
                    
                    # For links, we try to keep the entire link on one line if possible
                    link_text = " ".join(words)
                    link_width = blf.dimensions(font_id, link_text + " ")[0]
                    
                    # If the entire link fits, add it as a whole
                    if current_width + link_width <= max_width:
                        current_line.append((link_text + " ", style, url))
                        current_width += link_width
                    else:
                        # If not, add the link word by word
                        for word in words:
                            word_width = blf.dimensions(font_id, word + " ")[0]
                            
                            if current_width + word_width > max_width:
                                # Line is full, start new line
                                if current_line:
                                    lines.append((current_line, line_x, y))
                                    if not first_line:
                                        y -= line_spacing
                                    first_line = False
                                    current_line = []
                                    current_width = indent_width
                                    line_x = x + indent_width
                            
                            # Add word as part of the link
                            current_line.append((word + " ", style, url))
                            current_width += word_width

            # Add the line if there's content
            if current_line:
                lines.append((current_line, line_x, y))
                if not first_line:
                    y -= line_spacing
                first_line = False

        return lines, y

    def compute_layout(self, blocks, start_x, start_y, max_width):
        """Convert blocks into layout instructions and return the total height"""
        self.renderer.clear_layout()
        y = start_y
        content_start_y = start_y
        prev_block_type = None
        first_block = True  # Track if this is the first block

        for block in blocks:
            block_type = block['type']
            indent_count = block.get('indent_count', 0)  # Get indent count directly
            font_size = self.renderer.get_font_size()
            line_spacing = self.renderer.get_line_spacing()

            # Only apply spacing if this isn't the first block
            if not first_block:
                y -= line_spacing
            first_block = False

            # Handle block-specific layout
            if block_type == 'heading':
                level = block.get('level', 1)
                font_size = self.renderer.get_heading_font_size(level)
                x = start_x + self.get_indent_pixels(indent_count)
                
                # Position text with proper baseline offset
                text_y = y - font_size  # Move baseline down by font size to avoid overlap
                
                segments = block['segments']
                for segment in segments:
                    if len(segment) == 2:  # Normal text or bold
                        style, segment_text = segment
                        font_id = self.renderer.draw.get_heading_font_id(level)
                        blf.size(font_id, font_size)
                        self.renderer.add_layout_instruction({
                            'type': 'text',
                            'text': segment_text,
                            'x': x,
                            'y': text_y,
                            'font_id': font_id,
                            'font_size': font_size,
                            'color': self.renderer.color_main_variation
                        })
                        x += blf.dimensions(font_id, segment_text)[0]
                    elif len(segment) == 3:  # Link
                        style, segment_text, url = segment
                        font_id = self.renderer.draw.get_heading_font_id(level)
                        blf.size(font_id, font_size)
                        text_width = blf.dimensions(font_id, segment_text)[0]
                        
                        # Store link rectangle for click detection with padding
                        # Fix: Adjust the y-coordinate to properly center the clickable area on the text
                        self.renderer.add_link(
                            url, 
                            x - self.link_padding, 
                            text_y + font_size/2,  # Center the clickable area vertically on the text
                            text_width + (self.link_padding * 2), 
                            font_size + (self.link_padding * 2)
                        )
                        
                        self.renderer.add_layout_instruction({
                            'type': 'text',
                            'text': segment_text,
                            'x': x,
                            'y': text_y,
                            'font_id': font_id,
                            'font_size': font_size,
                            'color': self.renderer.color_accent,
                            'is_link': True,
                            'url': url
                        })
                        x += text_width
                
                # Move down by font size plus spacing
                y = text_y - line_spacing

            elif block_type == 'list_item':
                # Position text with proper baseline offset
                text_y = y - font_size  # Move baseline down by font size to avoid overlap
                
                bullet_x = start_x + self.get_indent_pixels(indent_count)
                text_x = bullet_x + self.pixels_per_indent
                
                # Add bullet point
                self.renderer.add_layout_instruction({
                    'type': 'text',
                    'text': '•',
                    'x': bullet_x,
                    'y': text_y,
                    'font_id': self.renderer.draw.regular_font_id,
                    'font_size': font_size,
                    'color': self.renderer.color_main
                })

                # Add text
                x = text_x
                segments = block['segments']
                for segment in segments:
                    if len(segment) == 2:  # Normal text or bold
                        style, segment_text = segment
                        font_id = self.renderer.draw.get_font_id(style)
                        self.renderer.add_layout_instruction({
                            'type': 'text',
                            'text': segment_text,
                            'x': x,
                            'y': text_y,
                            'font_id': font_id,
                            'font_size': font_size,
                            'color': self.renderer.color_main
                        })
                        blf.size(font_id, font_size)
                        x += blf.dimensions(font_id, segment_text)[0]
                    elif len(segment) == 3:  # Link
                        style, segment_text, url = segment
                        font_id = self.renderer.draw.get_font_id(style)
                        blf.size(font_id, font_size)
                        text_width = blf.dimensions(font_id, segment_text)[0]
                        
                        # Store link rectangle for click detection with padding
                        # Fix: Adjust the y-coordinate to properly center the clickable area on the text
                        self.renderer.add_link(
                            url, 
                            x - self.link_padding, 
                            text_y + font_size/2,  # Center the clickable area vertically on the text
                            text_width + (self.link_padding * 2), 
                            font_size + (self.link_padding * 2)
                        )
                        
                        self.renderer.add_layout_instruction({
                            'type': 'text',
                            'text': segment_text,
                            'x': x,
                            'y': text_y,
                            'font_id': font_id,
                            'font_size': font_size,
                            'color': self.renderer.color_accent,
                            'is_link': True,
                            'url': url
                        })
                        x += text_width

                # Update y position for next element
                y = text_y

            elif block_type == 'paragraph':
                # Adjust paragraph layout to use proper baseline positioning
                lines, new_y = self.layout_paragraph(
                    block['text'],
                    start_x, y - font_size,  # Start with baseline offset
                    max_width,
                    font_size=font_size,
                    indent_count=indent_count
                )
                y = new_y

                for segments, lx, ly in lines:
                    x = lx
                    for segment in segments:
                        if len(segment) == 2:  # Normal text or bold
                            text, style = segment
                            font_id = self.renderer.draw.get_font_id(style)
                            self.renderer.add_layout_instruction({
                                'type': 'text',
                                'text': text,
                                'x': x,
                                'y': ly,
                                'font_id': font_id,
                                'font_size': font_size,
                                'color': self.renderer.color_main
                            })
                            blf.size(font_id, font_size)
                            x += blf.dimensions(font_id, text)[0]
                        elif len(segment) == 3:  # Link
                            text, style, url = segment
                            font_id = self.renderer.draw.get_font_id(style)
                            blf.size(font_id, font_size)
                            text_width = blf.dimensions(font_id, text)[0]
                            
                            # Store link rectangle for click detection with padding
                            # Fix: Adjust the y-coordinate to properly center the clickable area on the text
                            self.renderer.add_link(
                                url, 
                                x - self.link_padding, 
                                ly + font_size/2,  # Center the clickable area vertically on the text
                                text_width + (self.link_padding * 2), 
                                font_size + (self.link_padding * 2)
                            )
                            
                            self.renderer.add_layout_instruction({
                                'type': 'text',
                                'text': text,
                                'x': x,
                                'y': ly,
                                'font_id': font_id,
                                'font_size': font_size,
                                'color': self.renderer.color_accent,
                                'is_link': True,
                                'url': url
                            })
                            x += text_width

            elif block_type == 'code':
                code_lines = block['text'].split('\n')
                if not code_lines:
                    continue
                    
                code_font_size = self.renderer.get_code_font_size()
                line_spacing = self.renderer.get_line_spacing()
                code_x = start_x + self.get_indent_pixels(indent_count)
                padding = line_spacing * 0.75

                # Calculate available width for text
                available_width = max_width - self.get_indent_pixels(indent_count) - (padding * 2)

                # Calculate the width of the first line to use as reference
                blf.size(self.renderer.draw.regular_font_id, code_font_size)
                first_line_width = blf.dimensions(self.renderer.draw.regular_font_id, code_lines[0])[0] if code_lines else 0
                
                # Ensure minimum width is first line width or available width, whichever is smaller
                target_width = min(first_line_width, available_width)

                # Process each line
                current_y = y
                wrapped_lines = []
                
                for line in code_lines:
                    if not line.strip():
                        wrapped_lines.append("")
                        continue

                    blf.size(self.renderer.draw.regular_font_id, code_font_size)
                    line_width = blf.dimensions(self.renderer.draw.regular_font_id, line)[0]
                    if line_width > target_width:
                        current_part = ""
                        for char in line:
                            test_width = blf.dimensions(self.renderer.draw.regular_font_id, current_part + char)[0]
                            if test_width <= target_width:
                                current_part += char
                            else:
                                wrapped_lines.append(current_part)
                                current_part = char
                        if current_part:
                            wrapped_lines.append(current_part)
                    else:
                        wrapped_lines.append(line)

                # Draw backgrounds and text
                for line in wrapped_lines:
                    text_y = current_y - code_font_size  # Position text baseline
                    
                    if line.strip():
                        # Add background for this specific line
                        self.renderer.add_layout_instruction({
                            'type': 'code_line_bg',
                            'x': code_x - padding,
                            'y': text_y,  # Align background with text baseline
                            'width': target_width + padding * 2,
                            'height': code_font_size + padding,
                            'color': self.renderer.color_code_background
                        })
                        
                        # Add the text
                        self.renderer.add_layout_instruction({
                            'type': 'code',
                            'text': line,
                            'x': code_x,
                            'y': text_y,
                            'font_id': self.renderer.draw.regular_font_id,
                            'font_size': code_font_size,
                            'color': self.renderer.color_main
                        })
                    
                    current_y = text_y - line_spacing
                
                y = current_y

            elif block_type == 'hr':
                y -= line_spacing
                # Draw HR across full width regardless of indentation
                self.renderer.add_layout_instruction({
                    'type': 'hr',
                    'x': start_x,
                    'y': y,
                    'width': max_width,
                    'color': self.renderer.color_main_variation
                })
                y -= line_spacing

            elif block_type == 'image':
                y -= self.renderer.get_paragraph_spacing()
                
                image = self.renderer.draw.get_image(block['path'])
                if (image):
                    aspect = image.size[1] / image.size[0]
                    indent_px = self.get_indent_pixels(indent_count)
                    width = min(max_width - indent_px, image.size[0])
                    height = width * aspect
                    
                    self.renderer.add_layout_instruction({
                        'type': 'image',
                        'path': block['path'],
                        'x': start_x + indent_px,
                        'y': y,
                        'max_width': max_width - indent_px,
                        'height': height
                    })
                    y -= height
                    y -= self.renderer.get_paragraph_spacing()

            elif block_type == 'blank_line':
                y -= (font_size + line_spacing)

            prev_block_type = block_type

        total_height = content_start_y - y
        return total_height
