import bpy


class NSOLVE_MT_ProjectMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_ProjectMenu"
    bl_label = "Project"

    def draw(self, _context):
        layout = self.layout

        layout.operator("nsolve.project_line").mouse_init = False
        layout.operator("nsolve.project_loop", text="Project Loop").mode = 'OFFSET'
        layout.operator("nsolve.project_circle")
        layout.operator("nsolve.project_grid")
        layout.operator("nsolve.project_rake")
