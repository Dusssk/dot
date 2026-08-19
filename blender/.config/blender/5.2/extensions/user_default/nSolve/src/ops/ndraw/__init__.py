import bpy

from . import loops
from . import fill_quads
from . import extrude
from . import pencil
from . import draw


class types():
    class theme(bpy.types.PropertyGroup):
        pencil: bpy.props.PointerProperty(type=pencil.types.theme)


types_classes = (
    *pencil.types_classes,
    types.theme,
)
