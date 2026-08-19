def refresh_gizmo(self, context):
    if context is None or not hasattr(context, 'screen') or context.screen is None:
        return
        
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            current_state = space.show_gizmo
            space.show_gizmo = not current_state  # Toggle to force gizmo refresh
            space.show_gizmo = current_state
