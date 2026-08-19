import bpy
from .... import __package__ as base_package
from ....utils import addon


class NSOLVE_PT_Options(bpy.types.Panel):
    bl_idname = 'NSOLVE_PT_Options'
    bl_label = "nSolve Options"
    bl_description = "Panel containing nSolve options"
    bl_space_type = 'VIEW_3D'
    bl_ui_units_x = 12
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout

        pref = context.preferences.addons[base_package].preferences

        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = True
        col.label(text="General")

        col.prop(pref, 'menus', text='Topbar Menu')
        if pref.menus:
            col.prop(pref, 'menus_type', text='Menu Type')

        nsolve = addon.pref().tools.nsolve
        interface_options = nsolve.InterfaceOptions
        col.prop(nsolve, 'expanded', text='Expanded Gizmo')
        col.prop(nsolve, 'main_gizmo_skip_alt', text='Disable Alt Scroll')

        nsuite = addon.pref().tools.nsuite
        col.prop(nsuite, 'continuous_cut')

        # Interface Options
        col = layout.column(align=True)
        col.use_property_split = True
        col.label(text="Interface")

        interface_options = nsolve.InterfaceOptions
        col.prop(interface_options, 'enable_banner', text='Banner ')
        col.prop(interface_options, 'show_interface', text='Interface ')
        #col.prop(interface_options, 'show_header', text='Header ')
        if interface_options.show_interface:
            col.prop(interface_options, 'gizmo_enabled', text='nSolve Label')
            col.separator()
            # if interface_options.enable_animation:
            #     col.prop(interface_options, 'enable_animation', text='Enable Animation')
            #     col.prop(interface_options, 'extra_animation', text='Extra Animation')
        #if interface_options.show_header:
            #col.prop(interface_options, 'enable_header_animation', text='Header Animation')


        if nsolve.nsu.hide:
            col = layout.column(align=True)
            col.use_property_split = True
            col.label(text="Gizmo")

            col.prop(nsuite, 'nsu_edit_mode', text='Edit Mode')

        col.separator()
        analyze = addon.pref().ops.mesh.analyze
        col.label(text="Analyze")
        col.prop(analyze, 'show_interface', text='Statistics')
        col.prop(analyze, 'show_fliped', text='Fliped Normals')
