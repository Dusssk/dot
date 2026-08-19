import bpy

from mathutils import Vector

from ..types import button, imgbutton, imgtextbutton
from ....icons import gizmos
from ....utils import addon
from .nsuite import NsuGizmo
from ....utils.region import fixed_width

hide_gizmo_mdals =(
    'NSOLVE_OT_bevel',
    'NSOLVE_OT_collapse_verts',
    'NSOLVE_OT_mesh_cut',
    'NSOLVE_OT_dissolve_edges',
    'NSOLVE_OT_hard_edge_slide',
    'NSOLVE_OT_hard_loop_cut',
    'NSOLVE_OT_join_verts',
    'NSOLVE_OT_merge_verts',
    'NSOLVE_OT_slide_vert',
    'NSOLVE_OT_offset_edges',
    'NSOLVE_OT_project_circle',
    'NSOLVE_OT_project_grid',
    'NSOLVE_OT_project_line',
    'NSOLVE_OT_project_loop',
    'NSOLVE_OT_project_mesh',
    'NSOLVE_OT_project_rake',
    'MESH_OT_knife_tool',
    'TRANSFORM_OT_edge_slide',
    'VIEW3D_OT_select_box',
    'MESH_OT_loopcut_slide',
)


class NSOLVE_GGT_Nsolve(bpy.types.GizmoGroup):
    bl_idname = 'NSOLVE_GGT_Nsolve'
    bl_label = 'Nsolve Gizmo'
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_region_type = 'WINDOW'
    bl_options = {'SHOW_MODAL_ALL', 'SCALE'}

    # Add tracking for highlighted button and its neighbors
    highlighted_button_index = -1
    button_drawers = []

    keymap_name = '3D View NSO'

    @classmethod
    def poll(cls, context):
        active_tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode, create=False)
        nsolve_tool = True if active_tool and active_tool.idname == 'nsolve.nsolvetool' else False
        return context.space_data.show_gizmo_tool and context.edit_object and nsolve_tool

    @classmethod
    def setup_keymap(cls, keyconfig):
        km = keyconfig.keymaps.get(cls.keymap_name, None)
        if km: return km

        km = keyconfig.keymaps.new(name=cls.keymap_name, space_type='VIEW_3D')

        # Default LMB click
        kmi = km.keymap_items.new("gizmogroup.gizmo_tweak", 'LEFTMOUSE', 'PRESS')

        # G to move
        kmi = km.keymap_items.new("nsolve.transform_gizmo", 'G', 'PRESS')
        kmi.properties.mode = 'TRANSLATE'
        kmi.properties.gizmo = 'NSO'

        # S to scale
        kmi = km.keymap_items.new("nsolve.transform_gizmo", 'S', 'PRESS')
        kmi.properties.mode = 'SCALE'
        kmi.properties.gizmo = 'NSO'

        # F to flip
        kmi = km.keymap_items.new("nsolve.flip_gizmo", 'F', 'PRESS')
        kmi.properties.gizmo = 'NSO'

        # D to call NSO panel
        kmi = km.keymap_items.new("nsolve.call_panel", 'D', 'PRESS')
        kmi.properties.gizmo = 'NSO'

        return km

    def setup(self, context):
        self.gizmos.clear()

    def create(self, context):
        self.gizmos.clear()

        nsolve = addon.pref().tools.nsolve
        if nsolve.nso.hide:
            self.create_lmb_tab(context, nsolve)

        if nsolve.nsu.hide:
            NsuGizmo.create(self, context)

    def get_area(self, context):
        area_width = context.region.width
        left_fix, right_fix = fixed_width(context)
        usable_width = area_width - left_fix - right_fix

        return usable_width

    def is_modal_active(self, context):        # Check if modal_operators attribute exists (for older Blender versions)
        if not hasattr(context.window, 'modal_operators'):
            return False

        modals = context.window.modal_operators
        if not modals:
            return False

        for modal in modals:
            if modal.bl_idname in hide_gizmo_mdals:
                return True

        return False

    def create_lmb_tab(self, context, nsolve):
        # Calculate base size and spacing based on scale and DPI
        scale = nsolve.main_gizmo_scale
        base_size = Vector((scale, scale))

        # Get spacing from preferences instead of hardcoded value
        props = addon.pref().tools.nsolve
        spacing = scale * props.main_gizmo_spacing

        region = context.region
        area_width = region.width
        area_height = region.height

        left_fix, right_fix = fixed_width(context)
        usable_width = area_width - left_fix - right_fix

        # Calculate positions based on area size and DPI
        _location = Vector(props.main_gizmo_location)
        xpos = left_fix + (_location.x / 100.0) * usable_width
        ypos = (_location.y / 100.0) * area_height

        location = Vector((xpos, ypos))
        flip = props.main_gizmo_flip
        if (flip):
            size_bar = Vector((scale/4, scale))
        else:
            size_bar = Vector((scale, scale/4))

        # Reset button drawers list
        self.button_drawers = []

        # Create buttons with adjusted sizes and positions
        bar_location = location.copy()  # Create a separate location for the bar
        draw_button0 = imgbutton.Draw(self, bar_location, size_bar)
        draw_button0.operator("nsolve.transform_gizmo", properties={'gizmo': 'NSO'})
        self.button_drawers.append(draw_button0)

        # Add spacing before the nSolve button
        if flip:
            location.x += base_size.x
        else:
            location.y -= base_size.y

        nsolve_gizmo = addon.pref().tools.nsolve.main.operator
        pushed_select, pushed_join, pushed_merge, pushed_slide, pushed_line, pushed_collapse, pushed_dissolve, pushed_offset, pushed_knife, pushed_hide = False, False, False, False, False, False, False, False, False, False
        expand = addon.pref().tools.nsolve.expanded
        if expand:
            if nsolve_gizmo == 'SELECT':
                pushed_select = True
            elif nsolve_gizmo == 'JOIN':
                pushed_join = True
            elif nsolve_gizmo == 'MERGE':
                pushed_merge = True
            elif nsolve_gizmo == 'SLIDE':
                pushed_slide = True
            elif nsolve_gizmo == 'LINE':
                pushed_line = True
            elif nsolve_gizmo == 'COLLAPSE':
                pushed_collapse = True
            elif nsolve_gizmo == 'DISSOLVE':
                pushed_dissolve = True
            elif nsolve_gizmo == 'OFFSET':
                pushed_offset = True
            elif nsolve_gizmo == 'KNIFE':
                pushed_knife = True
            elif nsolve_gizmo == 'HIDE':
                pushed_hide = True


        gizmo_definitions = {
            'SELECT': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'SELECT', 'mode': 'SET', 'description': 'Select'},
                'icon': "select.png",
                'pushed': pushed_select
            },
            'JOIN': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'JOIN', 'mode': 'SET', 'description': 'Join'},
                'icon': "join.png",
                'pushed': pushed_join
            },
            'MERGE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'MERGE', 'mode': 'SET', 'description': 'Merge'},
                'icon': "merge.png",
                'pushed': pushed_merge
            },
            'SLIDE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'SLIDE', 'mode': 'SET', 'description': 'Slide'},
                'icon': "slide.png",
                'pushed': pushed_slide
            },
            'LINE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'LINE', 'mode': 'SET', 'description': 'Line'},
                'icon': "project_line.png",
                'pushed': pushed_line
            },
            'COLLAPSE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'COLLAPSE', 'mode': 'SET', 'description': 'Collapse'},
                'icon': "collapse_verts.png",
                'pushed': pushed_collapse
            },
            'DISSOLVE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'DISSOLVE', 'mode': 'SET', 'description': 'Dissolve'},
                'icon': "dissolve.png",
                'pushed': pushed_dissolve
            },
            'OFFSET': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'OFFSET', 'mode': 'SET', 'description': 'Offset'},
                'icon': "offset_edges.png",
                'pushed': pushed_offset
            },
            'KNIFE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'KNIFE', 'mode': 'SET', 'description': 'Knife'},
                'icon': "knife.png",
                'pushed': pushed_knife
            },
            'HIDE': {
                'operator': "nsolve.set_gizmo",
                'properties': {'gizmo': 'HIDE', 'mode': 'SET', 'description': 'Hide'},
                'icon': "hide.png",
                'pushed': pushed_hide
            }
        }

        # Draw main nSolve button
        draw_nsolve_button = imgbutton.Draw(self, location, base_size, "nsolve.png")
        draw_nsolve_button.operator("nsolve.expand_gizmo", properties={})
        self.button_drawers.append(draw_nsolve_button)

        if expand:
            # Draw buttons for each item in main_items
            main_items = addon.pref().tools.nsolve.main_gizmo_list_items
            for item in main_items:
                gizmo_info = gizmo_definitions[item.operator]
                location = location.copy()
                if flip:
                    location.x += base_size.x + spacing  # Use calculated spacing
                else:
                    location.y -= base_size.y + spacing  # Use calculated spacing
                draw_button = imgbutton.Draw(self, location, base_size, gizmo_info['icon'], gizmo_info['pushed'])
                draw_button.operator(gizmo_info['operator'], properties=gizmo_info['properties'])
                self.button_drawers.append(draw_button)

        else:
            # Draw only the active gizmo button
            gizmo_info = gizmo_definitions.get(nsolve_gizmo)
            if gizmo_info:
                location = location.copy()
                if flip:
                    location.x += base_size.x + spacing  # Use calculated spacing
                else:
                    location.y -= base_size.y + spacing  # Use calculated spacing
                draw_button = imgbutton.Draw(self, location, base_size, gizmo_info['icon'], gizmo_info['pushed'])
                draw_button.operator(gizmo_info['operator'], properties=gizmo_info['properties'])
                self.button_drawers.append(draw_button)

    # Add a method to update the highlighted button and apply magnification to neighbors
    def update_highlighted_button(self):
        # Find which button is currently highlighted
        highlighted_index = -1
        for i, drawer in enumerate(self.button_drawers):
            if hasattr(drawer.gizmo, 'is_highlight') and drawer.gizmo.is_highlight:
                highlighted_index = i
                break

        # If highlighted button changed, update neighbor magnification
        if highlighted_index != self.highlighted_button_index:
            self.highlighted_button_index = highlighted_index

            # Get the magnification value from preferences
            props = addon.pref().tools.nsolve
            base_magnification = props.main_gizmo_magnification

            # Calculate neighbor magnification based on the base magnification
            # Make sure neighbors always have lower magnification than the highlighted button
            # If base_magnification is 2.0:
            # - Direct neighbors get 40% of the effect (1.0 + (2.0-1.0)*0.4 = 1.4)
            # - Second-level neighbors get 20% of the effect (1.0 + (2.0-1.0)*0.2 = 1.2)
            direct_neighbor_mag = 1.0 + (base_magnification - 1.0) * 0.4
            second_neighbor_mag = 1.0 + (base_magnification - 1.0) * 0.2

            # Apply magnification to all buttons
            for i, drawer in enumerate(self.button_drawers):
                # Skip if this is a text button that shouldn't be magnified
                if hasattr(drawer.gizmo, 'is_text_button') and drawer.gizmo.is_text_button:
                    drawer.gizmo.main_magnification = 1.0
                    drawer.gizmo.neighbor_magnification = 1.0
                    continue

                # Always set draw_button0 (index 0) and draw_nsolve_button (index 1) to no magnification
                if i == 0 or i == 1:
                    drawer.gizmo.main_magnification = 1.0
                    drawer.gizmo.neighbor_magnification = 1.0
                    continue

                # For the highlighted button
                if i == highlighted_index:
                    # Set the main magnification value for the highlighted button
                    drawer.gizmo.main_magnification = base_magnification
                    # Reset neighbor magnification to ensure it doesn't interfere
                    drawer.gizmo.neighbor_magnification = 1.0
                    continue

                # Calculate distance from highlighted button
                distance = abs(i - highlighted_index) if highlighted_index >= 0 else 999

                # Apply magnification based on distance
                if distance == 1:  # Direct neighbors
                    # Apply a smaller magnification to direct neighbors
                    drawer.gizmo.neighbor_magnification = direct_neighbor_mag
                elif distance == 2:  # Second-level neighbors
                    # Apply an even smaller magnification to second-level neighbors
                    drawer.gizmo.neighbor_magnification = second_neighbor_mag
                else:
                    # Reset magnification for other buttons
                    drawer.gizmo.neighbor_magnification = 1.0

    def draw_prepare(self, context):
        usable_width = self.get_area(context)
        if self.width != usable_width:
            self.create(context)

        # Update highlighted button and neighbor magnification
        self.update_highlighted_button()

        # Hide all gizmos except first bar button if nsolve modal is active
        if self.is_modal_active(context):
            for i, gz in enumerate(self.gizmos):
                # Skip the first gizmo (bar button)
                if i > 1 :
                    gz.hide = True
        else:
            for gz in self.gizmos:
                gz.hide = False

    def refresh(self, context):
        usable_width = self.get_area(context)
        self.width = usable_width
        self.create(context)
