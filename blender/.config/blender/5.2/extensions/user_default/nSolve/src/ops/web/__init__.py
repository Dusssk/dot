import bpy

from .... import bl_info


class NSOLVE_OT_help_link(bpy.types.Operator):
    bl_idname = 'nsolve.help_link'
    bl_label = 'Visit Documentation Website'
    bl_description = '\n Ctrl - nSolve Discord Community\n\nShift - nSolve Docs'

    url: bpy.props.StringProperty(
        name = 'Help URL',
        description = 'nSolve help URL to visit',
        default = bl_info['wiki_url'])

    use_url: bpy.props.BoolProperty(default=False)

    def invoke(self, context, event):
        use_url = False
        if event.ctrl and not self.use_url:
            self.url = 'https://discord.gg/BnSPbg4p'
            use_url = True
        if event.shift and not self.use_url:
            self.url = bl_info['wiki_url']
            use_url = True
        elif self.use_url:
            use_url = True

        # NSOLVE_PT_help is currently not implemented
        # if not use_url:
        #     bpy.ops.wm.call_panel(name='NSOLVE_PT_help', keep_open=True)
        #     return {"FINISHED"}

        bpy.ops.wm.url_open(url=self.url)

        return {"FINISHED"}


classes = (
    NSOLVE_OT_help_link,
)
