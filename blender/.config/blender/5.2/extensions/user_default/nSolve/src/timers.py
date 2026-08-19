import bpy
from . import tools, preferences

timers = [
    (tools.nsolve.initialize_nsolve_tool, 1, False),
    (tools.nsuite.initialize_nsuite_gizmos, 1, False),
    #(preferences.initialize_pie_operator_list, 1, False),
]


def register():
    for f, fi, pers in timers:
        if not bpy.app.timers.is_registered(f):
            bpy.app.timers.register(f, first_interval=fi, persistent=pers)


def unregister():
    for f, *_ in timers:
        if bpy.app.timers.is_registered(f):
            bpy.app.timers.unregister(f)
