import os
import webbrowser
from bpy.types import SpaceView3D, Operator, Event
from .renderer import MarkdownRenderer


class NSOLVE_OT_ShowLogs(Operator):
    """Show changelog and logs in the 3D viewport (ESC to close)"""

    bl_idname = "nsolve.show_logs"
    bl_label = "Show Logs"
    bl_description = "Show changelog and logs in the 3D viewport (ESC to close)"
    bl_options = {'REGISTER', 'BLOCKING'}

    _renderer = None
    _timer = None
    _last_width = 0
    _last_height = 0
    _draw_handle = None  # Store the actual handle here
    _wrapped_callback = None  # Store the wrapped callback
    _scroll_offset = 0
    _scroll_speed = 30  # Pixels per scroll
    _content_height = 0
    _last_mouse_x = 0  # Track last mouse position
    _last_mouse_y = 0
    _is_dragging_scrollbar = False  # Track if user is dragging the scrollbar
    _drag_start_y = 0  # Y position where drag started
    _drag_start_offset = 0  # Scroll offset when drag started

    @classmethod
    def setup_renderer(cls):
        if cls._renderer is None:
            cls._renderer = MarkdownRenderer()

    def check_resize(self, context):
        """Check if the window has been resized"""
        region = context.region
        width, height = region.width, region.height

        if width != self._last_width or height != self._last_height:
            self._last_width = width
            self._last_height = height
            return True
        return False
        
    def is_mouse_over_scrollbar(self, context, mouse_x, mouse_y):
        """Check if the mouse is over the scrollbar"""
        region = context.region
        margin_x = region.width * self._renderer.margin_size_x
        margin_y = region.height * self._renderer.margin_size_y
        
        # Calculate content width
        content_width = min(self._renderer.max_content_width, region.width)
        if content_width < region.width:
            margin_x = (region.width - content_width) / 2
            
        # Calculate scrollbar position with spacing from content
        scrollbar_spacing = 15  # Same as in draw.py
        scrollbar_width = 10
        
        # Determine if we need a scrollbar (simplified check)
        needs_scrollbar = True  # We'll assume we need it
        
        # Calculate effective content width
        if needs_scrollbar:
            effective_content_width = content_width - scrollbar_width - scrollbar_spacing
        else:
            effective_content_width = content_width
            
        # Calculate scrollbar position
        scrollbar_x = margin_x + effective_content_width + scrollbar_spacing
        
        # Check if mouse is over scrollbar
        return (scrollbar_x <= mouse_x <= scrollbar_x + scrollbar_width and
                margin_y <= mouse_y <= region.height - margin_y)
    
    def update_scroll_from_drag(self, context, mouse_y):
        """Update scroll position based on drag position"""
        region = context.region
        margin_y = region.height * self._renderer.margin_size_y
        
        # Calculate visible area
        visible_height = region.height - (margin_y * 2)
        
        # Calculate max scroll
        max_scroll = max(0, abs(self._content_height - visible_height))
        if max_scroll == 0:
            return
            
        # Calculate drag distance
        drag_distance = self._drag_start_y - mouse_y
        
        # Calculate scroll ratio
        scroll_ratio = drag_distance / visible_height
        
        # Calculate new scroll offset
        new_offset = self._drag_start_offset + (scroll_ratio * max_scroll)
        
        # Clamp scroll offset
        self._scroll_offset = max(0, min(max_scroll, new_offset))

    def modal(self, context, event):
        if event.type == 'ESC':
            self.cancel(context)
            context.area.tag_redraw()
            return {'CANCELLED'}

        # Get mouse position relative to region
        mouse_x = event.mouse_x - context.region.x
        mouse_y = event.mouse_y - context.region.y

        # Track mouse position for cursor changes
        if event.type == 'MOUSEMOVE':
            self._last_mouse_x = event.mouse_x
            self._last_mouse_y = event.mouse_y
            
            # Handle scrollbar dragging
            if self._is_dragging_scrollbar:
                self.update_scroll_from_drag(context, mouse_y)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
                
            # Check if mouse is over scrollbar and update cursor
            if self.is_mouse_over_scrollbar(context, mouse_x, mouse_y):
                context.window.cursor_modal_set('SCROLL_Y')
            else:
                # Update cursor based on whether mouse is over a link
                is_over_link = self._renderer.update_cursor_for_link(context, mouse_x, mouse_y)
                # If not over a link, ensure cursor is set to default
                if not is_over_link:
                    context.window.cursor_modal_set('DEFAULT')

        # Handle scrollbar interaction
        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                # Check if clicking on scrollbar
                if self.is_mouse_over_scrollbar(context, mouse_x, mouse_y):
                    self._is_dragging_scrollbar = True
                    self._drag_start_y = mouse_y
                    self._drag_start_offset = self._scroll_offset
                    context.window.cursor_modal_set('SCROLL_Y')
                    return {'RUNNING_MODAL'}
            elif event.value == 'RELEASE':
                # End scrollbar dragging
                if self._is_dragging_scrollbar:
                    self._is_dragging_scrollbar = False
                    # Check what's under the mouse after releasing
                    if self.is_mouse_over_scrollbar(context, mouse_x, mouse_y):
                        context.window.cursor_modal_set('SCROLL_Y')
                    else:
                        # Check if over a link, otherwise set to default
                        is_over_link = self._renderer.update_cursor_for_link(context, mouse_x, mouse_y)
                        if not is_over_link:
                            context.window.cursor_modal_set('DEFAULT')
                    return {'RUNNING_MODAL'}
                    
                # Check if the mouse is over a link
                url = self._renderer.get_link_at_position(mouse_x, mouse_y)
                if url:
                    # Open the link in the default web browser
                    webbrowser.open(url)
                    return {'RUNNING_MODAL'}
                # Continue with normal modal behavior if not clicking a link
                self.cancel(context)
                context.area.tag_redraw()
                return {'CANCELLED'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'UP_ARROW', 'DOWN_ARROW'}:
            region = context.region
            margin_y = region.height * self._renderer.margin_size_y

            # Calculate visible area
            visible_height = region.height - (margin_y * 2)
            
            # Calculate max scroll - this is the difference between content height and visible area
            # We subtract the visible height from content height to get how much we can scroll
            max_scroll = max(0, abs(self._content_height - visible_height))

            # Reversed scroll logic: up means scrolling down (decreasing offset)
            if event.type in {'WHEELUPMOUSE', 'UP_ARROW'}:
                self._scroll_offset = max(0, self._scroll_offset - self._scroll_speed)
            else:
                # Only allow scrolling down if we haven't reached the end of content
                if self._scroll_offset < max_scroll:
                    self._scroll_offset = min(max_scroll, self._scroll_offset + self._scroll_speed)
                    
            # After scrolling, update the cursor state since the links will have moved
            self._renderer.update_cursor_for_link(
                context, 
                self._last_mouse_x - context.region.x,
                self._last_mouse_y - context.region.y
            )

            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'TIMER':
            if self.check_resize(context):
                # Reset scroll position on resize to prevent out-of-bounds
                self._scroll_offset = 0
                # Reset cursor state when resizing
                self._renderer._is_cursor_over_link = False
                # Reset scrollbar dragging state
                self._is_dragging_scrollbar = False
                # Reset cursor to default
                context.window.cursor_modal_set('DEFAULT')
                # Force a redraw
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()

        return {'RUNNING_MODAL'}

    def invoke(self, context, _event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a 3D View")
            return {'CANCELLED'}

        # Initialize mouse tracking
        self._last_mouse_x = 0
        self._last_mouse_y = 0
        
        # Initialize scrollbar state
        self._is_dragging_scrollbar = False
        self._drag_start_y = 0
        self._drag_start_offset = 0
        
        self.execute(context)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.setup_renderer()

        # Initialize window size tracking
        region = context.region
        self._last_width = region.width
        self._last_height = region.height

        # Reset scroll position
        self._scroll_offset = 0

        # Reset cursor state
        if self._renderer:
            self._renderer._is_cursor_over_link = False

        # Set margin to match the background margin
        self._renderer._margin = region.height * 0.2

        # Get the logs.md file path from the main addon folder - going up 4 levels from ops/ui/logs/logs.py
        addon_path = os.path.dirname(__file__)
        logs_path = os.path.join(addon_path, 'logs.md')

        if not os.path.exists(logs_path):
            self.report({'ERROR'}, "Logs file not found")
            return {'CANCELLED'}

        # Set the file path for the renderer
        self._renderer.filepath = logs_path

        # Add the draw handler if not already added
        if self._draw_handle is None:
            def wrapped_callback(context):
                self._content_height = self._renderer.draw_callback(context, self._scroll_offset)

            self._wrapped_callback = wrapped_callback
            self._draw_handle = SpaceView3D.draw_handler_add(
                wrapped_callback, (context,), 'WINDOW', 'POST_PIXEL'
            )
            self._renderer.draw_handle = True  # Just use as a flag

        # Add timer for continuous updates
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        # Reset cursor to default when closing
        context.window.cursor_modal_set('DEFAULT')
        
        # Reset scrollbar state
        self._is_dragging_scrollbar = False
        
        if self._draw_handle is not None:
            SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            self._wrapped_callback = None
            self._renderer.draw_handle = None

        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None


classes = (NSOLVE_OT_ShowLogs,)
