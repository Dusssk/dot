import bpy

from . import circle
from . import grid
from . import line
from . import loop
from . import mesh
from . import rake


class types():
    class theme(bpy.types.PropertyGroup):
        circle: bpy.props.PointerProperty(type=circle.types.theme)
        grid: bpy.props.PointerProperty(type=grid.types.theme)
        line: bpy.props.PointerProperty(type=line.types.theme)
        loop: bpy.props.PointerProperty(type=loop.types.theme)
        rake: bpy.props.PointerProperty(type=rake.types.theme)


types_classes = (
    *circle.types_classes,
    *grid.types_classes,
    *line.types_classes,
    *loop.types_classes,
    *rake.types_classes,
    types.theme,
)

classes = (
    circle.NSOLVE_OT_ProjectCircle,
    grid.NSOLVE_OT_ProjectGrid,
    line.NSOLVE_OT_ProjectLine,
    loop.NSOLVE_OT_ProjectLoop,
    mesh.NSOLVE_OT_ProjectMesh,
    rake.NSOLVE_OT_ProjectRake,
)