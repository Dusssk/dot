from pathlib import Path
import bpy
from ...utils import addon
from .utils import refresh_gizmo
from ... import bl_info
from ...icons.menus import get_icon_id
from ...src.ops.nflow import BehaviorPresetEntryItems
from ..ops.nflow.common import UIMetadata
import json
import os
from bpy_extras.io_utils import ImportHelper, ExportHelper


def check_gizmo(context):
    area = context.area
    # Ensure the area is a 3D View
    if area.type == 'VIEW_3D':
        # Find the 'WINDOW' region within the 3D View
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region:
            # Assuming 'nsolve' is set up correctly with ops_gizmo_location attributes
            nsuite = addon.pref().tools.nsuite
            locations = [nsuite.ops_gizmo_location]

            for location in locations:
                if location[0] < 1 or location[0] > 99 or location[1] < 1 or location[1] > 90:
                    return True

            return False

    return False  # If not a 3D View area or no 'WINDOW' region found


def jump_to_nsolve_tool(cls, context):
    bpy.ops.nsolve.set_tool(tool='NSO')
    nsolve = addon.pref().tools.nsolve
    nsolve.nsu.hide = True
    if cls.swap:
        cls.swap = False

def buttons_icons_list() -> list[str]:
    '''List of pngs with extension in icons/buttons'''
    folder = Path(__file__).parent.parent.parent / "icons" / "buttons"
    if not folder.exists(): return []
    lst= [val.name for val in sorted(folder.glob("*.png"))]

    return lst


class NSOLVE_MT_Nsuite(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'nsolve.nsuitetool'
    bl_label = "nSuite"
    bl_description = f'Version {bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}'
    bl_icon = (Path(__file__).parent.parent.parent / "icons" / "tools" / "nsuite").as_posix()
    bl_widget = 'NSOLVE_GGT_Nsuite'
    bl_keymap = (
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': [('mode', 'SET')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'ctrl': True}, {'properties': [('mode', 'SUB')]}),
        ('view3d.select_box', {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG', 'shift': True}, {'properties': [('mode', 'ADD')]}),
        ('nsolve.select_smartloop', {'type': 'RIGHTMOUSE', 'value': 'PRESS', 'ctrl': True}, {'properties': []}),
        ('nsolve.select_planarloop', {'type': 'RIGHTMOUSE', 'value': 'PRESS', 'shift': True}, {'properties': []}),
        ('nsolve.helper', {'type': 'D', 'value': 'PRESS'}, {'properties': []}),
    )

    def draw_settings(context, layout, tool):
        layout.operator('nsolve.helper', text='', icon_value=get_icon_id('nSuite'), depress=False)
        layout.label(text=f'{bl_info["version"][0]}.{bl_info["version"][1]}.{bl_info["version"][2]}')

        layout.separator()

        layout.popover("NSOLVE_PT_Nsuite", text="", icon='OPTIONS')
        row = layout.row(align=True)
        row.separator()
        row.popover("NSOLVE_PT_Options", text="", icon='PREFERENCES')

        row.separator()
        nsuite = addon.pref().tools.nsuite
        nsu = nsuite.nsu
        row.prop(nsu, 'swap', text='', icon='HIDE_ON')

        out_of_bounds = check_gizmo(context)

        if out_of_bounds:
            row = layout.row(align=True)
            row.alert = True
            fix = row.operator("nsolve.fix_gizmo", text="Fix")
            fix.gizmo = 'NSU'

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


def nsuite_options(layout):
    '''Draw the nsuite options'''

    nsuite = addon.pref().tools.nsuite

    layout.use_property_split = True
    layout.use_property_decorate = True

    col = layout

    box = col.column(align=True)
    subbox = box.box()
    col = subbox.column(align=True)
    col.operator("nsolve.restore_default_operators", icon='EVENT_R', text="Restore Default")

    # Add Import/Export buttons
    row = col.row(align=True)
    row.operator("nsolve.import_nsuite_layout", icon='IMPORT', text="Import Layout")
    row.operator("nsolve.export_nsuite_layout", icon='EXPORT', text="Export Layout")

    # Add Open Folder button
    row.operator("nsolve.open_nsu_folder", icon='FILE_FOLDER', text="Open Folder")


class NSOLVE_PT_Nsuite(bpy.types.Panel):
    bl_label = "nSolve"
    bl_idname = 'NSOLVE_PT_Nsuite'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'

    def draw(self, context):

        layout = self.layout
        layout.ui_units_x = 14

        nsu = addon.pref().tools.nsuite.nsu
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

        layout.separator(factor=2)
        split = layout.split(factor=0.9)
        info = f"{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"
        split.label(text=info)
        row = split.row(align=False)
        row.operator("nsolve.set_tool", text="", icon_value=get_icon_id("nSolve")).tool = 'NSO'


operators = [
    ('none', 'None', 'Empty slot'),
    ('nsuite', 'nSuite', 'nSuite'),
    ('tool', 'Tool', 'Geometry Node Tool'),
    ('custom', 'Custom', 'Custom operator'),
    ('script', 'Script', 'Execute a script'),
]

nsuite_operators = [
    ('none', 'None', 'Empty slot'),
    ('hard_loop_cut', 'Hard Loop Cut', 'Hard loop cut'),
    ('loop_cut', 'Loop Cut', 'Loop cut'),
    ('hard_edge_slide', 'Hard Edge Slide', 'Hard edge slide'),
    ('offset_edges', 'Offset Edges', 'Offset edges'),
    ('bevel', 'Bevel', 'Bevel'),
    ('mesh_cut', 'Mesh Cut', 'Mesh cut'),
    ('project_line', 'Project Line', 'Project line'),
    ('project_loop', 'Project Loop', 'Project loop'),
    ('project_circle', 'Project Circle', 'Project circle'),
    ('project_grid', 'Project Grid', 'Project grid'),
    ('select_smartloop', 'Select Smart Loop', 'Select smart loop'),
    ('analyze', 'Analyze', 'Analyze'),
]



class CustomOperatorProperty(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('INT', "Integer", ""),
            ('FLOAT', "Float", ""),
            ('STRING', "String", ""),
            ('BOOL', "Boolean", ""),
            ('ENUM', "Enum", ""),
        ],
        default='INT'
    )
    value_int: bpy.props.IntProperty(name="Value (Int)", default=0)
    value_float: bpy.props.FloatProperty(name="Value (Float)", default=0.0)
    value_string: bpy.props.StringProperty(name="Value (String)", default="")
    value_bool: bpy.props.BoolProperty(name="Value (Bool)", default=False)
    value_enum: bpy.props.StringProperty(name="Value (Enum)", default="")


class NSOLVE_OT_EditCustomOperatorProperties(bpy.types.Operator):
    bl_idname = "nsolve.edit_custom_operator_properties"
    bl_label = "Edit Custom Operator Properties"
    bl_description = "Edit properties of the custom operator"
    bl_options = {'INTERNAL'}

    show_hidden: bpy.props.BoolProperty(
        name='Show Hidden',
        description='Show hidden arguments',
        default=False
    )
    arguments: bpy.props.CollectionProperty(
        name="Arguments",
        type=CustomOperatorProperty
    )
    custom_operator: bpy.props.StringProperty()
    button_index: bpy.props.IntProperty()

    def invoke(self, context, event):
        if not self.custom_operator:
            self.report({'ERROR'}, "No custom operator specified")
            return {'CANCELLED'}

        # Parse the operator ID (e.g., 'object.move')
        try:
            category, operator_name = self.custom_operator.split(".")
        except ValueError:
            self.report({'ERROR'}, "Invalid operator ID format")
            return {'CANCELLED'}

        # Retrieve the operator class
        operator_class = getattr(getattr(bpy.ops, category, None), operator_name, None)
        if operator_class is None:
            self.report({'ERROR'}, f"Operator '{self.custom_operator}' not found")
            return {'CANCELLED'}

        # Get the operator's RNA type
        op_rna = operator_class.get_rna_type()

        # Clear existing arguments
        self.arguments.clear()

        # Get temporary properties
        temp_props = context.window_manager.nsolve.nsuite.temp_properties

        # Retrieve default properties
        for prop_rna in op_rna.properties:
            if prop_rna.identifier in ('bl_idname', 'bl_label', 'bl_options'):
                continue  # Skip internal properties

            if not self.show_hidden and prop_rna.is_hidden:
                continue  # Skip hidden properties if not showing

            argument = self.arguments.add()
            argument.name = prop_rna.identifier

            # Find existing property if it exists
            existing_prop = next(
                (p for p in temp_props.operator_properties if p.name == prop_rna.identifier),
                None
            )

            # Determine property type and assign default or existing value
            if prop_rna.type == 'BOOLEAN':
                argument.type = 'BOOL'
                argument.value_bool = existing_prop.value_bool if existing_prop else prop_rna.default
            elif prop_rna.type == 'INT':
                argument.type = 'INT'
                argument.value_int = existing_prop.value_int if existing_prop else prop_rna.default
            elif prop_rna.type == 'FLOAT':
                argument.type = 'FLOAT'
                argument.value_float = existing_prop.value_float if existing_prop else prop_rna.default
            elif prop_rna.type == 'STRING':
                argument.type = 'STRING'
                argument.value_string = existing_prop.value_string if existing_prop else prop_rna.default
            elif prop_rna.type == 'ENUM':
                argument.type = 'ENUM'
                argument.value_enum = existing_prop.value_enum if existing_prop else prop_rna.default

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Update temporary properties
        temp_props = context.window_manager.nsolve.nsuite.temp_properties
        temp_props.operator_properties.clear()

        for arg in self.arguments:
            new_prop = temp_props.operator_properties.add()
            new_prop.name = arg.name
            new_prop.type = arg.type
            new_prop.value_int = arg.value_int
            new_prop.value_float = arg.value_float
            new_prop.value_string = arg.value_string
            new_prop.value_bool = arg.value_bool
            new_prop.value_enum = arg.value_enum

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Operator Properties:")
        for arg in self.arguments:
            row = box.row()
            row.label(text=arg.name)
            if arg.type == 'INT':
                row.prop(arg, "value_int", text="")
            elif arg.type == 'FLOAT':
                row.prop(arg, "value_float", text="")
            elif arg.type == 'STRING':
                row.prop(arg, "value_string", text="")
            elif arg.type == 'BOOL':
                row.prop(arg, "value_bool", text="")
            elif arg.type == 'ENUM':
                row.prop(arg, "value_enum", text="")


class NSOLVE_OT_ConfigureGizmoButton(bpy.types.Operator):
    bl_idname = "nsolve.configure_gizmo_button"
    bl_label = "Configure Button"
    bl_description = "Configure gizmo button"
    bl_options = {'REGISTER', 'INTERNAL'}

    instance = None
    icons = []

    button_index: bpy.props.IntProperty()
    gizmo_index: bpy.props.IntProperty()
    operator: bpy.props.EnumProperty(
        name="Operator",
        description="Choose an operator",
        items=operators,
        default='none'
    )
    custom_operator: bpy.props.StringProperty(
        name="Custom Operator",
        description="Choose a custom operator",
        default="",
        options={'SKIP_SAVE'}
    )

    nsuite_operator: bpy.props.EnumProperty(
        name="NSuite Operator",
        description="Choose an NSuite operator",
        items=nsuite_operators,
        default='hard_loop_cut'
    )

    tool_operator: bpy.props.StringProperty(
        name="Tool Operator",
        description="Choose a geometry node tool",
        default=""
    )

    custom_icon: bpy.props.StringProperty(
        name="Custom Icon",
        description="Icon from icons/buttons folder",
        default=''
    )
    operator_properties: bpy.props.CollectionProperty(type=CustomOperatorProperty)

    script: bpy.props.StringProperty(
        name="Script",
        description="Script to run \n Imports: bpy, math, mathutils",
        default=""
    )

    script_description: bpy.props.StringProperty(
        name="Description",
        description="",
        default=""
    )

    def invoke(self, context, event):
        props = addon.pref().tools.nsuite
        if len(props.nsu_gizmos_items) <= self.gizmo_index:
            return {'CANCELLED'}

        gizmo = props.nsu_gizmos_items[self.gizmo_index]
        if len(gizmo.list_items) <= self.button_index:
            return {'CANCELLED'}

        # cache icon list
        self.icons = buttons_icons_list()

        button = gizmo.list_items[self.button_index]
        self.operator = button.operator
        self.nsuite_operator = button.nsuite_operator
        self.custom_operator = button.custom_operator
        self.tool_operator = button.tool_operator
        self.custom_icon = button.custom_icon
        self.script = button.script
        self.script_description = button.script_description

        # Copy operator properties
        self.operator_properties.clear()
        for prop in button.operator_properties:
            item = self.operator_properties.add()
            item.name = prop.name
            item.type = prop.type
            item.value_int = prop.value_int
            item.value_float = prop.value_float
            item.value_string = prop.value_string
            item.value_bool = prop.value_bool
            item.value_enum = prop.value_enum

        context.window_manager.nsolve.nsuite.temp_properties.update_geometry_node_groups(context)
        context.window_manager.nsolve.nsuite.temp_operators.update_search_candidates(context)
        self.__class__.instance = self

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        from ...icons import buttons

        layout = self.layout

        # Main operator selection
        box = layout.box()
        box.prop(self, "operator", text="")

        if self.operator == 'nsuite':
            box = layout.box()
            box.prop(self, "nsuite_operator", text="")
        elif self.operator == 'tool':
            box = layout.box()
            # Get available geometry node tools
            tools = get_geometry_node_tools()
            row = box.row(align=True)
            row.prop_search(self, "tool_operator", context.window_manager.nsolve.nsuite.temp_properties, "geometry_node_groups", text="")

            # Icon selection
            row.operator(NSOLVE_OT_CustomIconSelect.bl_idname, icon_value=buttons.get_icon_id(self.custom_icon.split('.')[0]))

        elif self.operator == 'custom':
            box = layout.box()
            row = box.row(align=True)
            row.operator("nsolve.manage_operator_filters", text="", icon='FILTER')
            row.prop_search(self, "custom_operator", context.window_manager.nsolve.nsuite.temp_operators, "operator_search_candidates", text="")

            # Custom icon
            row.operator(NSOLVE_OT_CustomIconSelect.bl_idname, icon_value=buttons.get_icon_id(self.custom_icon.split('.')[0]))

            # Edit operator properties
            if self.custom_operator:
                box.operator("nsolve.edit_custom_operator_properties", text="Edit Properties").custom_operator = self.custom_operator

        elif self.operator == 'script':
            box = layout.box()
            row = box.row(align=True)
            row.prop(self, 'script')
            # Custom icon
            row.operator(NSOLVE_OT_CustomIconSelect.bl_idname, icon_value=buttons.get_icon_id(self.custom_icon.split('.')[0]))

            row = box.row(align=True)
            row.prop(self, "script_description")


    def execute(self, context):
        self.__class__.instance = None
        props = addon.pref().tools.nsuite
        if len(props.nsu_gizmos_items) <= self.gizmo_index:
            return {'CANCELLED'}

        gizmo = props.nsu_gizmos_items[self.gizmo_index]
        if len(gizmo.list_items) <= self.button_index:
            return {'CANCELLED'}

        button = gizmo.list_items[self.button_index]

        # Update button properties
        button.operator = self.operator
        button.nsuite_operator = self.nsuite_operator
        button.custom_operator = self.custom_operator
        button.tool_operator = self.tool_operator
        button.custom_icon = self.custom_icon
        button.script = self.script
        button.script_description = self.script_description

        # Update operator properties
        button.operator_properties.clear()
        for prop in self.operator_properties:
            item = button.operator_properties.add()
            item.name = prop.name
            item.type = prop.type
            item.value_int = prop.value_int
            item.value_float = prop.value_float
            item.value_string = prop.value_string
            item.value_bool = prop.value_bool
            item.value_enum = prop.value_enum

        # Force a redraw to update UI
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return {'FINISHED'}

    def cancel(self, context):
        self.__class__.instance = None


class NSOLVE_OT_CustomIconSelect(bpy.types.Operator):
    bl_label = ""
    bl_idname = "nsolve.custom_icon_selector"
    bl_description = "Icon Selector"

    operator = None

    def execute(self, context):

        context.window_manager.popover(self.draw_func)
        return {'FINISHED'}

    @staticmethod
    def draw_func(self, context):
        from ...icons import buttons
        import math

        icons = NSOLVE_OT_ConfigureGizmoButton.instance.icons
        layout = self.layout
        grid = layout.grid_flow(align=False, even_columns=True, even_rows=True)
        grid.scale_x = grid.scale_y = 2
        grid.emboss = 'PULLDOWN_MENU'

        for path in icons:
            icon_value = buttons.get_icon_id(path.split('.')[0])
            row = grid.row(align=False)
            op = row.operator(NSOLVE_OT_SelectIcon.bl_idname, text='', icon_value=icon_value)
            op.icon_name = path


class NSOLVE_OT_SelectIcon(bpy.types.Operator):
    bl_idname = "nsolve.select_icon"
    bl_label = "Select Icon"
    bl_description = "Select this icon"
    bl_options = {'INTERNAL'}

    icon_name: bpy.props.StringProperty()

    def execute(self, context):
        operator = NSOLVE_OT_ConfigureGizmoButton.instance
        operator.custom_icon = self.icon_name

        return {'FINISHED'}


class NSOLVE_OT_AddCustomProperty(bpy.types.Operator):
    bl_label = "Add Custom Property"
    bl_idname = "nsolve.add_custom_property"
    bl_description = "Add a new custom property"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        prop = addon.pref().tools.nsuite
        item = prop.ops_gizmo_list_items[prop.ops_gizmo_list_index]

        # Add new property
        new_prop = item.custom_properties.add()
        new_prop.name = f"prop_{len(item.custom_properties)}"
        new_prop.type = 'FLOAT'

        return {'FINISHED'}


class NSOLVE_OT_RemoveCustomProperty(bpy.types.Operator):
    bl_label = "Remove Custom Property"
    bl_idname = "nsolve.remove_custom_property"
    bl_description = "Remove selected custom property"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        prop = addon.pref().tools.nsuite
        item = prop.ops_gizmo_list_items[prop.ops_gizmo_list_index]

        if item.custom_properties and item.custom_properties_index >= 0:
            item.custom_properties.remove(item.custom_properties_index)
            if item.custom_properties_index >= len(item.custom_properties):
                item.custom_properties_index = len(item.custom_properties) - 1

        return {'FINISHED'}


class NSOLVE_OT_NsuiteAddOperator(bpy.types.Operator):
    bl_label = "Add Operator"
    bl_idname = "nsolve.add_operator"
    bl_description = ""
    bl_options = {'REGISTER', 'INTERNAL'}

    operator: bpy.props.EnumProperty(
        name="Operator",
        description="Choose an operator to add",
        items=operators,
        default='none'
    )

    def execute(self, context):
        TOTAL_SLOTS = 75
        prop = addon.pref().tools.nsuite

        # Only add if we haven't reached max slots
        if len(prop.ops_gizmo_list_items) < TOTAL_SLOTS:
            new_item = prop.ops_gizmo_list_items.add()
            new_item.operator = self.operator
            prop.ops_gizmo_list_index = len(prop.ops_gizmo_list_items) - 1

        return {'FINISHED'}


class NSOLVE_OT_NsuiteRestoreDefaultOperartors(bpy.types.Operator):
    bl_idname = "nsolve.restore_default_operators"
    bl_label = "Restore Default Operators"
    bl_description = "Restore default operators"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        props = addon.pref().tools.nsuite

        # Try to load from default.nsu first
        default_nsu_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite", "default.nsu")
        if os.path.exists(default_nsu_path):
            try:
                bpy.ops.nsolve.import_nsuite_layout(filepath=default_nsu_path)
                return {'FINISHED'}
            except Exception as e:
                print(f"Failed to load default.nsu: {str(e)}")
                # Fall through to default initialization

        # Default initialization if no file exists or loading failed
        default_operator_slots = [
            ('nsuite', 0),  # First slot is nsuite
            ('tool', 1),   # Second slot is tool
            ('custom', 2),  # Third slot is custom
            ('none', 3),    # Fourth slot is none
        ]

        default_gizmos = [
            ('default', (45, 20), 48, 2.5, True, default_operator_slots, 0),
        ]

        # Create gizmo items based on default configurations
        props.nsu_gizmos_items.clear()

        for name, location, scale, space, flip, operator_slots, index in default_gizmos:
            gizmo = props.nsu_gizmos_items.add()
            gizmo.name = name
            gizmo.location = location
            gizmo.scale = scale
            gizmo.space = space
            gizmo.flip = flip

            # Create slots
            for i in range(75):  # Create all 75 slots
                item = gizmo.list_items.add()
                item.operator = 'none'  # Default to none
                item.nsuite_operator = 'none'  # Default to none

                # Set specific operators for default layout
                if i == 2:  # Position for hard_loop_cut
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'hard_loop_cut'
                elif i == 7:  # Position for loop_cut
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'loop_cut'
                elif i == 12:  # Position for hard_edge_slide
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'hard_edge_slide'
                elif i == 17:  # Position for offset_edges
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'offset_edges'
                elif i == 22:  # Position for bevel
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'bevel'
                elif i == 27:  # Position for mesh_cut
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'mesh_cut'
                elif i == 32:  # Position for project_line
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'project_line'
                elif i == 37:  # Position for project_loop
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'project_loop'
                elif i == 42:  # Position for project_circle
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'project_circle'
                elif i == 47:  # Position for project_grid
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'project_grid'
                elif i == 52:  # Position for select_smartloop
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'select_smartloop'
                elif i == 57:  # Position for analyze
                    item.operator = 'nsuite'
                    item.nsuite_operator = 'analyze'

        props.nsu_gizmos_index = 0

        return {'FINISHED'}


class NSOLVE_MT_NsuiteOperatorsAddMenu(bpy.types.Menu):
    bl_label = "Add Operator Menu"
    bl_idname = "NSOLVE_MT_add_operators_gizmo_menu"
    bl_description = ""

    def draw(self, context):
        layout = self.layout
        for ops_type, name, _ in operators:
            layout.operator("nsolve.add_operator", text=f"Add {name}").operator = ops_type


class NSOLVE_UL_NsuiteOpsGizmoList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        if item:
            op_name = next((name for code, name, desc in operators if code == item.operator), "Unknown")
            layout.label(text=f"{op_name}", translate=False)

    def draw_filter(self, context, layout):
        pass


class NsuiteOpsGizmoList(bpy.types.PropertyGroup):
    # Store the type of modifier
    operator: bpy.props.EnumProperty(name="Items", description="Items", items=operators, default='none', update=refresh_gizmo)
    nsuite_operator: bpy.props.EnumProperty(name="NSuite Operator", description="NSuite operator to use", items=nsuite_operators, default='hard_loop_cut', update=refresh_gizmo)
    tool_operator: bpy.props.StringProperty(name="Tool Operator", description="Tool operator to use", default="", update=refresh_gizmo)
    custom_operator: bpy.props.StringProperty(name="Operator", description="Custom Operator", default="", update=refresh_gizmo)
    custom_properties: bpy.props.CollectionProperty(name="Custom Properties", description="Properties for the custom operator", type=CustomOperatorProperty)
    custom_properties_index: bpy.props.IntProperty(name="Index", description="Index", default=-1)
    custom_icon: bpy.props.StringProperty(name="Custom Icon", description="Custom icon from png folder", default="custom.png", update=refresh_gizmo)
    operator_properties: bpy.props.CollectionProperty(name="Operator Properties", description="Properties for the operator", type=CustomOperatorProperty)
    script: bpy.props.StringProperty(name="Script", description="Script to execute", default="", update=refresh_gizmo)
    script_description: bpy.props.StringProperty(name="Script Description", description="", default="", update=refresh_gizmo)


class NsuiteSearchCandidate(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    description: bpy.props.StringProperty(name="Description")


class OperatorFilter(bpy.types.PropertyGroup):
    def update_operator_filter(self, context):
        # Update the operator search candidates when filter changes
        context.window_manager.nsolve.nsuite.temp_operators.update_search_candidates(context)

    name: bpy.props.StringProperty(
        name="Filter",
        description="Operator prefix to filter (e.g. 'mesh', 'view3d')",
        default="",
        update=update_operator_filter
    )
    enabled: bpy.props.BoolProperty(
        name="Enabled",
        description="Enable/disable this filter",
        default=True,
        update=update_operator_filter
    )


class NsuiteTemporaryProperties(bpy.types.PropertyGroup):
    show_blender_operators: bpy.props.BoolProperty(
        name="Show Blender Operators",
        description="Show Blender operators in the list",
        default=True
    )
    show_custom_operators: bpy.props.BoolProperty(
        name="Show Custom Operators",
        description="Show custom operators in the list",
        default=True
    )
    operator_filters: bpy.props.CollectionProperty(
        type=OperatorFilter,
        name="Operator Filters",
        description="List of operator prefix filters"
    )
    operator_search_candidates: bpy.props.CollectionProperty(
        type=bpy.types.PropertyGroup,
        name="Operator Search Candidates",
        description="List of operators for dynamic search"
    )
    icon_search_candidates: bpy.props.CollectionProperty(
        type=bpy.types.PropertyGroup,
        name="Icon Search Candidates",
        description="List of available icons for dynamic search"
    )
    operator_properties: bpy.props.CollectionProperty(
        type=CustomOperatorProperty,
        name="Operator Properties",
        description="Properties for operators"
    )
    geometry_node_groups: bpy.props.CollectionProperty(
        type=bpy.types.PropertyGroup,
        name="Geometry Node Groups",
        description="List of available geometry node groups"
    )

    def update_geometry_node_groups(self, context):
        self.geometry_node_groups.clear()
        for ng in bpy.data.node_groups:
            # Only include geometry nodes that are tools
            if ng.bl_idname == 'GeometryNodeTree' and ng.is_tool:
                item = self.geometry_node_groups.add()
                item.name = ng.name

    def update_search_candidates(self, context):
        # Clear existing candidates
        temp_props = context.window_manager.nsolve.nsuite.temp_operators
        temp_props.operator_search_candidates.clear()

        show_blender = temp_props.show_blender_operators

        if show_blender:
            # Get enabled filters
            enabled_filters = [f.name.lower() for f in temp_props.operator_filters if f.enabled and f.name.strip()]

            # If no filters exist yet, add default ones
            if not temp_props.operator_filters:
                default_filters = ['mesh', 'view3d', 'transform', 'hops', 'bc']
                for filter_name in default_filters:
                    new_filter = temp_props.operator_filters.add()
                    new_filter.name = filter_name
                    new_filter.enabled = True
                enabled_filters = default_filters

            for category in dir(bpy.ops):
                if not category.startswith('_'):
                    # Only process categories that match our enabled filters
                    if category.lower() in enabled_filters:
                        category_ops = getattr(bpy.ops, category)
                        for op_name in dir(category_ops):
                            if not op_name.startswith('_'):
                                full_name = f"{category}.{op_name}"
                                item = temp_props.operator_search_candidates.add()
                                item.name = full_name


class NsuiteNsuPanelPref(bpy.types.PropertyGroup):
    hide: bpy.props.BoolProperty(name="Hide", description="Hide", default=True, update=refresh_gizmo)
    enable: bpy.props.BoolProperty(name="Expand NSU", description="", default=False)
    layout: bpy.props.BoolProperty(name="Layout", description="Layout", default=True)
    swap: bpy.props.BoolProperty(name="Swap", description="Swap", default=False, update=jump_to_nsolve_tool)


class NsuiteGizmoList(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    location: bpy.props.FloatVectorProperty(name="Operators Gizmo Location", description="Gizmo Location", default=(45, 20), size=2, max=99, min=1, update=refresh_gizmo)
    scale: bpy.props.IntProperty(name="Gizmo Scale", description="Gizmo Scale", default=48, min=16, max=256, update=refresh_gizmo)
    space: bpy.props.FloatProperty(name="Gizmo Space", description="Gizmo Space", default=2.5, min=2, max=3, update=refresh_gizmo)
    flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=True, update=refresh_gizmo)
    list_items: bpy.props.CollectionProperty(type=NsuiteOpsGizmoList)
    list_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)


class NsuitePersonaGizmoList(bpy.types.PropertyGroup):
    persona: bpy.props.StringProperty()


class NSOLVE_UL_NsuitePersonaList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            text = item.persona[:-4]
            layout.label(text=text)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list

        # Initialize with everything visible
        flt_flags = [self.bitflag_filter_item] * len(items)
        flt_neworder = []

        return flt_flags, flt_neworder


class NSOLVE_OT_ApplyNsuPersona(bpy.types.Operator):
    bl_idname = "nsolve.apply_nsu_persona"
    bl_label = "Apply NSU Persona"
    bl_description = "Apply selected NSU persona"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            nsuite = addon.pref().tools.nsuite
            index = nsuite.nsu_persona_index

            if index < 0 or index >= len(nsuite.nsu_persona_items):
                self.report({'ERROR'}, "No persona selected")
                return {'CANCELLED'}

            persona = nsuite.nsu_persona_items[index]
            persona_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite", persona.persona)

            if not os.path.exists(persona_path):
                self.report({'ERROR'}, f"Persona file not found: {persona_path}")
                return {'CANCELLED'}

            # Get valid operator values
            valid_operators = {item[0] for item in operators}
            valid_nsuite_operators = {item[0] for item in nsuite_operators}

            # Load persona data
            with open(persona_path, 'r') as f:
                layout_data = json.load(f)

            # Clear existing items
            nsuite.nsu_gizmos_items.clear()

            for gizmo_data in layout_data:
                gizmo = nsuite.nsu_gizmos_items.add()
                gizmo.name = gizmo_data.get('name', 'default')
                gizmo.location = gizmo_data.get('location', (45, 20))
                gizmo.scale = gizmo_data.get('scale', 48)
                gizmo.space = gizmo_data.get('space', 2.5)
                gizmo.flip = gizmo_data.get('flip', True)

                for item_data in gizmo_data.get('list_items', []):
                    item = gizmo.list_items.add()

                    # Validate operator values against defined enums
                    op = item_data.get('operator', 'none')
                    item.operator = op if op in valid_operators else 'none'

                    nsuite_op = item_data.get('nsuite_operator', 'none')
                    item.nsuite_operator = nsuite_op if nsuite_op in valid_nsuite_operators else 'none'

                    item.tool_operator = item_data.get('tool_operator', '')
                    item.custom_operator = item_data.get('custom_operator', '')
                    item.custom_icon = item_data.get('custom_icon', 'custom.png')

                    # Import operator properties
                    for prop_data in item_data.get('operator_properties', []):
                        prop = item.operator_properties.add()
                        prop.name = prop_data.get('name', '')
                        prop.type = prop_data.get('type', 'INT')

                        # Set the appropriate value based on type
                        if prop.type == 'INT':
                            prop.value_int = prop_data.get('value', 0)
                        elif prop.type == 'FLOAT':
                            prop.value_float = prop_data.get('value', 0.0)
                        elif prop.type == 'STRING':
                            prop.value_string = prop_data.get('value', '')
                        elif prop.type == 'BOOL':
                            prop.value_bool = prop_data.get('value', False)
                        elif prop.type == 'ENUM':
                            prop.value_enum = prop_data.get('value', '')

            self.report({'INFO'}, f"Successfully applied persona: {persona.persona}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply persona: {str(e)}")
            return {'CANCELLED'}


class NSOLVE_OT_RemoveNsuPersona(bpy.types.Operator):
    bl_idname = "nsolve.remove_nsu_persona"
    bl_label = "Remove NSU Persona"
    bl_description = "Remove selected NSU persona file"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = addon.pref().tools.nsuite
        if props.nsu_persona_index >= 0:
            item = props.nsu_persona_items[props.nsu_persona_index]
            if item.persona == "default.nsu":
                self.report({'ERROR'}, "Cannot remove default persona")
                return {'CANCELLED'}

            filepath = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite", item.persona)
            try:
                os.remove(filepath)
                # Refresh the list
                bpy.ops.nsolve.refresh_nsu_personas()
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f"Failed to remove persona: {str(e)}")
                return {'CANCELLED'}
        return {'CANCELLED'}

class NSOLVE_OT_RefreshNsuPersonas(bpy.types.Operator):
    bl_idname = "nsolve.refresh_nsu_personas"
    bl_label = "Refresh NSU Personas"
    bl_description = "Refresh NSU personas list"

    def execute(self, context):
        props = addon.pref().tools.nsuite
        config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite")

        # Clear existing items
        props.nsu_persona_items.clear()

        # Add all .nsu files
        if os.path.exists(config_dir):
            for filename in os.listdir(config_dir):
                if filename.endswith('.nsu'):
                    item = props.nsu_persona_items.add()
                    item.persona = filename

        return {'FINISHED'}


class NSOLVE_OT_OpenNsuFolder(bpy.types.Operator):
    bl_idname = "nsolve.open_nsu_folder"
    bl_label = "Open NSU Folder"
    bl_description = "Open NSU config folder in file explorer"

    def execute(self, context):
        config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite")
        config_dir = os.path.abspath(config_dir)

        if os.path.exists(config_dir):
            bpy.ops.wm.path_open(filepath=config_dir)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Config folder does not exist")
            return {'CANCELLED'}


class NSOLVE_OT_SaveNsuPersona(bpy.types.Operator, ExportHelper):
    bl_idname = "nsolve.save_nsu_persona"
    bl_label = "Save NSU Persona"
    bl_description = "Save current layout as NSU persona"

    filename_ext = ".nsu"
    filter_glob: bpy.props.StringProperty(default="*.nsu", options={'HIDDEN'})

    def invoke(self, context, event):
        # Set default path to config/nsuite folder
        config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite")
        self.filepath = os.path.join(os.path.abspath(config_dir), "new_persona.nsu")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        """Execute the export operation."""
        try:
            nsuite = addon.pref().tools.nsuite
            gizmos_data = []

            for gizmo in nsuite.nsu_gizmos_items:
                gizmo_data = {
                    'name': gizmo.name,
                    'location': list(gizmo.location),
                    'scale': gizmo.scale,
                    'space': gizmo.space,
                    'flip': gizmo.flip,
                    'list_items': []
                }

                for item in gizmo.list_items:
                    item_data = {
                        'operator': item.operator,
                        'nsuite_operator': item.nsuite_operator,
                        'tool_operator': item.tool_operator,
                        'custom_operator': item.custom_operator,
                        'custom_icon': item.custom_icon,
                        'operator_properties': [],
                        'script': item.script,
                        'script_description': item.script_description,
                    }

                    # Export operator properties
                    for prop in item.operator_properties:
                        prop_data = {
                            'name': prop.name,
                            'type': prop.type,
                        }

                        # Get the appropriate value based on type
                        if prop.type == 'INT':
                            prop_data['value'] = prop.value_int
                        elif prop.type == 'FLOAT':
                            prop_data['value'] = prop.value_float
                        elif prop.type == 'STRING':
                            prop_data['value'] = prop.value_string
                        elif prop.type == 'BOOL':
                            prop_data['value'] = prop.value_bool
                        elif prop.type == 'ENUM':
                            prop_data['value'] = prop.value_enum

                        item_data['operator_properties'].append(prop_data)

                    gizmo_data['list_items'].append(item_data)

                gizmos_data.append(gizmo_data)

            with open(self.filepath, 'w') as f:
                json.dump(gizmos_data, f, indent=4)

            self.report({'INFO'}, f"Successfully exported layout to {self.filepath}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to export layout: {str(e)}")
            return {'CANCELLED'}


class NSOLVE_OT_ExportNsuiteLayout(bpy.types.Operator, ExportHelper):
    bl_idname = "nsolve.export_nsuite_layout"
    bl_label = "Export Layout"
    bl_description = "Export layout to file"

    filename_ext = ".nsu"
    filter_glob: bpy.props.StringProperty(default="*.nsu", options={'HIDDEN'})

    def execute(self, context):
        """Execute the export operation."""
        try:
            nsuite = addon.pref().tools.nsuite
            gizmos_data = []

            for gizmo in nsuite.nsu_gizmos_items:
                gizmo_data = {
                    'name': gizmo.name,
                    'location': list(gizmo.location),
                    'scale': gizmo.scale,
                    'space': gizmo.space,
                    'flip': gizmo.flip,
                    'list_items': []
                }

                for item in gizmo.list_items:
                    item_data = {
                        'operator': item.operator,
                        'nsuite_operator': item.nsuite_operator,
                        'tool_operator': item.tool_operator,
                        'custom_operator': item.custom_operator,
                        'custom_icon': item.custom_icon,
                        'operator_properties': [],
                        'script': item.script,
                        'script_description': item.script_description,
                    }

                    # Export operator properties
                    for prop in item.operator_properties:
                        prop_data = {
                            'name': prop.name,
                            'type': prop.type,
                        }

                        # Get the appropriate value based on type
                        if prop.type == 'INT':
                            prop_data['value'] = prop.value_int
                        elif prop.type == 'FLOAT':
                            prop_data['value'] = prop.value_float
                        elif prop.type == 'STRING':
                            prop_data['value'] = prop.value_string
                        elif prop.type == 'BOOL':
                            prop_data['value'] = prop.value_bool
                        elif prop.type == 'ENUM':
                            prop_data['value'] = prop.value_enum

                        item_data['operator_properties'].append(prop_data)

                    gizmo_data['list_items'].append(item_data)

                gizmos_data.append(gizmo_data)

            with open(self.filepath, 'w') as f:
                json.dump(gizmos_data, f, indent=4)

            self.report({'INFO'}, f"Successfully exported layout to {self.filepath}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to export layout: {str(e)}")
            return {'CANCELLED'}


class NSOLVE_OT_ImportNsuiteLayout(bpy.types.Operator, ImportHelper):
    bl_idname = "nsolve.import_nsuite_layout"
    bl_label = "Import Layout"
    bl_description = "Import layout from file"

    filename_ext = ".nsu"
    filter_glob: bpy.props.StringProperty(default="*.nsu", options={'HIDDEN'})

    def execute(self, context):
        props = addon.pref().tools.nsuite

        try:
            # Read and validate file
            try:
                with open(self.filepath, 'r') as f:
                    layout_data = json.load(f)

                if not isinstance(layout_data, list):
                    self.report({'ERROR'}, "Invalid file format: Expected a list of gizmos")
                    return {'CANCELLED'}
            except json.JSONDecodeError as e:
                self.report({'ERROR'}, f"Invalid JSON file: {str(e)}")
                return {'CANCELLED'}
            except IOError as e:
                self.report({'ERROR'}, f"Failed to read file: {str(e)}")
                return {'CANCELLED'}

            # Clear existing items
            props.nsu_gizmos_items.clear()

            # Get valid enum values
            valid_operators = {item[0] for item in operators}
            valid_nsuite_operators = {item[0] for item in nsuite_operators}

            # Import data
            for gizmo_data in layout_data:
                try:
                    gizmo = props.nsu_gizmos_items.add()
                    gizmo.name = gizmo_data.get('name', '')
                    gizmo.location = gizmo_data.get('location', (45, 20))
                    gizmo.scale = gizmo_data.get('scale', 48)
                    gizmo.space = gizmo_data.get('space', 2.5)
                    gizmo.flip = gizmo_data.get('flip', True)

                    for item_data in gizmo_data.get('list_items', []):
                        item = gizmo.list_items.add()

                        # Validate operator values against defined enums
                        op = item_data.get('operator', 'none')
                        item.operator = op if op in valid_operators else 'none'

                        nsuite_op = item_data.get('nsuite_operator', 'none')
                        item.nsuite_operator = nsuite_op if nsuite_op in valid_nsuite_operators else 'none'

                        item.tool_operator = item_data.get('tool_operator', '')
                        item.custom_operator = item_data.get('custom_operator', '')
                        item.custom_icon = item_data.get('custom_icon', 'custom.png')

                        # Import operator properties
                        for prop_data in item_data.get('operator_properties', []):
                            prop = item.operator_properties.add()
                            prop.name = prop_data.get('name', '')
                            prop.type = prop_data.get('type', 'INT')

                            # Set the appropriate value based on type
                            if prop.type == 'INT':
                                prop.value_int = prop_data.get('value', 0)
                            elif prop.type == 'FLOAT':
                                prop.value_float = prop_data.get('value', 0.0)
                            elif prop.type == 'STRING':
                                prop.value_string = prop_data.get('value', '')
                            elif prop.type == 'BOOL':
                                prop.value_bool = prop_data.get('value', False)
                            elif prop.type == 'ENUM':
                                prop.value_enum = prop_data.get('value', '')

                except Exception as e:
                    self.report({'WARNING'}, f"Failed to import gizmo {gizmo_data.get('name', 'unknown')}: {str(e)}")
                    continue

            # Refresh the UI
            refresh_gizmo(None, None)

            # Force a redraw of the viewport
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            self.report({'INFO'}, f"Successfully imported layout from {self.filepath}")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to import layout: {str(e)}")
            return {'CANCELLED'}


class NSOLVE_OT_SetOperator(bpy.types.Operator):
    bl_idname = "nsolve.set_operator"
    bl_label = "Set Operator"
    bl_description = "Set the operator for the gizmo"
    bl_options = {'REGISTER', 'INTERNAL'}

    operator: bpy.props.StringProperty(
        name="Operator",
        description="Operator to set",
        default=""
    )

    nsuite_operator: bpy.props.StringProperty(
        name="NSuite Operator",
        description="NSuite operator to set",
        default=""
    )

    def execute(self, context):
        props = addon.pref().tools.nsuite
        if props.nsu_gizmos_index >= 0:
            gizmo = props.nsu_gizmos_items[props.nsu_gizmos_index]
            if gizmo.list_index >= 0:
                item = gizmo.list_items[gizmo.list_index]
                item.operator = self.operator
                if self.nsuite_operator:
                    item.nsuite_operator = self.nsuite_operator
                refresh_gizmo(None, None)
        return {'FINISHED'}

class NSOLVE_MT_Choose_Operator(bpy.types.Menu):
    bl_label = 'Choose Operator'
    bl_idname = 'NSOLVE_MT_Choose_Operator'

    def draw(self, context):
        layout = self.layout

        # Main operators
        for op_id, op_name, op_desc in operators:
            if op_id == 'nsuite':
                # NSuite submenu
                layout.menu("NSOLVE_MT_NsuiteOperators", text=op_name)
            elif op_id == 'tool':
                # Tools submenu
                layout.menu("NSOLVE_MT_ToolsOperators", text=op_name)
            else:
                # Regular operators
                op = layout.operator("nsolve.set_operator", text=op_name)
                op.operator = op_id

class NSOLVE_MT_NsuiteOperators(bpy.types.Menu):
    bl_label = "NSuite Operators"
    bl_idname = "NSOLVE_MT_NsuiteOperators"

    def draw(self, context):
        layout = self.layout
        for nsuite_op_id, nsuite_op_name, nsuite_op_desc in nsuite_operators:
            if nsuite_op_id != 'none':  # Skip the none option
                op = layout.operator("nsolve.set_operator", text=nsuite_op_name)
                op.operator = 'nsuite'  # Set main operator to nsuite
                op.nsuite_operator = nsuite_op_id  # Set the specific nsuite operator

class NSOLVE_MT_ToolsOperators(bpy.types.Menu):
    bl_label = "Tools Operators"
    bl_idname = "NSOLVE_MT_ToolsOperators"

    def draw(self, context):
        layout = self.layout
        for tool in get_geometry_node_tools():
            op = layout.operator("nsolve.set_operator", text=tool[1])
            op.operator = 'tool'  # Set main operator to tool
            op.nsuite_operator = tool[0]  # Store the tool ID in nsuite_operator

class NSOLVE_OT_ManageOperatorFilters(bpy.types.Operator):
    bl_idname = "nsolve.manage_operator_filters"
    bl_label = "Manage Operator Filters"
    bl_description = "Manage operator prefix filters"
    bl_options = {'REGISTER', 'INTERNAL'}

    def add_default_filters(self, temp_props):
        # Clear any existing filters first
        temp_props.operator_filters.clear()

        default_filters = ['mesh', 'view3d', 'transform', 'hops', 'bc']
        for filter_name in default_filters:
            new_filter = temp_props.operator_filters.add()
            new_filter.name = filter_name
            new_filter.enabled = True

    def draw(self, context):
        layout = self.layout
        temp_props = context.window_manager.nsolve.nsuite.temp_operators

        # Add default filters if none exist
        if len(temp_props.operator_filters) == 0:
            self.add_default_filters(temp_props)

        # Draw filter list
        for i, filter_item in enumerate(temp_props.operator_filters):
            row = layout.row(align=True)

            # Enable/disable toggle
            row.prop(filter_item, "enabled", text="", icon='HIDE_OFF' if filter_item.enabled else 'HIDE_ON')

            # Filter name
            row.prop(filter_item, "name", text="")

            # Remove button
            remove_op = row.operator("nsolve.remove_operator_filter", text="", icon='X')
            remove_op.index = i

        # Add new filter button
        layout.operator("nsolve.add_operator_filter", text="Add Filter", icon='ADD')

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class NSOLVE_OT_AddOperatorFilter(bpy.types.Operator):
    bl_idname = "nsolve.add_operator_filter"
    bl_label = "Add Filter"
    bl_description = "Add a new operator filter"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        temp_props = context.window_manager.nsolve.nsuite.temp_operators
        new_filter = temp_props.operator_filters.add()
        new_filter.enabled = True
        return {'FINISHED'}

class NSOLVE_OT_RemoveOperatorFilter(bpy.types.Operator):
    bl_idname = "nsolve.remove_operator_filter"
    bl_label = "Remove Filter"
    bl_description = "Remove this operator filter"
    bl_options = {'REGISTER', 'INTERNAL'}

    index: bpy.props.IntProperty()

    def execute(self, context):
        temp_props = context.window_manager.nsolve.nsuite.temp_operators
        temp_props.operator_filters.remove(self.index)
        return {'FINISHED'}

class types():
    class pref(bpy.types.PropertyGroup):
        ops_gizmo_location: bpy.props.FloatVectorProperty(name="Operators Gizmo Location", description="Gizmo Location", default=(45, 20), size=2, max=99, min=1, update=refresh_gizmo)
        ops_gizmo_scale: bpy.props.IntProperty(name="Gizmo Scale", description="Gizmo Scale", default=48, min=16, max=256, update=refresh_gizmo)
        ops_gizmo_space: bpy.props.FloatProperty(name="Gizmo Space", description="Gizmo Space", default=2.5, min=2, max=3, update=refresh_gizmo)
        ops_gizmo_flip: bpy.props.BoolProperty(name="Flip", description="Flip", default=True, update=refresh_gizmo)
        ops_gizmo_list_items: bpy.props.CollectionProperty(type=NsuiteOpsGizmoList)
        ops_gizmo_list_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)

        nsu: bpy.props.PointerProperty(type=NsuiteNsuPanelPref)
        nsu_edit_mode: bpy.props.BoolProperty(name="Edit Mode", description="Enable gizmo edit mode", default=False, update=refresh_gizmo)

        nsu_persona_items: bpy.props.CollectionProperty(type=NsuitePersonaGizmoList)
        nsu_persona_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)
        nsu_gizmos_items: bpy.props.CollectionProperty(type=NsuiteGizmoList)
        nsu_gizmos_index: bpy.props.IntProperty(name="Index", description="Index", default=-1, update=refresh_gizmo)

        continuous_cut: bpy.props.BoolProperty(name="MeshCut - Multi", description="Multi cut on mesh cut until esc", default=False)

    class window_manager(bpy.types.PropertyGroup):
        temp_properties: bpy.props.PointerProperty(type=NsuiteTemporaryProperties)
        temp_operators: bpy.props.PointerProperty(type=NsuiteTemporaryProperties)


types_classes = (
    CustomOperatorProperty,
    NsuiteNsuPanelPref,
    NsuiteSearchCandidate,
    NsuiteOpsGizmoList,
    OperatorFilter,
    NsuiteTemporaryProperties,
    NsuiteGizmoList,
    NsuitePersonaGizmoList,
    NSOLVE_UL_NsuiteOpsGizmoList,
    NSOLVE_UL_NsuitePersonaList,
    types.pref,
    types.window_manager,
)

classes = (
    NSOLVE_OT_ManageOperatorFilters,
    NSOLVE_OT_AddOperatorFilter,
    NSOLVE_OT_RemoveOperatorFilter,
    NSOLVE_OT_NsuiteRestoreDefaultOperartors,
    NSOLVE_OT_NsuiteAddOperator,
    NSOLVE_MT_NsuiteOperatorsAddMenu,
    NSOLVE_OT_EditCustomOperatorProperties,
    NSOLVE_PT_Nsuite,
    NSOLVE_OT_ConfigureGizmoButton,
    NSOLVE_OT_AddCustomProperty,
    NSOLVE_OT_RemoveCustomProperty,
    NSOLVE_OT_ExportNsuiteLayout,
    NSOLVE_OT_ImportNsuiteLayout,
    NSOLVE_OT_ApplyNsuPersona,
    NSOLVE_OT_RemoveNsuPersona,
    NSOLVE_OT_RefreshNsuPersonas,
    NSOLVE_OT_OpenNsuFolder,
    NSOLVE_OT_SaveNsuPersona,
    NSOLVE_OT_SetOperator,
    NSOLVE_MT_Choose_Operator,
    NSOLVE_MT_NsuiteOperators,
    NSOLVE_MT_ToolsOperators,
    NSOLVE_OT_CustomIconSelect,
    NSOLVE_OT_SelectIcon,
)

def initialize_nsuite_gizmos(props=None, operator_slots=None):
    """Initialize NSuite gizmos by loading from default.nsu or using hardcoded defaults if file doesn't exist.

    Args:
        props: NSuite properties, defaults to addon preferences if None
        operator_slots: Optional custom operator slot configuration
    """
    if props is None:
        props = addon.pref().tools.nsuite

    def validate_gizmo_structure():
        """Validate the structure of gizmos items and their list items.
        Returns True if valid, False if invalid."""
        if len(props.nsu_gizmos_items) == 0:
            return False

        required_gizmo_fields = {
            'name': str,
            'location': 'FloatVector',  # Special case for FloatVectorProperty
            'scale': int,
            'space': float,
            'flip': bool,
            'list_items': list
        }

        required_item_fields = {
            'operator': str,
            'nsuite_operator': str,
            'tool_operator': str,
            'custom_operator': str,
            'custom_icon': str,
            'operator_properties': list
        }

        for gizmo in props.nsu_gizmos_items:
            # Check gizmo fields
            for field, field_type in required_gizmo_fields.items():
                if not hasattr(gizmo, field):
                    print(f"Missing required gizmo field: {field}")
                    return False

                value = getattr(gizmo, field)
                if field == 'list_items':
                    if not value:  # Check if list_items exists and is not empty
                        print(f"Gizmo {gizmo.name} has no list items")
                        return False
                elif field == 'location':
                    # Check if location is a FloatVectorProperty with size 2
                    try:
                        if len(value) != 2 or not all(isinstance(v, float) for v in value):
                            print(f"Invalid location format for gizmo {gizmo.name}")
                            return False
                    except (TypeError, AttributeError):
                        print(f"Invalid location type for gizmo {gizmo.name}")
                        return False
                elif not isinstance(value, field_type):
                    print(f"Invalid type for field {field} in gizmo {gizmo.name}")
                    return False

            # Check each list item
            for item in gizmo.list_items:
                for field, field_type in required_item_fields.items():
                    if not hasattr(item, field):
                        print(f"Missing required item field: {field}")
                        return False

                    value = getattr(item, field)
                    if field != 'operator_properties' and not isinstance(value, field_type):
                        print(f"Invalid type for field {field} in gizmo {gizmo.name}")
                        return False

        return True

    # Skip initialization if there are existing items and no operator_slots override
    if len(props.nsu_gizmos_items) > 0 and operator_slots is None:
        # Validate existing structure
        if validate_gizmo_structure():
            return
        else:
            # If validation fails, clear items to reinitialize with defaults
            print("Invalid gizmo structure detected, reinitializing with defaults")
            props.nsu_gizmos_items.clear()

    # Try to load from default.nsu first
    default_nsu_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "nsuite", "default.nsu")

    # Only try to import if the file exists
    if os.path.exists(default_nsu_path):
        bpy.ops.nsolve.import_nsuite_layout(filepath=default_nsu_path)
        # Validate imported structure
        if validate_gizmo_structure():
            return
        else:
            print("Invalid structure in default.nsu, falling back to hardcoded defaults")
            props.nsu_gizmos_items.clear()

    # If file doesn't exist or validation failed, use hardcoded defaults
    print("Using hardcoded defaults")

    # Clear existing items
    props.nsu_gizmos_items.clear()

    # Create default gizmo
    gizmo = props.nsu_gizmos_items.add()
    gizmo.name = 'default'
    gizmo.location = (45, 20)
    gizmo.scale = 48
    gizmo.space = 2.5
    gizmo.flip = True

    # Initialize all slots
    for i in range(75):
        item = gizmo.list_items.add()
        item.operator = 'none'
        item.nsuite_operator = 'none'

        # Set specific operators for default layout
        if i == 2:  # Position for hard_loop_cut
            item.operator = 'nsuite'
            item.nsuite_operator = 'hard_loop_cut'
        elif i == 7:  # Position for loop_cut
            item.operator = 'nsuite'
            item.nsuite_operator = 'loop_cut'
        elif i == 12:  # Position for hard_edge_slide
            item.operator = 'nsuite'
            item.nsuite_operator = 'hard_edge_slide'
        elif i == 17:  # Position for offset_edges
            item.operator = 'nsuite'
            item.nsuite_operator = 'offset_edges'
        elif i == 22:  # Position for bevel
            item.operator = 'nsuite'
            item.nsuite_operator = 'bevel'
        elif i == 27:  # Position for mesh_cut
            item.operator = 'nsuite'
            item.nsuite_operator = 'mesh_cut'
        elif i == 32:  # Position for project_line
            item.operator = 'nsuite'
            item.nsuite_operator = 'project_line'
        elif i == 37:  # Position for project_loop
            item.operator = 'nsuite'
            item.nsuite_operator = 'project_loop'
        elif i == 42:  # Position for project_circle
            item.operator = 'nsuite'
            item.nsuite_operator = 'project_circle'
        elif i == 47:  # Position for project_grid
            item.operator = 'nsuite'
            item.nsuite_operator = 'project_grid'
        elif i == 52:  # Position for select_smartloop
            item.operator = 'nsuite'
            item.nsuite_operator = 'select_smartloop'
        elif i == 57:  # Position for analyze
            item.operator = 'nsuite'
            item.nsuite_operator = 'analyze'

    props.nsu_gizmos_index = 0

def get_geometry_node_tools():
    """Get a list of available geometry node tools.

    Returns:
        List of tuples: (tool_id, tool_name, tool_description)
    """
    tools = []

    # Get active object
    obj = bpy.context.active_object
    if not obj or not obj.type == 'MESH':
        return tools

    # Check if object has geometry nodes modifier
    for modifier in obj.modifiers:
        if modifier.type == 'NODES':
            # Get node group
            node_group = modifier.node_group
            if node_group:
                # Add nodes as tools
                for node in node_group.nodes:
                    if node.type not in {'GROUP_INPUT', 'GROUP_OUTPUT'}:
                        tool_id = f"geonode_{node.bl_idname.lower()}"
                        tool_name = node.bl_label
                        tool_desc = f"Geometry Node: {node.bl_label}"
                        tools.append((tool_id, tool_name, tool_desc))

    return tools
