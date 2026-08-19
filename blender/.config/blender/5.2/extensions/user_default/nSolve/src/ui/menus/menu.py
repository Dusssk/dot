import bpy
from .... import bl_info


class NSOLVE_MT_MainMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_MainMenu"
    bl_label = f"nSolve: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        nsolve_tool = True if active_tool and active_tool.idname == 'nsolve.nsolvetool' else False
        nsuite_tool = True if active_tool and active_tool.idname == 'nsolve.nsuitetool' else False
        nflow_tool = True if active_tool and active_tool.idname == 'nsolve.nflow_edit_mode' else False

        if nsolve_tool:
            layout.menu("NSOLVE_MT_NsoMenu", text="    nSolve")
            layout.operator("wm.tool_set_by_id", text="nSuite").name = 'nsolve.nsuitetool'
            layout.operator("wm.tool_set_by_id", text="nFlow").name = 'nsolve.nflow_edit_mode'

        elif nsuite_tool:
            layout.operator("wm.tool_set_by_id", text="nSolve").name = 'nsolve.nsolvetool'
            layout.operator("wm.tool_set_by_id", text="nFlow").name = 'nsolve.nflow_edit_mode'        

        elif nflow_tool:
            layout.operator("wm.tool_set_by_id", text="nSolve").name = 'nsolve.nsolvetool'
            layout.operator("wm.tool_set_by_id", text="nSuite").name = 'nsolve.nsuitetool'

        else:
            layout.operator("wm.tool_set_by_id", text="nSolve").name = 'nsolve.nsolvetool'
            layout.operator("wm.tool_set_by_id", text="nSuite").name = 'nsolve.nsuitetool'
            layout.operator("wm.tool_set_by_id", text="nFlow").name = 'nsolve.nflow_edit_mode'

        layout.separator()
        layout.operator("nsolve.hard_loop_cut").release_confirm = False
        layout.operator("mesh.loopcut_slide").TRANSFORM_OT_edge_slide.release_confirm = False
        layout.separator()
        layout.operator("nsolve.hard_edge_slide")
        layout.operator("nsolve.offset_edges")
        layout.separator()
        layout.operator("nsolve.bevel")
        layout.separator()
        layout.operator("nsolve.mesh_cut")
        layout.separator()
        layout.menu("NSOLVE_MT_ProjectMenu", text="Project")
        layout.separator()
        analyzetext = "Analyze (OFF)" if bpy.context.scene.nsolve.ops.mesh.analyze.running else "Analyze (ON)"
        layout.operator("nsolve.analyze", text=analyzetext)
        layout.separator()
        layout.operator_context = "EXEC_DEFAULT"
        layout.menu("NSOLVE_MT_SelectMenu", text="Select")

        # layout.separator()
        # layout.menu("NSOLVE_MT_FilesMenu", text="Examples")
