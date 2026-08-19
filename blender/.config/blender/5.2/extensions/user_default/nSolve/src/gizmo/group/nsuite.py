import bpy
from mathutils import Vector
from ..types import imgbutton
from ....icons import gizmos
from ....utils import addon
from ....utils.region import fixed_width


class NsuGizmo:
    @staticmethod
    def create(gizmo_group, context):
        props = addon.pref().tools.nsuite

        # Define gizmo properties and icons
        gizmo_definitions = {
            'hard_loop_cut': {
                'operator': "nsolve.hard_loop_cut",
                'properties': {'release_confirm': True},
                'icon': "hard_loop_cut.png",
                'pushed': False,
            },
            'loop_cut': {
                'operator': "mesh.loopcut_slide",
                'properties': {},
                'icon': "loop_cut.png",
                'pushed': False,
            },
            'hard_edge_slide': {
                'operator': "nsolve.hard_edge_slide",
                'properties': {},
                'icon': "hard_edge_slide.png",
                'pushed': False,
            },
            'offset_edges': {
                'operator': "nsolve.offset_edges",
                'properties': {},
                'icon': "offset_edges.png",
                'pushed': False,
            },
            'mesh_cut': {
                'operator': "nsolve.mesh_cut",
                'properties': {},
                'icon': "cut.png",
                'pushed': False,
            },
            'bevel': {
                'operator': "nsolve.bevel",
                'properties': {},
                'icon': "bevel.png",
                'pushed': False,
            },
            'project_line': {
                'operator': "nsolve.project_line",
                'properties': {'mouse_init': False},
                'icon': "project_line.png",
                'pushed': False,
            },
            'project_loop': {
                'operator': "nsolve.project_loop",
                'properties': {'mode': 'OFFSET'},
                'icon': "project_loop.png",
                'pushed': False,
            },
            'project_circle': {
                'operator': "nsolve.project_circle",
                'properties': {},
                'icon': "project_circle.png",
                'pushed': False,
            },
            'project_grid': {
                'operator': "nsolve.project_grid",
                'properties': {},
                'icon': "project_grid.png",
                'pushed': False,
            },
            'analyze': {
                'operator': "nsolve.analyze",
                'properties': {},
                'icon': "analyze.png",
                'pushed': context.scene.nsolve.ops.mesh.analyze.running if hasattr(context.scene.nsolve, 'ops') else False,
            },
            'select_smartloop': {
                'operator': "nsolve.select_multi_smartloop",
                'properties': {},
                'icon': "select_smartloop.png",
                'pushed': False,
            },
            'select_rounded_area': {
                'operator': "nsolve.select_rounded_area",
                'properties': {},
                'icon': "select_rounded_area.png",
                'pushed': False,
            },
            'select_similar_strip': {
                'operator': "nsolve.select_similar_strip",
                'properties': {},
                'icon': "select_similar_strip.png",
                'pushed': False,
            },
            'select_planarloop': {
                'operator': "nsolve.select_multi_planarloop",
                'properties': {},
                'icon': "select_planarloop.png",
                'pushed': False,
            }
        }

        region = context.region
        area_width = region.width
        area_height = region.height
        left_fix, right_fix = fixed_width(context)
        usable_width = area_width - left_fix - right_fix

        # Get edit mode state
        is_edit_mode = props.nsu_edit_mode

        edit_location = Vector((50, 5))
        edit_xpos = left_fix + (edit_location.x / 100.0) * usable_width
        edit_ypos = (edit_location.y / 100.0) * area_height
        edit_buttons_location =Vector((edit_xpos, edit_ypos))
        edit_buttons_size = Vector((48, 48))

        if is_edit_mode:
            # Toggle edit mode button
            edit_button = imgbutton.Draw(gizmo_group, edit_buttons_location, edit_buttons_size, 'close.png')
            edit_button.operator("nsolve.toggle_edit_mode")

            # Add gizmo button
            # edit_buttons_location += Vector((edit_buttons_size.x + 10, 0))
            # add_button = imgbutton.Draw(gizmo_group, edit_buttons_location, edit_buttons_size, 'add.png')
            # add_button.operator("nsolve.add_gizmo")

        # Draw each gizmo
        for i, gizmo in enumerate(props.nsu_gizmos_items):
            scale = gizmo.scale
            button_size = Vector((scale/1.2, scale/1.2))
            spacing = scale/8

            # Calculate positions based on area size and DPI
            _location = Vector(gizmo.location)
            xpos = left_fix + (_location.x / 100.0) * usable_width
            ypos = (_location.y / 100.0) * area_height
            location = Vector((xpos, ypos))
            flip = gizmo.flip

            # Grid dimensions
            GRID_ROWS = 15
            GRID_COLS = 5

            # Calculate total grid size
            total_grid_width = GRID_COLS * (button_size.x + spacing) - spacing
            total_grid_height = GRID_ROWS * (button_size.y + spacing) - spacing

            # 1. First create and position the bar button at cursor
            bar_width = scale * 0.8  # Short bar
            bar_height = scale/6   # Thin bar height

            if flip:
                bar_size = Vector((bar_height, bar_width))
                # Bar exactly at cursor, vertically centered
                bar_location = location + Vector((0, -bar_width/2))
                remove_loc = bar_location - Vector((spacing * 8, 0))
            else:
                bar_size = Vector((bar_width, bar_height))
                # Bar centered on cursor
                bar_location = location + Vector((-bar_width/2, 0))
                remove_loc = bar_location + Vector((0, spacing * 8))

            if is_edit_mode:
                # Add remove button before bar
                r_loc = remove_loc
                # remove_button = imgbutton.Draw(gizmo_group, remove_loc, button_size, 'remove.png')
                # remove_button.operator("nsolve.remove_gizmo", properties={'gizmo_index': i})

            draw_button0 = imgbutton.Draw(gizmo_group, bar_location, bar_size)
            draw_button0.operator("nsolve.transform_nsu_gizmo", properties={'gizmo_index': i})

            # 2. Then position grid relative to bar
            if flip:
                # Start grid to the right of bar, centered vertically
                grid_start = location + Vector((bar_height + spacing*2, -total_grid_height/6)) + Vector((scale/2, 0))
            else:
                # Start grid below bar, centered horizontally
                grid_start = location + Vector((-total_grid_width/2, -bar_height - spacing*2)) + Vector((0, -scale/2))

            # Create grid of buttons
            for row in range(GRID_ROWS):
                for col in range(GRID_COLS):
                    idx = row * GRID_COLS + col
                    if idx >= 75:  # Maximum 75 buttons
                        break

                    # Calculate position based on flip
                    if flip:
                        button_pos = grid_start + Vector((row * (button_size.x + spacing), col * (button_size.y + spacing)))
                    else:
                        button_pos = grid_start + Vector((col * (button_size.x + spacing), -row * (button_size.y + spacing)))

                    # Get operator data if it exists
                    op_data = None
                    if idx < len(gizmo.list_items):
                        op_data = gizmo.list_items[idx]

                    # Skip empty slots and none operators unless in edit mode
                    if not is_edit_mode and (not op_data or not op_data.operator or op_data.operator == 'none'):
                        continue

                    # Determine icon for the button
                    icon = None
                    pushed = False
                    if is_edit_mode:
                        # In edit mode
                        if not op_data or not op_data.operator or op_data.operator == 'none':
                            icon = "empty_button.png"
                        elif op_data.operator == 'custom' and op_data.custom_operator:
                            # For custom operators, use custom icon or fallback to custom.png
                            icon = op_data.custom_icon if op_data.custom_icon else "custom.png"
                        elif op_data.operator == 'nsuite':
                            # For nsuite operators, check gizmo_definitions first
                            gizmo_info = gizmo_definitions.get(op_data.nsuite_operator)
                            if gizmo_info and gizmo_info.get('icon'):
                                icon = gizmo_info['icon']
                            else:
                                # Fallback to operator name if not in definitions
                                icon = f"{op_data.nsuite_operator}.png"
                        elif op_data.operator == 'tool':
                            # For tool operators, use custom icon or fallback
                            icon = op_data.custom_icon if op_data.custom_icon else "tool.png"

                        elif op_data.operator == 'script':
                            # For scripts, use custom icon or fallback
                            icon = op_data.custom_icon if op_data.custom_icon else "tool.png"
                        else:
                            # For built-in operators
                            gizmo_info = gizmo_definitions.get(op_data.operator)
                            if gizmo_info and gizmo_info.get('icon'):
                                icon = gizmo_info['icon']
                            else:
                                # Use custom.png as fallback if icon doesn't exist
                                icon = "custom.png"
                    else:
                        # Normal operation mode
                        if op_data.operator == 'custom':
                            # For custom operators, use custom icon or fallback to custom.png
                            icon = op_data.custom_icon if op_data.custom_icon else "custom.png"
                            # Set pushed state to true if no operator is set
                            pushed = not bool(op_data.custom_operator)
                        elif op_data.operator == 'nsuite':
                            # For nsuite operators
                            # Check if there's a special mapping in gizmo_definitions
                            gizmo_info = gizmo_definitions.get(op_data.nsuite_operator)
                            if gizmo_info and gizmo_info.get('operator'):
                                # Use the mapped operator from definitions
                                icon = gizmo_info['icon']
                                pushed = gizmo_info['pushed']
                            else:
                                # Default to nsolve namespace
                                icon = f"{op_data.nsuite_operator}.png"
                                pushed = False
                        elif op_data.operator == 'tool':
                            # For tool operators, use custom icon or fallback
                            icon = op_data.custom_icon if op_data.custom_icon else "tool.png"
                            # Set pushed state to true if no tool is set
                            pushed = not bool(op_data.tool_operator)

                        elif op_data.operator == 'script':
                            # For scripts, use custom icon or fallback
                            icon = op_data.custom_icon if op_data.custom_icon else "tool.png"
                            # Set pushed state to true if no tool is set
                            pushed = not bool(op_data.script)
                        else:
                            # For built-in operators
                            gizmo_info = gizmo_definitions.get(op_data.operator)
                            if gizmo_info and gizmo_info.get('icon'):
                                icon = gizmo_info['icon']
                                pushed = gizmo_info['pushed']
                            else:
                                # Use custom.png as fallback if icon doesn't exist
                                icon = "custom.png"
                                pushed = False

                    # Create button with icon
                    draw_button = imgbutton.Draw(gizmo_group, button_pos, button_size, icon, pushed)

                    # Set red color if operator is not properly set
                    if op_data:
                        if (op_data.operator == 'custom' and not op_data.custom_operator) or \
                           (op_data.operator == 'tool' and not op_data.tool_operator) or \
                            (op_data.operator == 'script' and not op_data.script):
                            draw_button.gizmo.color = (1.0, 0.2, 0.2)  # Red color
                            draw_button.gizmo.alpha = 1.0

                    if is_edit_mode:
                        # In edit mode, clicking configures the button
                        draw_button.operator("nsolve.configure_gizmo_button", properties={'button_index': idx, 'gizmo_index': i})
                    else:
                        # Only set operator if we have valid operator data
                        if op_data and op_data.operator and op_data.operator != 'none':
                            if op_data.operator == 'tool' and op_data.tool_operator:
                                # For tool operators, execute the node group directly
                                node_group = bpy.data.node_groups.get(op_data.tool_operator)
                                if node_group:
                                    draw_button.operator("geometry.execute_node_group", properties={
                                        'name': op_data.tool_operator
                                    })

                            elif op_data.operator == 'script' and op_data.script:
                                # For scripts, execute the node group directly
                                draw_button.operator("nsolve.button_run_script", properties={
                                        'script': op_data.script,
                                        'script_description': op_data.script_description,
                                    })
                            elif op_data.operator == 'custom' and op_data.custom_operator:
                                # For custom operator with properties
                                properties = {}
                                for prop in op_data.operator_properties:
                                    if prop.type == 'INT':
                                        properties[prop.name] = prop.value_int
                                    elif prop.type == 'FLOAT':
                                        properties[prop.name] = prop.value_float
                                    elif prop.type == 'STRING':
                                        properties[prop.name] = prop.value_string
                                    elif prop.type == 'BOOL':
                                        properties[prop.name] = prop.value_bool
                                    elif prop.type == 'ENUM':
                                        properties[prop.name] = prop.value_enum
                                draw_button.operator(op_data.custom_operator, properties=properties)
                            elif op_data.operator == 'nsuite':
                                # For nsuite operators
                                gizmo_info = gizmo_definitions.get(op_data.nsuite_operator)
                                if gizmo_info and gizmo_info.get('operator'):
                                    draw_button.operator(gizmo_info['operator'], properties=gizmo_info['properties'])
                                else:
                                    draw_button.operator(f"nsolve.{op_data.nsuite_operator}")
                            else:
                                # For built-in operators
                                gizmo_info = gizmo_definitions.get(op_data.operator)
                                if gizmo_info and gizmo_info.get('operator'):
                                    draw_button.operator(gizmo_info['operator'], properties=gizmo_info['properties'])


class NSOLVE_GGT_Nsuite(bpy.types.GizmoGroup):
    bl_idname = 'NSOLVE_GGT_Nsuite'
    bl_label = 'Nsuite Gizmo'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_region_type = 'WINDOW'
    bl_options = {'SHOW_MODAL_ALL', 'SCALE'}

    keymap_name = '3D View NSU'

    @classmethod
    def setup_keymap(cls, keyconfig):
        km = keyconfig.keymaps.get(cls.keymap_name, None)

        if km: return km

        km = keyconfig.keymaps.new(name=cls.keymap_name, space_type='VIEW_3D')

        # Default LMB click
        kmi = km.keymap_items.new("gizmogroup.gizmo_tweak", 'LEFTMOUSE', 'PRESS')

        # D to call NSU panel
        kmi = km.keymap_items.new("nsolve.call_panel", 'D', 'PRESS')
        kmi.properties.gizmo = 'NSU'

        return km

    @classmethod
    def poll(cls, context):
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        nsolve_tool = True if active_tool and active_tool.idname == 'nsolve.nsuitetool' else False
        return context.space_data.show_gizmo_tool and context.edit_object and nsolve_tool

    def setup(self, context):
        self.gizmos.clear()

    def create(self, context):
        self.gizmos.clear()

        nsuite = addon.pref().tools.nsuite
        if nsuite.nsu.hide:
            NsuGizmo.create(self, context)

    def get_area(self, context):
        area_width = context.region.width
        left_fix, right_fix = fixed_width(context)
        usable_width = area_width - left_fix - right_fix

        return usable_width

    def draw_prepare(self, context):
        usable_width = self.get_area(context)
        if self.width != usable_width:
            self.create(context)

    def refresh(self, context):
        usable_width = self.get_area(context)
        self.width = usable_width
        self.create(context)
