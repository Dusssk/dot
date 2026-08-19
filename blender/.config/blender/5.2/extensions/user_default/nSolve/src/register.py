import bpy
from bpy.utils import register_class, unregister_class, register_tool, unregister_tool
from . import ops, ui, types, preferences, tools, gizmo, keymap, timers, handlers
from .. import logs
from ..icons.menus import load_icons, unload_icons
from ..icons import buttons


classes = (
    *types.classes,
    *preferences.classes,
    *tools.classes,
    *ops.classes,
    *gizmo.classes,
    *ui.classes
    #*logs.classes
)


def register():
    load_icons()
    buttons.load_icons()

    for cls in classes:
        register_class(cls)
    preferences.initialize_pie_operator_list()

    register_tool(tools.main.NSOLVE_MT_Main, separator=True)
    register_tool(tools.nflow.NSOLVE_MT_NFlow_object_mode, after={'nsolve.main_tool'}, group=False)
    register_tool(tools.nflow.NSOLVE_MT_NFlow_edit_mode, separator=False, after={'builtin.transform'}, group=False)
    register_tool(tools.nsuite.NSOLVE_MT_Nsuite, group=True, separator=True, after={'builtin.transform'})
    # register_tool(tools.ndraw.NSOLVE_MT_Ndraw, after={'nsolve.nsuitetool'}, group=False)
    register_tool(tools.nsolve.NSOLVE_MT_NSolve, after={'nsolve.nsuitetool'}, group=False)

    types.register()
    keymap.register()
    timers.register()
    handlers.register()

def unregister():

    unload_icons()
    buttons.unload_icons()
    timers.unregister()
    keymap.unregister()
    handlers.unregister()

    unregister_tool(tools.nsuite.NSOLVE_MT_Nsuite)
    # unregister_tool(tools.ndraw.NSOLVE_MT_Ndraw)
    unregister_tool(tools.nsolve.NSOLVE_MT_NSolve)
    unregister_tool(tools.main.NSOLVE_MT_Main)
    unregister_tool(tools.nflow.NSOLVE_MT_NFlow_object_mode)
    unregister_tool(tools.nflow.NSOLVE_MT_NFlow_edit_mode)

    for cls in reversed(classes):
        unregister_class(cls)

    # delete gizmo group keymaps
    active_config = bpy.context.preferences.keymap.active_keyconfig
    active_config = bpy.context.window_manager.keyconfigs[active_config]
    for cls in gizmo.group.classes:
        km_name = getattr(cls, 'keymap_name', None)
        if not km_name: continue
        km = active_config.keymaps.get(km_name, None)
        if km:
            active_config.keymaps.remove(km)

    types.unregister()
