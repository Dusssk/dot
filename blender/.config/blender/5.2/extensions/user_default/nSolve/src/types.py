import bpy
from . import ops, tools

def get_module():
    name = __name__
    id = len(name) - 1
    dot_count = 0

    for c in reversed(name):
        if c == '.':
            dot_count += 1

        if dot_count == 2:
            return name[:id]

        id -= 1



class WindowManager(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.types.window_manager)
    addon: bpy.props.StringProperty(default=get_module())
    nsuite: bpy.props.PointerProperty(type=tools.nsuite.types.window_manager)


class WorkSpace(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.types.workspace)


class Scene(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.types.scene)


class Theme(bpy.types.PropertyGroup):
    ops: bpy.props.PointerProperty(type=ops.types.theme)


classes = [
    *ops.types_classes,
    *tools.types_classes,
    WindowManager,
    WorkSpace,
    Scene,
    Theme,
]


def register():
    bpy.types.WindowManager.nsolve = bpy.props.PointerProperty(type=WindowManager)
    bpy.types.WorkSpace.nsolve = bpy.props.PointerProperty(type=WorkSpace)
    bpy.types.Scene.nsolve = bpy.props.PointerProperty(type=Scene)

    ops.register()


def unregister():
    ops.unregister()

    del bpy.types.WindowManager.nsolve
    del bpy.types.WorkSpace.nsolve
    del bpy.types.Scene.nsolve
