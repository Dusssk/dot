import bpy
from . import analytics, animation


# Global instance
handlers = animation.ViewportHandlers()


def register_corner_draw_handler():
    """Register the corner drawing handler"""
    if handlers.corner_draw_handler is None:
        handlers.corner_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            handlers.draw_corners, (bpy.context,), 'WINDOW', 'POST_PIXEL'
        )


def unregister_corner_draw_handler():
    """Unregister the corner drawing handler"""
    if handlers.corner_draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(handlers.corner_draw_handler, 'WINDOW')
        handlers.corner_draw_handler = None

    if handlers.timer_handler is not None:
        bpy.app.timers.unregister(handlers.timer_handler)
        handlers.timer_handler = None


def register_gizmo_draw_handler():
    """Register the gizmo text drawing handler"""
    if not hasattr(handlers, 'gizmo_draw_handler') or handlers.gizmo_draw_handler is None:
        handlers.gizmo_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            handlers.draw_gizmo, (bpy.context,), 'WINDOW', 'POST_PIXEL'
        )


def unregister_gizmo_draw_handler():
    """Unregister the gizmo text drawing handler"""
    if hasattr(handlers, 'gizmo_draw_handler') and handlers.gizmo_draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(handlers.gizmo_draw_handler, 'WINDOW')
        handlers.gizmo_draw_handler = None


def register_depsgraph_update_post():
    """Handle depsgraph update"""
    bpy.app.handlers.depsgraph_update_post.append(analytics.logs)


def unregister_depsgraph_update_post():
    """Remove depsgraph update handler"""
    bpy.app.handlers.depsgraph_update_post.remove(analytics.logs)


def register():
    """Register all handlers"""
    register_corner_draw_handler()
    register_gizmo_draw_handler()
    register_depsgraph_update_post()


def unregister():
    """Unregister all handlers"""
    unregister_corner_draw_handler()
    unregister_gizmo_draw_handler()
    unregister_depsgraph_update_post()
