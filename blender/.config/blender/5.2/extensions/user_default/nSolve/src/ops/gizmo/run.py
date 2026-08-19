import bpy
from ....utils import addon


class NSOLVE_OT_RunGizmo(bpy.types.Operator):
    bl_idname = "nsolve.run_gizmo"
    bl_label = "Run Gizmo"
    bl_description = "Run Operator based on the current gizmo setting"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    state: bpy.props.EnumProperty(
        name="State",
        description="State",
        items=[('MAIN', 'Main', 'Main'), ('AUX', 'Aux', 'Aux'), ('SUB', 'Sub', 'Sub'), ('EXT', 'Ext', 'Ext')],
        default='MAIN'
    )

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    def invoke(self, context, event):

        prop = addon.pref().tools.nsolve

        if self.state == 'MAIN':
            option = prop.main
        elif self.state == 'AUX':
            option = prop.aux
        elif self.state == 'SUB':
            option = prop.sub
        elif self.state == 'EXT':
            option = prop.ext

        operator = option.operator
        select_mode = option.select_mode
        multi_join = option.multi_join
        snap_join = (option.snap_join.vert, option.snap_join.edge, option.snap_join.face, option.snap_join.mid_edge, option.snap_join.perp_edge, option.snap_join.center_face)
        multi_merge = option.multi_merge
        center_merge = option.center_merge
        merge_weld = option.merge_weld
        merge_weld_dist = option.merge_weld_dist
        cut_through = option.line_cut_through
        collapse_affect_selected = option.collapse_affect_selected
        dissolve_use_verts = option.dissolve_use_verts
        dissolve_use_face_split = option.dissolve_use_face_split
        slide_selection_mode = option.slide_selection_mode
        slide_multi_elem = option.slide_multi_elem
        hide_reverse = option.hide_reverse
        hide_volume = option.hide_volume

        if operator == 'SELECT':
            bpy.ops.view3d.select_box('INVOKE_DEFAULT', mode=select_mode)
        elif operator == 'JOIN':
            bpy.ops.nsolve.join_verts('INVOKE_DEFAULT', multi=multi_join, snap_mode=snap_join)
        elif operator == 'MERGE':
            bpy.ops.nsolve.merge_verts('INVOKE_DEFAULT', multi=multi_merge, center_merge=center_merge, merge_weld=merge_weld, merge_weld_dist=merge_weld_dist)
        elif operator == 'SLIDE':
            bpy.ops.nsolve.slide_vert('INVOKE_DEFAULT', selection_mode=slide_selection_mode, multi_elem=slide_multi_elem)
        elif operator == 'LINE':
            bpy.ops.nsolve.project_line('INVOKE_DEFAULT', cut_through=cut_through, draw_text="")
        elif operator == 'COLLAPSE':
            bpy.ops.nsolve.collapse_verts('INVOKE_DEFAULT', detect_vert=True, affect_selected=collapse_affect_selected)
        elif operator == 'DISSOLVE':
            bpy.ops.nsolve.dissolve_edges('INVOKE_DEFAULT', use_verts=dissolve_use_verts, use_face_split=dissolve_use_face_split)
        elif operator == 'OFFSET':
            bpy.ops.nsolve.offset_edges('INVOKE_DEFAULT')
        elif operator == 'KNIFE':
            bpy.ops.mesh.knife_tool('INVOKE_DEFAULT', wait_for_input=False)
        elif operator == 'HIDE':
            bpy.ops.nsolve.hide('INVOKE_DEFAULT', reverse=hide_reverse, volume=hide_volume)

        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text='nSolve')
        bpy.ops.nsolve.banner('INVOKE_DEFAULT', busy=True, operator=operator)

        return self.execute(context)

    def execute(self, context):

        return {'FINISHED'}
