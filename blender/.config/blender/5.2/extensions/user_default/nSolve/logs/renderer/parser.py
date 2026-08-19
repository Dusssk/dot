import os


class MarkdownParser:
    def __init__(self, renderer):
        self.renderer = renderer

    def parse_emphasis(self, text, strip_spaces=True):
        """Parse bold and italic text
        Args:
            text: Text to parse
            strip_spaces: If True, strip leading/trailing spaces before parsing
        """
        if strip_spaces:
            text = text.strip()
        
        segments = []
        current_pos = 0
        text_length = len(text)

        while current_pos < text_length:
            # Find next bold marker
            bold_start = text.find('**', current_pos)
            # Find next link marker
            link_start = text.find('[', current_pos)
            
            # Determine which comes first, bold or link
            first_marker = float('inf')
            marker_type = None
            if bold_start != -1:
                first_marker = bold_start
                marker_type = 'bold'
            
            if link_start != -1 and link_start < first_marker:
                first_marker = link_start
                marker_type = 'link'
                
            # If no more markers, add remaining text as normal and break
            if marker_type is None:
                if current_pos < text_length:
                    segments.append(('normal', text[current_pos:]))
                break
            
            # Add text before marker as normal text
            if first_marker > current_pos:
                segments.append(('normal', text[current_pos:first_marker]))
            
            if marker_type == 'bold':
                # Find closing bold marker
                bold_end = text.find('**', bold_start + 2)
                if bold_end == -1:
                    # No closing marker found, treat rest as normal text
                    segments.append(('normal', text[bold_start:]))
                    break
                
                # Add the bold text
                bold_text = text[bold_start + 2:bold_end]
                if bold_text:  # Only add if there's text between markers
                    segments.append(('bold', bold_text))
                
                current_pos = bold_end + 2
            elif marker_type == 'link':
                # Find closing markers for link
                text_end = text.find(']', link_start)
                url_start = text.find('(', text_end) if text_end != -1 else -1
                url_end = text.find(')', url_start) if url_start != -1 else -1
                
                if text_end == -1 or url_start == -1 or url_end == -1 or text_end + 1 != url_start:
                    # Invalid link format, treat as normal text
                    segments.append(('normal', text[link_start:link_start+1]))
                    current_pos = link_start + 1
                    continue
                
                # Extract link text and URL
                link_text = text[link_start + 1:text_end]
                link_url = text[url_start + 1:url_end]
                
                # Add the link
                if link_text:  # Only add if there's text to show
                    segments.append(('link', link_text, link_url))
                
                current_pos = url_end + 1

        return segments if segments else [('normal', text)]

    def _get_indent_count(self, line, is_header=False):
        """Get the exact number of leading spaces
        For headers, we need to handle # characters differently"""
        if not is_header:
            return len(line) - len(line.lstrip())
        
        # For headers, first get spaces before any # characters
        spaces_before_hash = len(line) - len(line.lstrip(' '))
        return spaces_before_hash

    def parse_markdown(self, filepath):
        """Parse markdown file and cache the result"""
        mtime = os.path.getmtime(filepath)
        if (filepath == self.renderer.cached_filepath and
                mtime == self.renderer.cached_mtime and
                self.renderer.cached_text is not None):
            return self.renderer.cached_text

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        self.renderer.cached_filepath = filepath
        self.renderer.cached_mtime = mtime

        blocks = []
        current_block = []
        in_codeblock = False

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            raw_line = lines[i]
            # Calculate indent before stripping to preserve original spacing
            indent_count = self._get_indent_count(raw_line)
            line = raw_line.lstrip()
            
            if not line:  # Empty line
                if current_block:
                    blocks.append({
                        'type': 'paragraph',
                        'text': '\n'.join(current_block).rstrip(),
                        'indent_count': self._get_indent_count(current_block[0])
                    })
                    current_block = []
                blocks.append({'type': 'blank_line'})
                i += 1
                continue

            # For all block types, use indent_count
            if line.startswith('-'):  # List items
                if current_block:
                    blocks.append({
                        'type': 'paragraph',
                        'text': '\n'.join(current_block).rstrip(),
                        'indent_count': self._get_indent_count(current_block[0])
                    })
                    current_block = []

                list_text = line[1:].strip()
                blocks.append({
                    'type': 'list_item',
                    'text': list_text,
                    'segments': self.parse_emphasis(list_text),
                    'indent_count': indent_count
                })
                i += 1
                continue

            elif line.startswith('#'):  # Headings
                if current_block:
                    blocks.append({
                        'type': 'paragraph',
                        'text': '\n'.join(current_block).rstrip(),
                        'indent_count': self._get_indent_count(current_block[0])
                    })
                    current_block = []

                # Calculate indent specifically for headers
                header_indent = self._get_indent_count(raw_line, is_header=True)
                level = len(line) - len(line.lstrip('#'))
                text = line[level:].strip()
                blocks.append({
                    'type': 'heading',
                    'level': level,
                    'segments': self.parse_emphasis(text),
                    'indent_count': header_indent
                })
                i += 1
                continue

            elif line.startswith('!['):  # Images
                if current_block:
                    blocks.append({
                        'type': 'paragraph',
                        'text': '\n'.join(current_block).rstrip(),
                        'indent_count': self._get_indent_count(current_block[0])
                    })
                    current_block = []

                start_alt = raw_line.find('[') + 1
                end_alt = raw_line.find(']')
                start_path = raw_line.find('(') + 1
                end_path = raw_line.find(')')
                
                if start_alt > 0 and end_alt > 0 and start_path > 0 and end_path > 0:
                    alt_text = raw_line[start_alt:end_alt]
                    image_path = raw_line[start_path:end_path]
                    if not os.path.isabs(image_path):
                        base_dir = os.path.dirname(filepath)
                        image_path = os.path.join(base_dir, image_path)
                    
                    blocks.append({
                        'type': 'image',
                        'alt': alt_text,
                        'path': image_path,
                        'indent_count': indent_count
                    })
                i += 1
                continue

            elif '```' in line:  # Code blocks
                opening_pos = line.find('```')
                closing_pos = line.find('```', opening_pos + 3)
                
                if closing_pos > -1:  # Single-line code block
                    # Handle any text before the code block
                    if opening_pos > 0:
                        pre_text = line[:opening_pos].strip()
                        if pre_text:
                            blocks.append({
                                'type': 'paragraph',
                                'text': pre_text,
                                'indent_count': indent_count
                            })
                    
                    # Extract and add the code block
                    code_content = line[opening_pos + 3:closing_pos].strip()
                    blocks.append({
                        'type': 'code',
                        'text': code_content,
                        'indent_count': indent_count
                    })
                    
                    # Handle any text after the code block
                    post_text = line[closing_pos + 3:].strip()
                    if post_text:
                        blocks.append({
                            'type': 'paragraph',
                            'text': post_text,
                            'indent_count': indent_count
                        })
                    i += 1
                    continue
                elif in_codeblock:  # End of multi-line code block
                    if current_block:
                        blocks.append({
                            'type': 'code',
                            'text': '\n'.join(current_block).rstrip(),
                            'indent_count': indent_count
                        })
                    current_block = []
                    in_codeblock = False
                else:  # Start of multi-line code block
                    if current_block:
                        blocks.append({
                            'type': 'paragraph',
                            'text': '\n'.join(current_block),
                            'indent_count': indent_count
                        })
                    current_block = []
                    in_codeblock = True
                i += 1
                continue

            elif in_codeblock:
                current_block.append(line)
                i += 1
                continue

            elif line.startswith('---') or line.startswith('***') or line.startswith('___'):  # Horizontal rule
                if current_block:
                    blocks.append({
                        'type': 'paragraph',
                        'text': '\n'.join(current_block).rstrip(),
                        'indent_count': self._get_indent_count(current_block[0])
                    })
                    current_block = []
                # Create a line of underscores that spans the full width
                blocks.append({
                    'type': 'paragraph',
                    'text': '_' * 120,  # Long enough to span typical widths
                    'segments': [('normal', '_' * 120)],
                    'indent_count': 0  # No indentation for full-width effect
                })
                i += 1
                continue

            elif line.startswith('|') and line.endswith('|'):  # Tables
                if current_block:
                    blocks.append({
                        'type': 'paragraph',
                        'text': '\n'.join(current_block).rstrip(),
                        'indent_count': self._get_indent_count(current_block[0])
                    })
                    current_block = []
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                blocks.append({
                    'type': 'table_row',
                    'cells': cells,
                    'indent_count': indent_count
                })
                i += 1
                continue

            # Handle regular text
            if current_block and self._get_indent_count(current_block[0]) != indent_count:
                blocks.append({
                    'type': 'paragraph',
                    'text': '\n'.join(current_block).rstrip(),
                    'indent_count': self._get_indent_count(current_block[0])
                })
                current_block = []

            # For regular text, create a block for each line
            if current_block:
                blocks.append({
                    'type': 'paragraph',
                    'text': current_block[0].rstrip(),
                    'indent_count': self._get_indent_count(current_block[0])
                })
                current_block = []
            
            blocks.append({
                'type': 'paragraph',
                'text': raw_line.rstrip(),
                'indent_count': indent_count
            })
            i += 1

        # Add final block if any
        if current_block:
            block_type = 'code' if in_codeblock else 'paragraph'
            blocks.append({
                'type': block_type,
                'text': current_block[0].rstrip(),
                'indent_count': self._get_indent_count(current_block[0])
            })
        
        self.renderer.cached_text = blocks
        return blocks
