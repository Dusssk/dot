import bpy
from . import export
from . import ndraw
from . import select
from . import stamp
from . import mesh
from . import obj
from . import gizmo
from . import nflow
from . import file
from . import web
from . import ui
from . import banner


class types():
    class window_manager(bpy.types.PropertyGroup):
        nflow: bpy.props.PointerProperty(type=nflow.types.window_manager)

    class theme(bpy.types.PropertyGroup):
        mesh: bpy.props.PointerProperty(type=mesh.types.theme)
        ndraw: bpy.props.PointerProperty(type=ndraw.types.theme)

    class scene(bpy.types.PropertyGroup):
        mesh: bpy.props.PointerProperty(type=mesh.types.scene)
        nflow: bpy.props.PointerProperty(type=nflow.types.scene)

    class workspace(bpy.types.PropertyGroup):
        nflow: bpy.props.PointerProperty(type=nflow.types.workspace)

    class pref(bpy.types.PropertyGroup):
        mesh: bpy.props.PointerProperty(type=mesh.types.pref)


types_classes = (
    *nflow.types_classes,
    *mesh.types_classes,
    *ndraw.types_classes,
    types.theme,
    types.scene,
    types.workspace,
    types.window_manager,
    types.pref,
)


classes = (
    *export.classes,
    *nflow.classes,
    *file.classes,
    ndraw.extrude.NSOLVE_OT_PencilExtrude,
    ndraw.fill_quads.NSOLVE_OT_PencilQaud,
    ndraw.pencil.NSOLVE_OT_Pencil,
    ndraw.draw.NSOLVE_OT_NdrawDraw,
    *ui.classes,
    *mesh.classes,
    *obj.classes,
    *select.classes,
    *stamp.classes,
    *gizmo.classes,
    *web.classes,
    *banner.classes,
)


def register():
    nflow.register()


def unregister():
    nflow.unregister()
