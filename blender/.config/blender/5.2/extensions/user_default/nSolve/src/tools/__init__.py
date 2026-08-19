import bpy

from . import nsolve
from . import nsuite
from . import nflow
from . import main
from . import ndraw


class types():
    class pref(bpy.types.PropertyGroup):
        nsolve: bpy.props.PointerProperty(type=nsolve.types.pref)
        nsuite: bpy.props.PointerProperty(type=nsuite.types.pref)
        ndraw: bpy.props.PointerProperty(type=ndraw.types.pref)


types_classes = (
    *nsolve.types_classes,
    *nsuite.types_classes,
    *ndraw.types_classes,
    types.pref,
)


classes = (
    *nsolve.classes,
    *nsuite.classes,
    *nflow.classes,
)
