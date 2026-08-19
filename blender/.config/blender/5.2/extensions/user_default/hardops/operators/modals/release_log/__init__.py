from bpy.utils import register_class, unregister_class

from . import shader
from . display import HOPS_OT_release_log

classes = (
    HOPS_OT_release_log,
)


def register_release_log():
    for cls in classes:
        register_class(cls)


def unregister_release_log():
    shader.remove_handlers(force=True)

    for cls in classes:
        unregister_class(cls)

