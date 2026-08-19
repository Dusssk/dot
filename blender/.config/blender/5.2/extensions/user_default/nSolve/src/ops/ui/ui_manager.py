import bpy

class UIManager:
    _active_header = None
    _active_text = None

    @classmethod
    def set_active_header(cls, operator):
        """Set the active header operator, closing any previous header"""
        try:
            if cls._active_header is not None and cls._active_header != operator:
                # Cancel the previous operator
                if not cls._active_header._timer:  # Check if timer is already removed
                    cls._active_header = None
                    return
                
                bpy.context.window_manager.event_timer_remove(cls._active_header._timer)
                cls._active_header.cancel(bpy.context)
                cls._active_header = None
        except (ReferenceError, AttributeError):
            # Operator was already removed, just clear it
            cls._active_header = None
        
        cls._active_header = operator

    @classmethod
    def set_active_text(cls, operator):
        """Set the active text operator, closing any previous text"""
        try:
            if cls._active_text is not None and cls._active_text != operator:
                # Cancel the previous operator
                if not cls._active_text._timer:  # Check if timer is already removed
                    cls._active_text = None
                    return
                    
                bpy.context.window_manager.event_timer_remove(cls._active_text._timer)
                cls._active_text.cancel(bpy.context)
                cls._active_text = None
        except (ReferenceError, AttributeError):
            # Operator was already removed, just clear it
            cls._active_text = None
        
        cls._active_text = operator

    @classmethod
    def clear_active_header(cls, operator):
        """Clear the active header operator if it matches the given one"""
        if cls._active_header == operator:
            cls._active_header = None

    @classmethod
    def clear_active_text(cls, operator):
        """Clear the active text operator if it matches the given one"""
        if cls._active_text == operator:
            cls._active_text = None
