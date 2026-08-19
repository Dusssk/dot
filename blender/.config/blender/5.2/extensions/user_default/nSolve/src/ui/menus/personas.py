import bpy

from ....utils import addon


class NSOLVE_MT_PersonasMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_PersonasMenu"
    bl_label = "Personas"

    def draw(self, _context):
        layout = self.layout

        nsolve = addon.pref().tools.nsolve

        if nsolve.personas_list_items:

            for index, item in enumerate(nsolve.personas_list_items):
                layout.operator("nsolve.apply_persona", text=item.persona).index = index

        else:
            layout.label(text="No personas set")
