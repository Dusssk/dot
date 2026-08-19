from pathlib import Path
import bpy
from ...utils import addon
from .utils import refresh_gizmo
from .nsuite import nsuite_options
from ...import bl_info
from ...icons.menus import get_icon_id
from ...fonts import FONT_ITEMS


def check_gizmo(context):
    area = context.area
    # Ensure the area is a 3D View
    if area.type == 'VIEW_3D':
        # Find the 'WINDOW' region within the 3D View
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region:

            # Assuming 'nsolve' is set up correctly with main_gizmo_location attributes
            nsolve = addon.pref().tools.nsolve
            locations = [nsolve.main_gizmo_location]

            for location in locations:
                if location[0] < 1 or location[0] > 99 or location[1] < 1 or location[1] > 99:
                    return True

            return False

    return False  # If not a 3D View area or no 'WINDOW' region found


class NSOLVE_MT_NSolve(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'nsolve.nsolvetool'
    bl_label = "nSolve"
    bl_description = f'Version: {bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "tools" / "nsolve").as_posix()
    bl_widget = 'NSOLVE_GGT_Nsolve'
    bl_keymap = (
        ('nsolve.hard_loop_cut', {'type': 'R', 'value': 'PRESS', 'alt': True}, {'properties': [('release_confirm', False)]}),
        ('nsolve.run_gizmo', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': False, 'ctrl': False}, {'properties': []}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True}, {'properties': [('mode', 'ADD')]}),
        ('nsolve.run_gizmo', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True, 'ctrl': False}, {'properties': [('state', 'AUX')]}),
        ('nsolve.run_gizmo', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': False, 'ctrl': True}, {'properties': [('state', 'SUB')]}),
        ('nsolve.run_gizmo', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': False, 'ctrl': False, 'alt': True}, {'properties': [('state', 'EXT')]}),
        ('nsolve.scroll_gizmo', {'type': 'WHEELUPMOUSE', 'value': 'PRESS', 'alt': True}, {'properties': [('mode', 'DOWN')]}),
        ('nsolve.scroll_gizmo', {'type': 'WHEELDOWNMOUSE', 'value': 'PRESS', 'alt': True}, {'properties': [('mode', 'UP')]}),
        ('nsolve.select_smartloop', {'type': 'RIGHTMOUSE', 'value': 'PRESS', 'ctrl': True}, {'properties': []}),
        ('nsolve.select_planarloop', {'type': 'RIGHTMOUSE', 'value': 'PRESS', 'shift': True}, {'properties': []}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):
        layout.operator('nsolve.helper', text='', icon_value=get_icon_id('nSolve'), depress=False)
        layout.label(text=f'{bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}')

        layout.separator()

        layout.popover("NSOLVE_PT_Nsolve", text="", icon='OPTIONS')
        nsolve = addon.pref().tools.nsolve

        sections = ['main', 'aux', 'sub', 'ext']
        labels = [nsolve.main_label, nsolve.aux_label, nsolve.sub_label, nsolve.ext_label]

        for section in sections:
            row = layout.row(align=True)

            if nsolve.labels:
                text = labels[sections.index(section)]
                row.label(text=text)
            operator = getattr(nsolve, section).operator
            text = operator.lower().capitalize()

            if operator == 'JOIN':
                if getattr(nsolve, section).multi_join:
                    text += ' (M)'
            elif operator == 'MERGE':
                suffix = ''
                if getattr(nsolve, section).multi_merge:
                    suffix += 'M'

                if getattr(nsolve, section).center_merge:
                    suffix += 'C'

                if suffix:
                    text += f' ({suffix})'
            elif operator == 'LINE':
                if getattr(nsolve, section).line_cut_through:
                    text += ' (C)'

            row.popover(f"NSOLVE_PT_{section.capitalize()}", text=text)

        row2 = layout.row(align=True)
        row2.popover("NSOLVE_PT_NsolvePersonas", text="", icon='COMMUNITY')
        row2.menu("NSOLVE_MT_PersonasMenu", text="", icon='TRIA_DOWN')

        row2.separator()
        row2.popover("NSOLVE_PT_Options", text="", icon='PREFERENCES')
        row2.separator()

        nsu = nsolve.nsu
        hide_icon = 'HIDE_OFF' if nsu.hide else 'HIDE_ON'
        row2.prop(nsu, 'hide', text='', icon=hide_icon)

        row2.separator()
        out_of_bounds = check_gizmo(context)

        if out_of_bounds:
            row = layout.row(align=True)
            row.alert = True
            fix = row.operator("nsolve.fix_gizmo", text="Fix")
            fix.gizmo = 'NSO'

        # layout.operator('nsolve.show_logs', text='', icon='FILE_TEXT')

        if addon.pref().menus:
            layout.separator_spacer()

            if addon.pref().menus_type == 'SEPARATED':
                layout.menu("NSOLVE_MT_SelectMenu", text="Select")
                layout.menu("NSOLVE_MT_VertMenu", text="Vert")
                layout.menu("NSOLVE_MT_EdgeMenu", text="Edge")
                layout.menu("NSOLVE_MT_FaceMenu", text="Face")

            else:
                layout.menu("NSOLVE_MT_MainMenu", text="Menu")


def draw_gizmos_layout(layout, props):

    if props.operator == 'JOIN':
        layout.prop(props, 'multi_join', text='Multi Join')
        layout.separator()
        col = layout.column(align=True, heading='Snap Mode')
        snap = props.snap_join
        col.prop(snap, 'vert', text='Vert', toggle=True)
        col.prop(snap, 'edge', text='Edge', toggle=True)
        col.prop(snap, 'face', text='Face', toggle=True)
        col.prop(snap, 'mid_edge', text='Mid Edge', toggle=True)
        col.prop(snap, 'perp_edge', text='Perp Edge', toggle=True)
        col.prop(snap, 'center_face', text='Center Face', toggle=True)
    elif props.operator == 'SELECT':
        layout.prop(props, 'select_mode', text='Select Mode')
    elif props.operator == 'MERGE':
        layout.prop(props, 'multi_merge', text='Multi Merge')
        layout.prop(props, 'center_merge', text='Center Merge')
        layout.prop(props, 'merge_weld', text='Merge Weld')
        if props.merge_weld:
            layout.prop(props, 'merge_weld_dist', text='Weld Distance')
    elif props.operator == 'LINE':
        layout.prop(props, 'line_cut_through', text='Cut Through')
    elif props.operator == 'COLLAPSE':
        layout.prop(props, 'collapse_affect_selected', text='Affect Selection')
    elif props.operator == 'DISSOLVE':
        layout.prop(props, 'dissolve_use_verts')
        layout.prop(props, 'dissolve_use_face_split')
    elif props.operator == 'SLIDE':
        layout.prop(props, 'slide_selection_mode')
        layout.prop(props, 'slide_multi_elem')
    elif props.operator == 'OFFSET':
        layout.prop(props, 'offset_distance', text='Distance')
        layout.prop(props, 'offset_even_offset', text='Even Offset')
    elif props.operator == 'KNIFE':
        layout.prop(props, 'knife_angle_limit', text='Angle Limit')
        layout.prop(props, 'knife_midpoint_snap', text='Midpoint Snap')
    elif props.operator == 'HIDE':
        layout.prop(props, 'hide_reverse', text='Reverse')
        layout.prop(props, 'hide_volume', text='Volume')
    layout.separator()

class NSOLVE_PT_Main(bpy.types.Panel):
    bl_label = "nSolve"
    bl_idname = 'NSOLVE_PT_Main'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        props = addon.pref().tools.nsolve.main
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(align=True)
        col.prop(props, 'operator', text='Operator', expand=True)

        layout.separator()
        draw_gizmos_layout(layout, props)


class NSOLVE_PT_Aux(bpy.types.Panel):
    bl_label = "nSolve"
    bl_idname = 'NSOLVE_PT_Aux'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        props = addon.pref().tools.nsolve.aux
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(align=True)
        col.prop(props, 'operator', text='Operator', expand=True)

        layout.separator()
        draw_gizmos_layout(layout, props)


class NSOLVE_PT_Sub(bpy.types.Panel):
    bl_label = "nSolve"
    bl_idname = 'NSOLVE_PT_Sub'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        props = addon.pref().tools.nsolve.sub
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(align=True)
        col.prop(props, 'operator', text='Operator', expand=True)

        layout.separator()
        draw_gizmos_layout(layout, props)


class NSOLVE_PT_Ext(bpy.types.Panel):
    bl_label = "nSolve"
    bl_idname = 'NSOLVE_PT_Ext'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        props = addon.pref().tools.nsolve.ext
        layout = self.layout
        layout.use_property_split = True

        col = layout.column(align=True)
        col.prop(props, 'operator', text='Operator', expand=True)

        layout.separator()
        draw_gizmos_layout(layout, props)


class NSOLVE_PT_NsolvePersonas(bpy.types.Panel):
    bl_label = "Personas"
    bl_idname = 'NSOLVE_PT_NsolvePersonas'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        layout.ui_units_x = 12

        layout.label(text="Personas")
        props = addon.pref().tools.nsolve

        header, nso = layout.panel("nsolve_personas_panel")
        header.label(text="NSO")

        if nso:
            row = nso.row()
            row.template_list("NSOLVE_UL_GizmoPersonas", "", props, "personas_list_items", props, "personas_list_index", rows=7)

            col = row.column(align=True)
            col.operator("nsolve.add_persona", text="", icon='ADD')
            col.operator("nsolve.remove_persona", text="", icon='REMOVE')

            if props.personas_list_index >= 0:
                col.separator()
                col.operator("nsolve.copy_persona", icon='EVENT_C', text="")
                col.operator("nsolve.apply_persona", icon='EVENT_A', text="").index = -1
                col.operator("nsolve.export_persona", icon='EXPORT', text="")
                col.operator("nsolve.import_persona", icon='IMPORT', text="")
                col.separator()
                col.operator("nsolve.configure_persona", text="", icon='SETTINGS')


        header, nsu = layout.panel("nsolve_nsu_personas_panel")
        header.label(text="NSU")

        if nsu:
            props = addon.pref().tools.nsuite
            row = nsu.row()
            row.template_list("NSOLVE_UL_NsuitePersonaList", "", props, "nsu_persona_items", props, "nsu_persona_index", rows=7)

            col = row.column(align=True)
            col.operator("nsolve.refresh_nsu_personas", text="", icon='FILE_REFRESH')
            col.operator("nsolve.open_nsu_folder", text="", icon='FILE_FOLDER')
            col.separator()
            col.operator("nsolve.apply_nsu_persona", text="", icon='CHECKMARK')
            col.separator()
            col.operator("nsolve.save_nsu_persona", text="", icon='FILE_TICK')
            col.separator()


class NSOLVE_OT_ConfigurePersona(bpy.types.Operator):
    bl_idname = "nsolve.configure_persona"
    bl_label = "Configure Persona"
    bl_description = "Configure persona settings"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        layout = self.layout
        props = addon.pref().tools.nsolve


        layout.use_property_split = True

        if props.personas_list_index >= 0:
            item = props.personas_list_items[props.personas_list_index]
            if item:
                ops = (item.main, item.aux, item.sub, item.ext)
                labels = (props.main_label, props.aux_label, props.sub_label, props.ext_label)

                for op, label in zip(ops, labels):
                    layout.prop(op, 'operator', text=label)
                    if op.operator == 'JOIN':
                        layout.prop(op, 'multi_join', text='Multi Join')
                        col = layout.column(align=True, heading='Snap Mode')
                        snap = op.snap_join
                        col.prop(snap, 'vert', text='Vert', toggle=True)
                        col.prop(snap, 'edge', text='Edge', toggle=True)
                        col.prop(snap, 'face', text='Face', toggle=True)
                        col.prop(snap, 'mid_edge', text='Mid Edge', toggle=True)
                        col.prop(snap, 'perp_edge', text='Perp Edge', toggle=True)
                        col.prop(snap, 'center_face', text='Center Face', toggle=True)
                    elif op.operator == 'SELECT':
                        layout.prop(op, 'select_mode', text='Select Mode')
                    elif op.operator == 'MERGE':
                        layout.prop(op, 'multi_merge', text='Multi Merge')
                        layout.prop(op, 'center_merge', text='Center Merge')
                        layout.prop(op, 'merge_weld', text='Merge Weld')
                        if op.merge_weld:
                            layout.prop(op, 'merge_weld_dist', text='Weld Distance')
                    elif op.operator == 'LINE':
                        layout.prop(op, 'line_cut_through', text='Cut Through')
                    elif op.operator == 'COLLAPSE':
                        layout.prop(op, 'collapse_affect_selected', text='Affect Selection')
                    elif op.operator == 'DISSOLVE':
                        layout.prop(op, 'dissolve_use_verts')
                        layout.prop(op, 'dissolve_use_face_split')
                    elif op.operator == 'SLIDE':
                        layout.prop(op, 'slide_selection_mode')
                        layout.prop(op, 'slide_multi_elem')
                    elif op.operator == 'OFFSET':
                        layout.prop(op, 'offset_distance', text='Distance')
                        layout.prop(op, 'offset_even_offset', text='Even Offset')
                    elif op.operator == 'KNIFE':
                        layout.prop(op, 'knife_angle_limit', text='Angle Limit')
                        layout.prop(op, 'knife_midpoint_snap', text='Midpoint Snap')
                    elif op.operator == 'HIDE':
                        layout.prop(op, 'hide_reverse', text='Reverse')
                        layout.prop(op, 'hide_volume', text='Volume')
                    layout.separator()

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)


def nso_sliders(layout):
    props = addon.pref().tools.nsolve
    nso = props.nso
    nsu = props.nsu

    layout.ui_units_x = 14
    layout.separator()
    maincol = layout.column(align=True)
    box = maincol.box()

    # Main Panel for nSolve
    split = box.split(factor=0.7)
    row = split.row(align=True)
    row.use_property_split = False
    row.alignment = 'LEFT'
    row.prop(nso, 'enable', text='', icon='TRIA_DOWN' if nso.enable else 'TRIA_RIGHT', emboss=False)
    row.prop(nso, 'enable', text='nSolve           ', emboss=False)

    row = split.row(align=True)
    row.alignment = 'RIGHT'
    row.operator("nsolve.place_gizmo", icon='DOT', text='').gizmo = 'NSO'
    row.separator()
    row.operator("nsolve.restore_default_main_operators", icon='EVENT_R', text="")
    row.separator()
    hide_icon = 'HIDE_OFF' if nso.hide else 'HIDE_ON'
    row.prop(nso, 'hide', text='', icon=hide_icon)

    if nso.enable:

        subbox = maincol.box()
        row = subbox.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.separator()
        row.prop(props, 'labels', text='')
        row.prop(nso, 'labels', text='Labels', emboss=False)

        if nso.labels:
            subcol = subbox.box()
            subcol.use_property_split = True
            subcol.prop(props, 'main_label')
            subcol.prop(props, 'aux_label')
            subcol.prop(props, 'sub_label')
            subcol.prop(props, 'ext_label')
            subcol.separator()

        innerbox = maincol.box()
        col = innerbox.column(align=True)
        row = col.row()
        row.template_list('NSOLVE_UL_MainGizmoList', '', props, 'main_gizmo_list_items', props, 'main_gizmo_list_index', rows=3)
        col = row.column(align=True)
        col.menu("NSOLVE_MT_add_main_operators_gizmo_menu", icon='ADD', text="")
        col.operator("nsolve.remove_main_operator", icon='REMOVE', text="")
        col.separator()
        col.operator("nsolve.move_main_operator_up", icon='TRIA_UP', text="")
        col.operator("nsolve.move_main_operator_down", icon='TRIA_DOWN', text="")
        col.separator()
        col.operator("nsolve.restore_default_main_operators", icon='EVENT_R', text="")
        innerbox.separator()

    # Main Panel for nSuite
    nsu = props.nsu

    maincol = layout.column(align=True)
    box = maincol.box()

    split = box.split(factor=0.7)
    row = split.row(align=True)
    row.use_property_split = False
    row.alignment = 'LEFT'
    row.prop(nsu, 'enable', text='', icon='TRIA_DOWN' if nsu.enable else 'TRIA_RIGHT', emboss=False)
    row.prop(nsu, 'enable', text='nSuite        ', emboss=False)

    row = split.row(align=True)
    row.alignment = 'RIGHT'
    row.operator("nsolve.place_gizmo", icon='DOT', text='').gizmo = 'NSU'
    row.separator()
    row.operator("nsolve.restore_default_operators", icon='EVENT_R', text="")
    row.separator()
    hide_icon = 'HIDE_OFF' if nsu.hide else 'HIDE_ON'
    row.prop(nsu, 'hide', text='', icon=hide_icon)

    if nsu.enable:
        nsuite_options(maincol)


class NSOLVE_PT_Nsolve(bpy.types.Panel):
    bl_label = "nSolve"
    bl_idname = 'NSOLVE_PT_Nsolve'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):
        layout = self.layout
        nso_sliders(layout)

        layout.separator(factor=2)
        split = layout.split(factor=0.9)
        info = f"{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"
        split.label(text=info)
        row = split.row(align=False)
        row.operator("nsolve.set_tool", text="", icon_value=get_icon_id("nSuite")).tool = 'NSU'


main_operators = [
    ('SELECT', 'Select', 'Select'),
    ('JOIN', 'Join', 'Join'),
    ('MERGE', 'Merge', 'Merge'),
    ('SLIDE', 'Slide', 'Slide'),
    ('LINE', 'Line', 'Line'),
    ('COLLAPSE', 'Collapse', 'Collapse'),
    ('DISSOLVE', 'Dissolve', 'Dissolve'),
    ('OFFSET', 'Offset', 'Offset'),
    ('KNIFE', 'Knife', 'Knife'),
    ('HIDE', 'Hide', 'Hide'),
    ]


class NSOLVE_UL_GizmoPersonas(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        if item:
            nsolve = addon.pref().tools.nsolve
            if index == nsolve.personas_list_index:
                layout.prop(item, "persona", text="", emboss=False)
            else:
                layout.label(text=item.persona)

    def draw_filter(self, context, layout):
        pass


class NSOLVE_OT_AddPersona(bpy.types.Operator):
    bl_label = "Add Persona"
    bl_idname = "nsolve.add_persona"
    bl_description = "Add new default persona"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        # Create a new gizmo item in the list
        prop.personas_list_items.add()  # Adds a new item to the collection
        prop.personas_list_index = len(prop.personas_list_items) - 1
        return {'FINISHED'}


def copy_persona(source, target):
    filter = {'rna_type', 'name'} #blender default
    for key in source.bl_rna.properties.keys():
        if key in filter: continue
        val = getattr(source, key)

        if isinstance(val, bpy.types.PropertyGroup):
            copy_persona(val, getattr(target, key))

        else:
            setattr(target, key, val)


class NSOLVE_OT_CopyPersona(bpy.types.Operator):
    bl_label = "Copy Persona"
    bl_idname = "nsolve.copy_persona"
    bl_description = "Copy the current settings to a new persona"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        prop = addon.pref().tools.nsolve

        props = (prop.main, prop.aux, prop.sub, prop.ext)

        prop.personas_list_items.add()
        index = len(prop.personas_list_items) - 1
        prop.personas_list_index = index

        copied = prop.personas_list_items[index]

        # combine operators names lowercase and capitalised from props with _
        copied.persona = '_'.join([prop.operator.lower().capitalize() for prop in props])

        copied_props = (copied.main, copied.aux, copied.sub, copied.ext)

        for prop, copied in zip(props, copied_props):
            copy_persona(prop, copied)

        return {'FINISHED'}


class NSOLVE_OT_ApplyPersona(bpy.types.Operator):
    bl_label = "Apply Persona"
    bl_idname = "nsolve.apply_persona"
    bl_description = "Use the selected persona as the current settings"
    bl_options = {'REGISTER', 'INTERNAL'}

    index: bpy.props.IntProperty(name="Index", description="Index", default=-1)

    def execute(self, context):
        prop = addon.pref().tools.nsolve

        if not prop.personas_list_items: return {'CANCELLED'}

        if self.index >= 0:
            index = self.index
            prop.personas_list_index = index
        else:
            index = prop.personas_list_index

        item = prop.personas_list_items[index]

        if not item:
            return {'CANCELLED'}

        props = (prop.main, prop.aux, prop.sub, prop.ext)
        items = (item.main, item.aux, item.sub, item.ext)

        for prop, item in zip(props, items):
            copy_persona(item, prop)

        return {'FINISHED'}


class NSOLVE_OT_RemovePersona(bpy.types.Operator):
    bl_label = "Remove Persona"
    bl_idname = "nsolve.remove_persona"
    bl_description = "Remove the selected persona"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        prop = addon.pref().tools.nsolve
        return len(prop.personas_list_items) > 0

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        index = prop.personas_list_index
        prop.personas_list_items.remove(index)
        prop.personas_list_index = min(max(0, index - 1), len(prop.personas_list_items) - 1)
        return {'FINISHED'}


class NSOLVE_MT_MainOperatorsAddMenu(bpy.types.Menu):
    bl_label = "Add Operator Menu"
    bl_idname = "NSOLVE_MT_add_main_operators_gizmo_menu"
    bl_description = ""

    def draw(self, context):
        layout = self.layout
        prop = addon.pref().tools.nsolve
        items = prop.main_gizmo_list_items

        for ops_type, name, _ in main_operators:
            col = layout.column()
            if ops_type in [item.operator for item in items]:
                col.enabled = False
            col.operator("nsolve.add_main_operator", text=f"Add {name}").operator = ops_type


class NSOLVE_UL_MainGizmoList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        if item:
            op_name = next((name for code, name, desc in main_operators if code == item.operator), "Unknown")
            layout.label(text=f"{op_name}", translate=False)

    def draw_filter(self, context, layout):
        pass


class NSOLVE_OT_MoveMainOperatorUp(bpy.types.Operator):
    bl_label = "Move Operator Up"
    bl_idname = "nsolve.move_main_operator_up"
    bl_description = ""
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        prop = addon.pref().tools.nsolve
        return prop.main_gizmo_list_index > 0

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        index = prop.main_gizmo_list_index
        prop.main_gizmo_list_items.move(index, index - 1)
        prop.main_gizmo_list_index -= 1
        return {'FINISHED'}


class NSOLVE_OT_MoveMainOperatorDown(bpy.types.Operator):
    bl_label = "Move Operator Down"
    bl_idname = "nsolve.move_main_operator_down"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = ""

    @classmethod
    def poll(cls, context):
        prop = addon.pref().tools.nsolve
        return prop.main_gizmo_list_index < len(prop.main_gizmo_list_items) - 1

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        index = prop.main_gizmo_list_index
        prop.main_gizmo_list_items.move(index, index + 1)
        prop.main_gizmo_list_index += 1
        return {'FINISHED'}


class NSOLVE_OT_AddMainOperartor(bpy.types.Operator):
    bl_label = "Add Operator"
    bl_idname = "nsolve.add_main_operator"
    bl_description = "Add new operator to the list"
    bl_options = {'REGISTER', 'INTERNAL'}

    operator: bpy.props.EnumProperty(name="Operator", description="Choose an operator to add", items=main_operators, default='JOIN')

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        # Create a new gizmo item in the list
        new_item = prop.main_gizmo_list_items.add()  # Adds a new item to the collection
        new_item.operator = self.operator  # Set the chosen operator to the new item
        prop.main_gizmo_list_index = len(prop.main_gizmo_list_items) - 1  # Optional: set the active index to the new item
        return {'FINISHED'}


class NSOLVE_OT_RestoreDefaultMainOperartors(bpy.types.Operator):
    bl_label = "Restore Default Operators"
    bl_idname = "nsolve.restore_default_main_operators"
    bl_description = "Restore the default operators"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):

        default_main_operators = (
            'SELECT',
            'JOIN',
            'MERGE',
            'SLIDE',
            'LINE',
            'COLLAPSE',
            'DISSOLVE',
            'OFFSET',
            'KNIFE',
            'HIDE',
        )

        prop = addon.pref().tools.nsolve
        prop.main_gizmo_list_items.clear()
        for operator in default_main_operators:
            new_item = prop.main_gizmo_list_items.add()
            new_item.operator = operator

        prop.nso.hide = True

        return {'FINISHED'}


class NSOLVE_OT_RemoveMainOperartor(bpy.types.Operator):
    bl_label = "Remove Operator"
    bl_idname = "nsolve.remove_main_operator"
    bl_description = "Remove the selected item from the list"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        prop = addon.pref().tools.nsolve
        return len(prop.main_gizmo_list_items) > 0

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        index = prop.main_gizmo_list_index
        prop.main_gizmo_list_items.remove(index)
        prop.main_gizmo_list_index = min(max(0, index - 1), len(prop.main_gizmo_list_items) - 1)
        return {'FINISHED'}


class NsolveSnapSettings(bpy.types.PropertyGroup):
    vert: bpy.props.BoolProperty(name="Vert", description="Snap to Vert", default=True)
    edge: bpy.props.BoolProperty(name="Edge", description="Snap to Edge", default=False)
    face: bpy.props.BoolProperty(name="Face", description="Snap to Face", default=False)
    mid_edge: bpy.props.BoolProperty(name="Mid Edge", description="Snap to Mid Edge", default=False)
    perp_edge: bpy.props.BoolProperty(name="Perp Edge", description="Snap to Perp Edge", default=False)
    center_face: bpy.props.BoolProperty(name="Center Face", description="Snap to Center Face", default=False)


class GizmoCollectionShared(bpy.types.PropertyGroup):
    multi_join: bpy.props.BoolProperty(name="Multi Join", description="Enable Multi Join", default=False, update=refresh_gizmo)
    snap_join: bpy.props.PointerProperty(type=NsolveSnapSettings)
    multi_merge: bpy.props.BoolProperty(name="Multi Merge", description="Enable Multi Merge", default=False, update=refresh_gizmo)
    center_merge: bpy.props.BoolProperty(name="Center Merge", description="Enable Center Merge", default=False, update=refresh_gizmo)
    merge_weld: bpy.props.BoolProperty(name="Merge Weld", description="Merge closest vertices", default=False, update=refresh_gizmo)
    merge_weld_dist: bpy.props.FloatProperty(name="Weld Distance", description="Distance to merge vertices", default=0.1, min=0.01, update=refresh_gizmo)
    line_cut_through: bpy.props.BoolProperty(name="Cut Through", description="Cut Through", default=False, update=refresh_gizmo)
    collapse_affect_selected: bpy.props.BoolProperty(name="Affect Selection", description="Affect Selection", default=False, update=refresh_gizmo)
    dissolve_use_verts: bpy.props.BoolProperty(name="Dissolve Verts", description="Dissolve Verts as well", default=True, update=refresh_gizmo)
    dissolve_use_face_split: bpy.props.BoolProperty(name="Split of face", description="Split off face corners to maintain surrounding geometry", default=False, update=refresh_gizmo)
    slide_selection_mode: bpy.props.EnumProperty(name="Mode", description="Override for contextual selection", items=[('CONTEXT', 'Context', 'Use Selection Mode'), ('VERT', 'Vertex', 'Verts Only'), ('EDGE', 'Edge' ,'Edges Only')], default='CONTEXT', update=refresh_gizmo)
    slide_multi_elem: bpy.props.BoolProperty(name="Multielement", description="Use whole selection", default=False, update=refresh_gizmo)
    offset_distance: bpy.props.FloatProperty(name="Distance", description="Distance", default=0.1, min=0.0, update=refresh_gizmo)
    offset_even_offset: bpy.props.BoolProperty(name="Even Offset", description="Even Offset", default=False, update=refresh_gizmo)
    knife_angle_limit: bpy.props.FloatProperty(name="Angle Limit", description="Angle Limit", default=30.0, min=0.0, max=180.0, update=refresh_gizmo)
    knife_midpoint_snap: bpy.props.BoolProperty(name="Midpoint Snap", description="Midpoint Snap", default=False, update=refresh_gizmo)
    hide_reverse: bpy.props.BoolProperty(name="Reverse", description="Reverse", default=True, update=refresh_gizmo)
    hide_volume: bpy.props.BoolProperty(name="Volume", description="Volume", default=True, update=refresh_gizmo)


class NsolveMainGizmoCollection(GizmoCollectionShared):
    operator: bpy.props.EnumProperty(name="Main Operator", description="Main Operator that will be called", items=main_operators, default='JOIN', update=refresh_gizmo)
    select_mode: bpy.props.EnumProperty(name="Select Mode", description="Select Mode", items=[('SET', 'Set', 'Set'), ('ADD', 'Add', 'Add'), ('SUB', 'Subtract', 'Subtract'), ('AND', 'Intersect', 'Intersect')], default='SET')


class NsolveAuxGizmoCollection(GizmoCollectionShared):
    operator: bpy.props.EnumProperty(name="Aux Operator", description="Aux Operator that will be called", items=main_operators, default='SLIDE', update=refresh_gizmo)
    select_mode: bpy.props.EnumProperty(name="Select Mode", description="Select Mode", items=[('SET', 'Set', 'Set'), ('ADD', 'Add', 'Add'), ('SUB', 'Subtract', 'Subtract'), ('AND', 'Intersect', 'Intersect')], default='ADD')


class NsolveSubGizmoCollection(GizmoCollectionShared):
    operator: bpy.props.EnumProperty(name="Sub Operator", description="Sub Operator that will be called", items=main_operators, default='COLLAPSE', update=refresh_gizmo)
    select_mode: bpy.props.EnumProperty(name="Select Mode", description="Select Mode", items=[('SET', 'Set', 'Set'), ('ADD', 'Add', 'Add'), ('SUB', 'Subtract', 'Subtract'), ('AND', 'Intersect', 'Intersect')], default='SUB')

class NsolveExtGizmoCollection(GizmoCollectionShared):
    operator: bpy.props.EnumProperty(name="Ext Operator", description="Ext Operator that will be called", items=main_operators, default='LINE', update=refresh_gizmo)
    select_mode: bpy.props.EnumProperty(name="Select Mode", description="Select Mode", items=[('SET', 'Set', 'Set'), ('ADD', 'Add', 'Add'), ('SUB', 'Subtract', 'Subtract'), ('AND', 'Intersect', 'Intersect')], default='AND')


class NsolveMainGizmoList(bpy.types.PropertyGroup):
    # Store the type of modifier
    operator: bpy.props.EnumProperty(name="Items", description="Items", items=main_operators, default='JOIN', update=refresh_gizmo)


class NsolvePersonasList(bpy.types.PropertyGroup):
    persona: bpy.props.StringProperty(name="Persona", description="Persona name", default='Persona', update=refresh_gizmo)
    main: bpy.props.PointerProperty(type=NsolveMainGizmoCollection)
    aux: bpy.props.PointerProperty(type=NsolveAuxGizmoCollection)
    sub: bpy.props.PointerProperty(type=NsolveSubGizmoCollection)
    ext: bpy.props.PointerProperty(type=NsolveExtGizmoCollection)


class NsolveNsoPanelPref(bpy.types.PropertyGroup):
    hide: bpy.props.BoolProperty(name="Hide", description="Hide", default=True, update=refresh_gizmo)
    enable: bpy.props.BoolProperty(name="Expand NSO", description="", default=False)
    labels: bpy.props.BoolProperty(name="Labels", description="Show labels", default=False)
    layout: bpy.props.BoolProperty(name="Layout", description="Layout", default=True)


class NsolveNsuPanelPref(bpy.types.PropertyGroup):
    hide: bpy.props.BoolProperty(name="Hide", description="Hide", default=False, update=refresh_gizmo)
    enable: bpy.props.BoolProperty(name="Expand NSU", description="", default=False)


class FolderState(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    expanded: bpy.props.BoolProperty(default=False)


class GizmoColor(bpy.types.PropertyGroup):
    inner: bpy.props.FloatVectorProperty(name="Inner", description="Inner", subtype='COLOR', default=(0.1, 0.1, 0.1, 0.7), size=4, min=0, max=1, update=refresh_gizmo)
    selected: bpy.props.FloatVectorProperty(name="Selected color", description="Selected color", subtype='COLOR', default=(0.1, 0.5, 0.8, 0.5), size=4, min=0, max=1, update=refresh_gizmo)


class InterfaceColor(bpy.types.PropertyGroup):
    """Color properties for interface elements"""
    main_tool: bpy.props.FloatVectorProperty(
        name="Main Tool Color",
        description="Color for main tool interface elements",
        subtype='COLOR',
        default=(0.4, 0.4, 0.4, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    nsolve_tool: bpy.props.FloatVectorProperty(
        name="NSolve Tool Color",
        description="Color for nsolve tool interface elements",
        subtype='COLOR',
        default=(1.0, 0.67, 0.5, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    nsuite_tool: bpy.props.FloatVectorProperty(
        name="NSuite Tool Color",
        description="Color for nsuite tool interface elements",
        subtype='COLOR',
        default=(0.2, 0.4, 1.0, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )

    select_color: bpy.props.FloatVectorProperty(
        name="Select Color",
        description="Color for select operator",
        subtype='COLOR',
        default=(0.2, 0.4, 1.0, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    join_color: bpy.props.FloatVectorProperty(
        name="Join Color",
        description="Color for join operator",
        subtype='COLOR',
        default=(0.8, 0.7, 0.26, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    merge_color: bpy.props.FloatVectorProperty(
        name="Merge Color",
        description="Color for merge operator",
        subtype='COLOR',
        default=(0.8, 0.12, 0.03, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    slide_color: bpy.props.FloatVectorProperty(
        name="Slide Color",
        description="Color for slide operator",
        subtype='COLOR',
        default=(0.2, 0.2, 0.8, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    line_color: bpy.props.FloatVectorProperty(
        name="Line Color",
        description="Color for line operator",
        subtype='COLOR',
        default=(0.6, 0.87, 1, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    collapse_color: bpy.props.FloatVectorProperty(
        name="Collapse Color",
        description="Color for collapse operator",
        subtype='COLOR',
        default=(0.8, 0.4, 0.2, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    dissolve_color: bpy.props.FloatVectorProperty(
        name="Dissolve Color",
        description="Color for dissolve operator",
        subtype='COLOR',
        default=(1.0, 0.0, 0.0, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    offset_color: bpy.props.FloatVectorProperty(
        name="Offset Color",
        description="Color for offset operator",
        subtype='COLOR',
        default=(0.01, 0.47, 0.8, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )
    knife_color: bpy.props.FloatVectorProperty(
        name="Knife Color",
        description="Color for knife operator",
        subtype='COLOR',
        default=(0.8, 0.32, 0.03, 0.8),
        size=4,
        min=0,
        max=1,
        update=refresh_gizmo
    )


class BannerColor(bpy.types.PropertyGroup):
    """Color properties for interface elements"""
    fg_text_color: bpy.props.FloatVectorProperty(
        name="FG Text Color",
        description="Color for banner fg text",
        subtype='COLOR',
        default=(1, 1, 1, 0.5),
        size=4,
        min=0,
        max=1,
        # update=refresh_gizmo
    )
    bg_text_color: bpy.props.FloatVectorProperty(
        name="BG Text Color",
        description="Color for banner bg text",
        subtype='COLOR',
        default=(1, 1, 1, 0.1),
        size=4,
        min=0,
        max=1,
        # update=refresh_gizmo
    )
    bg_color: bpy.props.FloatVectorProperty(
        name="BG Color",
        description="Color for banner bg",
        subtype='COLOR',
        default=(1, 1, 1, 0.3),
        size=4,
        min=0,
        max=1,
        # update=refresh_gizmo
    )
    highlight_color: bpy.props.FloatVectorProperty(
        name="Highlight Color",
        description="Color for banner 'tick' highlight",
        subtype='COLOR',
        default=(1, 1, 1, 0.3),
        size=4,
        min=0,
        max=1,
        # update=refresh_gizmo
    )
    tick_color: bpy.props.FloatVectorProperty(
        name="Tick Color",
        description="Color for banner 'tick'",
        subtype='COLOR',
        default=(0.5, 0.02, 0.02, 0.95),
        size=4,
        min=0,
        max=1,
        # update=refresh_gizmo
    )
    tick_color_use_tool: bpy.props.BoolProperty(
        name="Use Tool Color",
        description="Use the current tool color for the 'tick' instead of the theme option",
        default=True
        # update=refresh_gizmo
    )


class InterfaceOptions(bpy.types.PropertyGroup):
    show_interface: bpy.props.BoolProperty(name="Show Corners", description="Show corner indicators in the viewport", default=True, update=refresh_gizmo)
    enable_animation: bpy.props.BoolProperty(name="Enable Animation", description="Enable corner animation when changing tools", default=True, update=refresh_gizmo)
    extra_animation: bpy.props.BoolProperty(name="Extra Animation", description="Extra animation when using tools", default=True, update=refresh_gizmo)
    margin: bpy.props.FloatProperty(name="Margin", description="Margin", default=60.0, min=0.0, update=refresh_gizmo)
    animation_duration: bpy.props.FloatProperty(name="Animation Duration", description="Duration of the animation in seconds", default=0.4, min=0.1, update=refresh_gizmo)
    animation_margin: bpy.props.FloatProperty(name="Animation Margin", description="How much the margin changes during animation", default=16.0, min=0.0, max=50.0, update=refresh_gizmo)
    animation_text_size: bpy.props.IntProperty(name="Animatin Text Size", description="Text Size", default=24, min=0, update=refresh_gizmo)
    animation_text_in_time: bpy.props.FloatProperty(name="Text In Time", description="In Time", default=0.04, min=0.0, update=refresh_gizmo)
    animation_line_length: bpy.props.FloatProperty(name="Animation Line Length", description="Line Length", default=15.0, min=0.0, update=refresh_gizmo)
    animation_line_width: bpy.props.FloatProperty(name="Animation Line Width", description="Line Width", default=4.0, min=0.0, update=refresh_gizmo)
    text_size: bpy.props.IntProperty(name="Text Size", description="Bottom Text Size", default=16, min=0, update=refresh_gizmo)
    text_in_time: bpy.props.FloatProperty(name="Text In Time", description="In Time", default=0.22, min=0.0, update=refresh_gizmo)
    text_out_time: bpy.props.FloatProperty(name="Text Out Time", description="Out Time", default=0.14, min=0.0, update=refresh_gizmo)
    text_duration: bpy.props.FloatProperty(name="Text Duration", description="Duration of the text fade animation in seconds", default=2, min=0.1, update=refresh_gizmo)
    show_header: bpy.props.BoolProperty(name="Show Header", description="Show header", default=False, update=refresh_gizmo)
    enable_header_animation: bpy.props.BoolProperty(name="Enable Header Animation", description="Enable header animation when changing tools", default=True, update=refresh_gizmo)
    header_headertext_size: bpy.props.IntProperty(name="Header Text Size", description="Header Text Size", default=24, min=0, update=refresh_gizmo)
    header_linetext_size: bpy.props.IntProperty(name="Header Line Text Size", description="Header Line Text Size", default=14, min=0, update=refresh_gizmo)
    header_line_width: bpy.props.FloatProperty(name="Header Line Width", description="Header Line Width", default=4.0, min=0.0, update=refresh_gizmo)
    header_duration: bpy.props.FloatProperty(name="Header Duration", description="Duration of the header animation in seconds", default=1.6, min=0.1, update=refresh_gizmo)
    header_in_time: bpy.props.FloatProperty(name="Header In Time", description="In Time", default=0.2, min=0.0, update=refresh_gizmo)
    header_out_time: bpy.props.FloatProperty(name="Header Out Time", description="Out Time", default=0.2, min=0.0, update=refresh_gizmo)
    custom_font: bpy.props.BoolProperty(name="Custom Font", description="Use custom font", default=True, update=refresh_gizmo)
    gizmo_enabled: bpy.props.BoolProperty(name="Gizmo text Enabled", description="Enable Gizmo", default=False, update=refresh_gizmo)
    gizmo_in_time: bpy.props.FloatProperty(name="Gizmo In Time", description="In Time", default=0.22, min=0.0, update=refresh_gizmo)
    gizmo_scale: bpy.props.FloatProperty(name="GizmoText Scale", description="GizmoText Scale", default=1.4, min=0.1, max=10.0, update=refresh_gizmo)
    font_type: bpy.props.EnumProperty(
        name="Font Type",
        description="Font to use for interface text",
        items=FONT_ITEMS,
        default='GENOS_BOLD',
        update=refresh_gizmo
    )
    enable_banner: bpy.props.BoolProperty(name="Enable Banner", description="Display the animated banner in the viewport", default=False)
    banner_text_size: bpy.props.IntProperty(name="Banner Text Size", description="Text Size", default=100, min=0)
    banner_frame_time: bpy.props.FloatProperty(name="Banner Frame Time", description="Time for the banner frame", default=0.1, min=0.0, # update=refresh_gizmo
    )
    banner_tick_time: bpy.props.FloatProperty(name="Banner Tick Time", description="Time for the banner 'tick'", default=0.2, min=0.0, # update=refresh_gizmo
    )
    banner_highlight_time: bpy.props.FloatProperty(name="Banner Highlight Time", description="Time for the banner 'tick' highlight", default=0.1, min=0.0, # update=refresh_gizmo
    )
    banner_bg_text_time: bpy.props.FloatProperty(name="Banner BG Text Time", description="Time for the banner bg text", default=0.2, min=0.0, # update=refresh_gizmo
    )
    banner_fg_text_time: bpy.props.FloatProperty(name="Banner FG Text Time", description="Time for the banner fg text", default=0.3, min=0.0, # update=refresh_gizmo
    )


SHAPE_ITEMS = [
    ('CIRCLE', 'Circle', 'Circle'),
    ('SQUARE', 'Square', 'Square'),
    ('ROUNDED_SQUARE', 'Rounded', 'Rounded'),
]

class types():
    class pref(bpy.types.PropertyGroup):
        expanded: bpy.props.BoolProperty(name="Expanded", description="Expanded", default=True, update=refresh_gizmo)
        labels: bpy.props.BoolProperty(name="Labels", description="Show labels", default=True)
        main: bpy.props.PointerProperty(type=NsolveMainGizmoCollection)
        main_label: bpy.props.StringProperty(name="Main Label", description="Main Label", default="LMB:")
        aux: bpy.props.PointerProperty(type=NsolveAuxGizmoCollection)
        aux_label: bpy.props.StringProperty(name="Aux Label", description="Aux Label", default="Shift:")
        sub: bpy.props.PointerProperty(type=NsolveSubGizmoCollection)
        sub_label: bpy.props.StringProperty(name="Sub Label", description="Sub Label", default="Ctrl:")
        ext: bpy.props.PointerProperty(type=NsolveExtGizmoCollection)
        ext_label: bpy.props.StringProperty(name="Ext Label", description="Ext Label", default="Alt:")
        main_gizmo_location: bpy.props.FloatVectorProperty(name="Gizmo Location", description="Gizmo Location", default=(15, 60), size=2, max=99, min=1, update=refresh_gizmo)
        main_gizmo_scale: bpy.props.IntProperty(name="Gizmo Scale", description="Gizmo Scale", default=42, min=16, max=256, update=refresh_gizmo)
        main_gizmo_magnification: bpy.props.FloatProperty(name="Gizmo Magnification", description="Gizmo Magnification", default=1.4, min=1, max=10, update=refresh_gizmo)
        main_gizmo_spacing: bpy.props.FloatProperty(name="Gizmo Spacing", description="Gizmo Spacing", default=0.3, min=0.1, max=2.0, update=refresh_gizmo)
        main_gizmo_space: bpy.props.FloatProperty(name="Gizmo Space", description="Gizmo Space", default=2.5, min=2, max=3, update=refresh_gizmo)
        main_gizmo_flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=False, update=refresh_gizmo)
        main_gizmo_list_items: bpy.props.CollectionProperty(type=NsolveMainGizmoList)
        main_gizmo_list_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)
        main_gizmo_shape: bpy.props.EnumProperty(name="Shape", description="Shape", items=SHAPE_ITEMS, default='ROUNDED_SQUARE', update=refresh_gizmo)
        main_gizmo_skip_alt: bpy.props.BoolProperty(name="Skip Alt", description="Skip Alt", default=False, update=refresh_gizmo)

        InterfaceColor: bpy.props.PointerProperty(type=InterfaceColor)
        BannerColor: bpy.props.PointerProperty(type=BannerColor)
        InterfaceOptions: bpy.props.PointerProperty(type=InterfaceOptions)

        nso: bpy.props.PointerProperty(type=NsolveNsoPanelPref)
        nflow: bpy.props.PointerProperty(type=NsolveNsoPanelPref)
        nsu: bpy.props.PointerProperty(type=NsolveNsuPanelPref)
        folder_states: bpy.props.CollectionProperty(type=FolderState)

        personas_list_items: bpy.props.CollectionProperty(type=NsolvePersonasList)
        personas_list_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)

        gizmo_col: bpy.props.PointerProperty(type=GizmoColor)


types_classes = (
    InterfaceColor,
    BannerColor,
    InterfaceOptions,
    GizmoColor,
    NsolveNsoPanelPref,
    NsolveNsuPanelPref,
    NsolveSnapSettings,
    FolderState,
    NsolveMainGizmoCollection,
    NsolveAuxGizmoCollection,
    NsolveSubGizmoCollection,
    NsolveExtGizmoCollection,
    NsolveMainGizmoList,
    NSOLVE_UL_MainGizmoList,
    NsolvePersonasList,
    NSOLVE_UL_GizmoPersonas,
    types.pref,
)


classes = (
    NSOLVE_OT_RestoreDefaultMainOperartors,
    NSOLVE_OT_MoveMainOperatorUp,
    NSOLVE_OT_MoveMainOperatorDown,
    NSOLVE_OT_AddMainOperartor,
    NSOLVE_OT_RemoveMainOperartor,
    NSOLVE_OT_AddPersona,
    NSOLVE_OT_RemovePersona,
    NSOLVE_OT_ApplyPersona,
    NSOLVE_OT_CopyPersona,
    NSOLVE_MT_MainOperatorsAddMenu,
    NSOLVE_PT_Nsolve,
    NSOLVE_PT_NsolvePersonas,
    NSOLVE_PT_Main,
    NSOLVE_PT_Aux,
    NSOLVE_PT_Sub,
    NSOLVE_PT_Ext,
    NSOLVE_OT_ConfigurePersona,
)


def initialize_nsolve_tool():
    default_main_operators = (
        'SELECT',
        'JOIN',
        'MERGE',
        'SLIDE',
        'LINE',
        'COLLAPSE',
        'DISSOLVE',
        'OFFSET',
        'KNIFE',
        'HIDE',
    )

    prop = addon.pref().tools.nsolve
    if len(prop.main_gizmo_list_items) == 0:
        for operator in default_main_operators:
            item = prop.main_gizmo_list_items.add()
            item.operator = operator

    # Check if everything is set up as expected, then unregister the timer
    return None  # Returning None will stop the timer from repeating
