import bpy
from . import ops, tools, types
from .. import __package__ as base_package
import rna_keymap_ui


nsolve_items = [
    ('NONE', 'None', 'None'),
    ('SELECT', 'Select', 'Select'),
    ('JOIN', 'Join', 'Join'),
    ('MERGE', 'Merge', 'Merge'),
    ('SLIDE', 'Slide', 'Slide'),
    ('LINE', 'Line', 'Line'),
    ('COLLAPSE', 'Collapse', 'Collapse'),
    ('DISSOLVE', 'Dissolve', 'Dissolve'),
    ('OFFSET', 'Offset', 'Offset'),
    ('KNIFE', 'Knife', 'Knife'),
]

nsuite_items = [
    ('NONE', 'None', 'None'),
    ('nsolve.set_nsolve_tool', 'Set nSolve', 'Set nSolve as active tool'),
    ('nsolve.set_nsuite_tool', 'Set nSuite', 'Set nSuite as active tool'),
    ('nsolve.set_nflow_tool', 'Set nFlow', 'Set nFlow as active tool'),
    ('nsolve.hard_loop_cut', 'Hard Loop Cut', 'Hard Loop Cut'),
    ('mesh.loopcut_slide', 'Loop Cut', 'Loop Cut'),
    ('nsolve.hard_edge_slide', 'Hard Edge slide', 'Hard Edge slide'),
    ('nsolve.offset_edges', 'Offset Edges', 'Offset Edges'),
    ('nsolve.bevel', 'Bevel', 'Bevel'),
    ('nsolve.mesh_cut', 'Mesh Cut', 'Mesh Cut'),
    ('nsolve.project_line', 'Project Line', 'Project Line'),
    ('nsolve.project_loop', 'Project Loop', 'Project Loop'),
    ('nsolve.project_circle', 'Project Circle', 'Project Circle'),
    ('nsolve.project_grid', 'Project Grid', 'Project Grid'),
    ('nsolve.select_rounded_area', 'Select Rounded Area', 'Select Rounded Area'),
    ('nsolve.select_similar_strip', 'Select Similar Strip', 'Select Similar Strip'),
    ('nsolve.select_planarloop', 'Select Planar Loop', 'Select Planar Loop'),
    ('nsolve.select_smartloop', 'Select Smart Loop', 'Select Smart Loop'),
    ('nsolve.analyze', 'Analyze', 'Analyze'),
    ('nsolve.custom', 'Custom', 'Custom'),
]

pie_props = [
    ('NONE', 'None', 'None'),
    ('NSOLVE', 'nSolve', 'nSolve'),
    ('NSUITE', 'nSuite', 'nSuite'),
    ('COLUMN', 'Column', 'Column'),
    ('OPERATOR', 'Operator', 'Custom Operator'),
]

col_props = [
    ('NONE', 'None', 'None'),
    ('ROW', 'Row', 'Row'),
    ('NSOLVE', 'nSolve', 'nSolve'),
    ('NSUITE', 'nSuite', 'nSuite'),
    ('OPERATOR', 'Operator', 'Custom Operator'),
]

row_props = [
    ('NONE', 'None', 'None'),
    ('NSOLVE', 'nSolve', 'nSolve'),
    ('NSUITE', 'nSuite', 'nSuite'),
    ('OPERATOR', 'Operator', 'Custom Operator'),
]


class NSolve_RowElement(bpy.types.PropertyGroup):
    type: bpy.props.EnumProperty(
        items=row_props,
        name="Type",
        default='NONE'
    )
    nsolve_item: bpy.props.EnumProperty(
        items=nsolve_items,
        name="NSolve Action",
        default='NONE'
    )
    nsuite_item: bpy.props.EnumProperty(
        items=nsuite_items,
        name="NSuite Action",
        default='NONE'
    )
    operator_string: bpy.props.StringProperty(name="Operator", description="Custom operator string (e.g. mesh.loopcut_slide)", default="")


class NSolve_RowItem(bpy.types.PropertyGroup):
    type: bpy.props.EnumProperty(
        items=col_props,
        name="Type",
        default='NONE'
    )
    elements: bpy.props.CollectionProperty(type=NSolve_RowElement)
    row_collection: bpy.props.CollectionProperty(type=NSolve_RowElement)
    nsolve_item: bpy.props.EnumProperty(
        items=nsolve_items,
        name="NSolve Action",
        default='NONE'
    )
    nsuite_item: bpy.props.EnumProperty(
        items=nsuite_items,
        name="NSuite Action",
        default='NONE'
    )
    operator_string: bpy.props.StringProperty(name="Operator", description="Custom operator string (e.g. mesh.loopcut_slide)", default="")
    active_row_element_index: bpy.props.IntProperty()  # Index for active row element


class NSolve_Column(bpy.types.PropertyGroup):
    rows: bpy.props.CollectionProperty(type=NSolve_RowItem)
    column_collection: bpy.props.CollectionProperty(type=NSolve_RowItem)
    nsolve_item: bpy.props.EnumProperty(
        items=nsolve_items,
        name="NSolve Action",
        default='NONE'
    )
    nsuite_item: bpy.props.EnumProperty(
        items=nsuite_items,
        name="NSuite Action",
        default='NONE'
    )
    operator_string: bpy.props.StringProperty(name="Operator", description="Custom operator string (e.g. mesh.loopcut_slide)", default="")
    active_column_item_index: bpy.props.IntProperty()  # Index for active column item


class NSolve_Preference(bpy.types.AddonPreferences):
    bl_idname = base_package

    settings: bpy.props.EnumProperty(
        name='Settings',
        description='Settings to display',
        items=[
            ('OPTIONS', 'Options', ''),
            ('THEME', 'Theme', ''),
            ('KEYMAP', 'Keymap', ''),
            ('INTERFACE', 'Interface', ''),
            ('NFLOW', 'nFlow', ''),
            ('ANALYTICS', 'Analytics', ''),
        ],
        default='OPTIONS'
    )

    tools: bpy.props.PointerProperty(type=tools.types.pref)
    ops: bpy.props.PointerProperty(type=ops.types.pref)
    theme: bpy.props.PointerProperty(type=types.Theme)

    nflow: bpy.props.PointerProperty(type=ops.nflow.types.preferences)
    menus: bpy.props.BoolProperty(default=False)
    menus_type: bpy.props.EnumProperty(default='UNIFIED', description='Menu Type', items=[('UNIFIED', 'Unified', ''), ('NATIVE', 'Native', ''),])

    analytics_logs: bpy.props.BoolProperty(default=False)
    analytics_stats: bpy.props.BoolProperty(default=False)
    analytics_path: bpy.props.StringProperty(name="Analytics Path", description="Select a to analythics folder", default="", subtype='DIR_PATH')

    # Pie Menu Gizmo Settings
    pie_gizmo_top: bpy.props.EnumProperty(name="Top", description="Top button action", items=pie_props, default='NSOLVE')
    pie_gizmo_top_right: bpy.props.EnumProperty(name="Top Right", description="Top Right button action", items=pie_props, default='NONE')
    pie_gizmo_right: bpy.props.EnumProperty(name="Right", description="Right button action", items=pie_props, default='NSOLVE')
    pie_gizmo_bottom_right: bpy.props.EnumProperty(name="Bottom Right", description="Bottom Right button action", items=pie_props, default='NSOLVE')
    pie_gizmo_bottom: bpy.props.EnumProperty(name="Bottom", description="Bottom button action", items=pie_props, default='NSUITE')
    pie_gizmo_bottom_left: bpy.props.EnumProperty(name="Bottom Left", description="Bottom Left button action", items=pie_props, default='NONE')
    pie_gizmo_left: bpy.props.EnumProperty(name="Left", description="Left button action", items=pie_props, default='COLUMN')
    pie_gizmo_top_left: bpy.props.EnumProperty(name="Top Left", description="Top Left button action", items=pie_props, default='NONE')

    pie_gizmo_top_expanded: bpy.props.BoolProperty(name="Top Expanded", default=False)
    pie_gizmo_top_right_expanded: bpy.props.BoolProperty(name="Top Right Expanded", default=False)
    pie_gizmo_right_expanded: bpy.props.BoolProperty(name="Right Expanded", default=False)
    pie_gizmo_bottom_right_expanded: bpy.props.BoolProperty(name="Bottom Right Expanded", default=False)
    pie_gizmo_bottom_expanded: bpy.props.BoolProperty(name="Bottom Expanded", default=False)
    pie_gizmo_bottom_left_expanded: bpy.props.BoolProperty(name="Bottom Left Expanded", default=False)
    pie_gizmo_left_expanded: bpy.props.BoolProperty(name="Left Expanded", default=False)
    pie_gizmo_top_left_expanded: bpy.props.BoolProperty(name="Top Left Expanded", default=False)

    pie_menu_expanded: bpy.props.BoolProperty(name="Pie Menu Expanded", default=True)

    pie_gizmo_has_defaults: bpy.props.BoolProperty(default=False) # Track if defaults were set

    # Column Collections for each pie menu position
    columns_top: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_top_right: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_right: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_bottom_right: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_bottom: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_bottom_left: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_left: bpy.props.CollectionProperty(type=NSolve_Column)
    columns_top_left: bpy.props.CollectionProperty(type=NSolve_Column)

    # Active indices for each position
    active_column_index_top: bpy.props.IntProperty()
    active_column_index_top_right: bpy.props.IntProperty()
    active_column_index_right: bpy.props.IntProperty()
    active_column_index_bottom_right: bpy.props.IntProperty()
    active_column_index_bottom: bpy.props.IntProperty()
    active_column_index_bottom_left: bpy.props.IntProperty()
    active_column_index_left: bpy.props.IntProperty()
    active_column_index_top_left: bpy.props.IntProperty()

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        split = column.split(factor=0.2)
        col = split.column(align=True)
        col.prop(self, 'settings', expand=True)
        col = split.column(align=True)
        col.use_property_split = True
        pref = context.preferences.addons[base_package].preferences

        if self.settings == 'OPTIONS':
            col = col.column(align=True)
            col.prop(pref, 'menus', text='Menus')
            if pref.menus:
                col.prop(pref, 'menus_type', text='Menu Type')

            self.transform(context, col, pref)

        elif self.settings == 'KEYMAP':
            # Keymap Settings
            col = col.column(align=True)
            box = col.box()
            box.label(text="Keymap Settings")
            col = box.column(align=True)

            wm = context.window_manager
            kc = wm.keyconfigs.user

            # Pie Menu Hotkey:
            col.label(text="Pie Menu")
            km = kc.keymaps.get('3D View')  # Changed from '3D View Tool: VIEW_3D' to '3D View'
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == 'wm.call_menu_pie' and kmi.properties.name == "NSOLVE_MT_gizmo_pie":
                        col.context_pointer_set("keymap", km)
                        rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

            col.separator(factor=6.0)

            # Tool: nFlow
            interface_options = pref.tools.nsolve.InterfaceOptions
            col = col.column(align=True)

            # Pie Menu Buttons
            col.label(text="Pie Menu")
            box = col.box()

            # Create a collapsible panel for pie menu settings
            header = box.row()
            is_expanded = getattr(pref, 'pie_menu_expanded', False)  # Default to expanded
            header.prop(pref, 'pie_menu_expanded',
                       icon='TRIA_DOWN' if is_expanded else 'TRIA_RIGHT',
                       icon_only=True, emboss=False)
            header.label(text="Pie Menu Settings")

            if is_expanded:
                # Draw settings for each direction
                directions = ['top', 'top_right', 'right', 'bottom_right',
                            'bottom', 'bottom_left', 'left', 'top_left']

                for direction in directions:
                    self.draw_direction_settings(box, pref, direction)

        elif self.settings == 'INTERFACE':
            interface_options = pref.tools.nsolve.InterfaceOptions
            col = col.column(align=True)
            col.use_property_split = True

            for prop in interface_options.bl_rna.properties:
                if prop.identifier == 'rna_type':
                    continue
                if prop.identifier != 'name':
                    col.prop(interface_options, prop.identifier)

        elif self.settings == 'THEME':
            col = col.column(align=True)
            theme = pref.theme

            self.theme_draw(col, pref.tools.nsolve.gizmo_col, 'Gizmo')
            self.theme_draw(col, theme.ops.mesh.project.circle, 'Project Circle')
            self.theme_draw(col, theme.ops.mesh.project.grid, 'Project Grid')
            self.theme_draw(col, theme.ops.mesh.project.line, 'Project Line')
            self.theme_draw(col, theme.ops.mesh.project.loop, 'Project Loop')
            self.theme_draw(col, theme.ops.mesh.project.rake, 'Project Rake')
            self.theme_draw(col, theme.ops.mesh.bevel, 'Bevel')
            self.theme_draw(col, theme.ops.mesh.collapse_verts, 'Collapse Verts')
            self.theme_draw(col, theme.ops.mesh.cut, 'Cut')
            self.theme_draw(col, theme.ops.mesh.dissolve, 'Dissolve')
            self.theme_draw(col, theme.ops.mesh.hard_edge_slide, 'Hard Edge Slide')
            self.theme_draw(col, theme.ops.mesh.hard_loop_cut, 'Hard Loop Cut')
            self.theme_draw(col, theme.ops.mesh.join_verts, 'Join Verts')
            self.theme_draw(col, theme.ops.mesh.merge_verts, 'Merge Verts')
            self.theme_draw(col, theme.ops.mesh.offset_edges, 'Offset Edges')
            self.theme_draw(col, theme.ops.mesh.analyze, 'Analyze')
            self.theme_draw(col, theme.ops.ndraw.pencil, 'Pencil')
            self.theme_draw(col, pref.tools.nsolve.InterfaceColor, 'Interface')
            self.theme_draw(col, pref.tools.nsolve.BannerColor, 'Banner')

        elif self.settings == 'NFLOW':
            self.nflow.draw(col, context)

        elif self.settings == 'ANALYTICS':
            col = col.column(align=True)
            col.label(text="Analytics")
            col.prop(self, 'analytics_path', text='Path')
            col.separator()
            col.prop(self, 'analytics_stats', text='Enable Stats')
            col.prop(self, 'analytics_logs', text='Enable Logs')

    def draw_direction_settings(self, col, pref, direction):
        # Create a box for each direction
        box = col.box()

        # Header row with arrow and label
        header = box.row()
        is_expanded = getattr(pref, f'pie_gizmo_{direction}_expanded', False)
        header.prop(pref, f'pie_gizmo_{direction}_expanded',
                   icon='TRIA_DOWN' if is_expanded else 'TRIA_RIGHT',
                   icon_only=True, emboss=False)

        # Direction label and selector in header
        split = header.split(factor=0.4)
        split.label(text=direction.replace('_', ' ').title())
        split.prop(pref, f'pie_gizmo_{direction}', text="")

        # Only show content if expanded
        if is_expanded:
            # Get the current value for this direction
            prop_value = getattr(pref, f'pie_gizmo_{direction}')

            if prop_value == 'NONE':
                row = box.row()
                row.separator(factor=2.0)
                row.label(text="No item selected")

            # If a specific type is selected, show additional options
            if prop_value != 'NONE':
                sub = box.column(align=True)
                sub.separator(factor=0.5)

                if prop_value == 'NSOLVE':
                    # Get or create a column for this direction
                    if len(getattr(pref, f'columns_{direction}')) == 0:
                        col_item = getattr(pref, f'columns_{direction}').add()
                        setattr(pref, f'active_column_index_{direction}', 0)
                    col_item = getattr(pref, f'columns_{direction}')[getattr(pref, f'active_column_index_{direction}')]

                    # Indent the action selector
                    row = sub.row()
                    row.separator(factor=1.0)
                    row.prop(col_item, 'nsolve_item', text="")

                elif prop_value == 'NSUITE':
                    # Get or create a column for this direction
                    if len(getattr(pref, f'columns_{direction}')) == 0:
                        col_item = getattr(pref, f'columns_{direction}').add()
                        setattr(pref, f'active_column_index_{direction}', 0)
                    col_item = getattr(pref, f'columns_{direction}')[getattr(pref, f'active_column_index_{direction}')]

                    # Indent the action selector
                    row = sub.row()
                    row.separator(factor=1.0)
                    row.prop(col_item, 'nsuite_item', text="")

                elif prop_value == 'COLUMN':
                    # Get or create a column for this direction
                    if len(getattr(pref, f'columns_{direction}')) == 0:
                        col_item = getattr(pref, f'columns_{direction}').add()
                        setattr(pref, f'active_column_index_{direction}', 0)
                    col_item = getattr(pref, f'columns_{direction}')[getattr(pref, f'active_column_index_{direction}')]

                    # Draw column contents
                    for i, row_item in enumerate(col_item.rows):
                        # Main row container
                        main_row = sub.row()
                        main_row.separator(factor=4.0)  # Increased main indentation

                        # Column for the row content
                        row_col = main_row.column()

                        # Row header with type selector
                        header_row = row_col.row(align=True)
                        header_row.prop(row_item, 'type', text='')

                        # Content based on type
                        if row_item.type in ['NSOLVE', 'NSUITE', 'OPERATOR']:
                            # Indented content row
                            content_row = row_col.row()
                            content_row.separator(factor=6.0)  # Increased sub-indentation
                            content_col = content_row.column()

                            if row_item.type == 'NSOLVE':
                                content_col.prop(row_item, 'nsolve_item', text='')
                            elif row_item.type == 'NSUITE':
                                content_col.prop(row_item, 'nsuite_item', text='')
                            else:
                                content_col.prop(row_item, 'operator_string', text='')

                        elif row_item.type == 'ROW':
                            # Container for row elements
                            elements_row = row_col.row()
                            elements_row.separator(factor=6.0)  # Increased sub-indentation
                            elements_col = elements_row.column()

                            # Column for elements
                            element_list_row = elements_col.column(align=True)

                            # Draw each element
                            for j, element in enumerate(row_item.elements):
                                # Element container
                                element_col = element_list_row.column(align=True)

                                # Element header with type and remove button
                                element_header = element_col.row(align=True)
                                element_header.prop(element, 'type', text='')
                                op = element_header.operator('nsolve.remove_row_element', text='', icon='REMOVE')
                                op.index = i
                                op.element_index = j
                                op.direction = direction.lower()

                                # Element content if NSOLVE or NSUITE
                                if element.type in ['NSOLVE', 'NSUITE', 'OPERATOR']:
                                    content_row = element_col.row()
                                    if element.type == 'NSOLVE':
                                        element_col.prop(element, 'nsolve_item', text='')
                                    elif element.type == 'NSUITE':
                                        element_col.prop(element, 'nsuite_item', text='')
                                    else:
                                        element_col.prop(element, 'operator_string', text='')

                                element_list_row.separator(factor=3.0)  # Increased spacing between elements

                            # Add element button in its own row
                            button_row = elements_col.row(align=True)
                            op = button_row.operator('nsolve.add_row_element', text='Add Element', icon='ADD')
                            op.index = i
                            op.direction = direction.lower()

                        # Remove row button
                        op = header_row.operator('nsolve.remove_column_row', text='', icon='REMOVE')
                        op.index = i
                        op.direction = direction.lower()

                        sub.separator(factor=1.0)  # Space between rows

                    # Add row button
                    row = sub.row()
                    row.separator(factor=4.0)  # Match main indentation
                    op = row.operator('nsolve.add_column_row', text='Add Row', icon='ADD')
                    op.direction = direction.lower()

                elif prop_value == 'OPERATOR':
                    # Get or create a column for this direction
                    if len(getattr(pref, f'columns_{direction}')) == 0:
                        col_item = getattr(pref, f'columns_{direction}').add()
                        setattr(pref, f'active_column_index_{direction}', 0)
                    col_item = getattr(pref, f'columns_{direction}')[getattr(pref, f'active_column_index_{direction}')]

                    # Indent the action selector
                    row = sub.row()
                    row.separator(factor=1.0)
                    row.prop(col_item, 'operator_string', text="")

                col.separator()

    def theme_draw(self, layout, theme, label):
        # Get or create folder state for this theme
        folder_states = self.tools.nsolve.folder_states
        folder_state = None
        for state in folder_states:
            if state.name == label:
                folder_state = state
                break
        if not folder_state:
            folder_state = folder_states.add()
            folder_state.name = label

        # Add some space before each box
        layout.separator(factor=0.5)

        # Create box for the theme section
        box = layout.box()

        # Create header row that's fully clickable
        split = box.split(factor=0.7)
        row = split.row(align=True)
        row.use_property_split = False
        row.alignment = 'LEFT'
        row.prop(folder_state, "expanded", text="", icon='TRIA_DOWN' if folder_state.expanded else 'TRIA_RIGHT', emboss=False)
        row.prop(folder_state, "expanded", text=label, emboss=False)

        # Draw properties if expanded
        if folder_state.expanded:
            col = box.column(align=True)
            for prop in theme.bl_rna.properties:
                # ignore blender defined
                if prop.identifier == 'name' or prop.identifier == 'rna_type': continue
                col.prop(theme, prop.identifier)

    def transform(self, context, col, pref):

        col.separator()
        nso = pref.tools.nsolve
        col = col.column()
        #col.prop(nso, 'main_gizmo_shape', text='NSO Shape') #not needed
        col.prop(nso, 'main_gizmo_location', text='NSO Loc')
        col.prop(nso, 'main_gizmo_scale', text='NSO Scale')
        col.prop(nso, 'main_gizmo_magnification', text='NSO Magnification')
        col.prop(nso, 'main_gizmo_spacing', text='NSO Spacing')
        col.separator()

classes = (
    NSolve_RowElement,
    NSolve_RowItem,
    NSolve_Column,
    NSolve_Preference,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


def initialize_pie_operator_list():
    """Initialize the pie menu operator list with default values."""
    preferences = bpy.context.preferences.addons[base_package].preferences
    if preferences.pie_gizmo_has_defaults: return
    preferences.pie_gizmo_has_defaults = True

    # Right: NSOLVE JOIN
    preferences.pie_gizmo_right = 'NSOLVE'
    if len(preferences.columns_right) == 0:
        col = preferences.columns_right.add()
    col = preferences.columns_right[0]
    col.nsolve_item = 'JOIN'

    # Bottom Right: NSOLVE LINE
    preferences.pie_gizmo_bottom_right = 'NSOLVE'
    if len(preferences.columns_bottom_right) == 0:
        col = preferences.columns_bottom_right.add()
    col = preferences.columns_bottom_right[0]
    col.nsolve_item = 'LINE'

    # Bottom: NSUITE mesh cut
    preferences.pie_gizmo_bottom = 'NSUITE'
    if len(preferences.columns_bottom) == 0:
        col = preferences.columns_bottom.add()
    col = preferences.columns_bottom[0]
    col.nsuite_item = 'nsolve.mesh_cut'

    # Left: COLUMN with NSUITE elements
    preferences.pie_gizmo_left = 'COLUMN'
    if len(preferences.columns_left) == 0:
        col = preferences.columns_left.add()
    col = preferences.columns_left[0]


    # Add NSUITE elements
    nsuite_items = [
        'nsolve.hard_loop_cut',
        'nsolve.hard_edge_slide',
        'nsolve.offset_edges',
        'nsolve.bevel',
        'nsolve.mesh_cut'
    ]

    if len(col.rows) == 0:
        for item in nsuite_items:
            row = col.rows.add()
            row.type = 'NSUITE'
            row.nsuite_item = item

    # Top: COLUMN with 2 ROWs
    preferences.pie_gizmo_top = 'COLUMN'
    if len(preferences.columns_top) == 0:
        col = preferences.columns_top.add()
    col = preferences.columns_top[0]

    if len(col.rows) != 0: return

    # First row: Tool switching
    row = col.rows.add()
    row.type = 'ROW'

    # Add nSolve tool switch
    element = row.elements.add()
    element.type = 'NSUITE'
    element.nsuite_item = 'nsolve.set_nsolve_tool'

    # Add nSuite tool switch
    element = row.elements.add()
    element.type = 'NSUITE'
    element.nsuite_item = 'nsolve.set_nsuite_tool'

    # Add nFlow tool switch
    element = row.elements.add()
    element.type = 'NSUITE'
    element.nsuite_item = 'nsolve.set_nflow_tool'

    # Second row: Analyze
    row = col.rows.add()
    row.type = 'NSUITE'
    row.nsuite_item = 'nsolve.analyze'
