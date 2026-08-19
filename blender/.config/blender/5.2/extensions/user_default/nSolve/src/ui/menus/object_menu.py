import bpy
from .... import bl_info


class NSOLVE_MT_ObjectMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_ObjectMenu"
    bl_label = f"nSolve: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"

    def draw(self, _context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        nsolve_tool = True if active_tool and active_tool.idname == 'nsolve.main_tool' else False
        nflow_tool = True if active_tool and active_tool.idname == 'nsolve.nflow_object_mode' else False

        # layout.operator("nsolve.start_draw", text="nDraw")
        # layout.separator()

        if nsolve_tool:
            layout.operator("wm.tool_set_by_id", text="nFlow").name = 'nsolve.nflow_object_mode'

        elif nflow_tool:
            layout.operator("wm.tool_set_by_id", text="nSolve").name = 'nsolve.main_tool'

        else:
            layout.operator("wm.tool_set_by_id", text="nSolve").name = 'nsolve.main_tool'
            layout.operator("wm.tool_set_by_id", text="nFlow").name = 'nsolve.nflow_object_mode'

        #layout.separator()
        #layout.menu("NSOLVE_MT_FilesMenu", text="Examples")
