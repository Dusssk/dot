import bpy


class NSOLVE_MT_FaceMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_FaceMenu"
    bl_label = "Face"

    def draw(self, _context):
        layout = self.layout

        layout.operator("nsolve.project_circle")
        layout.operator("nsolve.project_grid")
        layout.separator()
        # layout.operator("nsolve.unbevel")
        # layout.separator()
        analyzetext = "Analyze (OFF)" if bpy.context.scene.nsolve.ops.mesh.analyze.running else "Analyze (ON)"
        layout.operator("nsolve.analyze", text=analyzetext)
