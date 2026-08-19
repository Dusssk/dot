import bpy

from mathutils import Matrix, Vector

from ....icons import gizmos
from ....utils import addon


class Draw:
    def __init__(self, gm, location, size, icon=None, pushed=False):

        self.icon = icon
        self.location = location
        self.size = size

        if icon:
            for i in self.icon:
                self.create_icons(gm, location, size, i)

        # Create gizmo
        self.gizmo = self.create(gm, location, size, pushed)

    def create(self, gm, location, size, pushed):
        # Define gizmos for X arrow (Red)

        translation_matrix = Matrix.Translation((location.x, location.y, 0))
        scale_matrix = Matrix.Scale(size.x, 4, Vector((1, 0, 0))) @ Matrix.Scale(size.y, 4, Vector((0, 1, 0)))

        geo = gizmos.background.icon[0][1]

        col = addon.pref().tools.nsolve.gizmo_col.inner
        col_selected = addon.pref().tools.nsolve.gizmo_col.selected

        gz = gm.gizmos.new(NSOLVE_GT_Button.bl_idname)
        gz.build(geo)
        if pushed:
            gz.color = col_selected[:-1]
            gz.alpha = col_selected[-1]
        else:
            gz.color = col[:-1]
            gz.alpha = col[-1]
        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 0.3
        gz.use_event_handle_all = True
        gz.use_draw_modal = True
        gz.scale_basis = 1
        gz.location = location
        gz.size = size
        gz.matrix_basis = translation_matrix @ scale_matrix

        return gz

    def create_icons(self, gm, location, size, icon):

        translation_matrix = Matrix.Translation((location.x, location.y, 0))
        scale_matrix = Matrix.Scale(size.x, 4, Vector((1, 0, 0))) @ Matrix.Scale(size.y, 4, Vector((0, 1, 0)))

        geo = icon[1]
        col = icon[0]

        gz = gm.gizmos.new(NSOLVE_GT_Button.bl_idname)
        gz.build(geo)
        gz.color = col[:-1]
        gz.alpha = col[-1]
        gz.hide_select = True
        gz.use_event_handle_all = True
        gz.use_draw_modal = True
        gz.scale_basis = 1
        gz.location = location
        gz.size = size
        gz.matrix_basis = translation_matrix @ scale_matrix

        return gz

    def is_modal(self):
        return self.gizmo.is_modal

    def hide(self, set=False):
        if set:
            self.gizmo.hide = True
        else:
            self.gizmo.hide = False

    def operator(self, operator, properties=None):
        try:
            op_props = self.gizmo.target_set_operator(operator)
        except Exception as e:
            print(f"Error setting operator '{operator}': {e}")
            return
        if properties:
            for prop, value in properties.items():
                try:
                    setattr(op_props, prop, value)
                except Exception as e:
                    print(f"Error setting property '{prop}' to '{value}' for operator '{operator}': {e}")

    def update(self, matrix_basis):

        self.gizmo.matrix_basis = matrix_basis


class NSOLVE_GT_Button(bpy.types.Gizmo):
    bl_idname = "NSOLVE_GT_Button"

    custom_shape = None

    def draw(self, context):
        self.draw_custom_shape(self.custom_shape)

    def test_select(self, context, location):

        loc = self.location
        size = self.size * 2

        # check if location is inside the button size of 24 an dat loc of xpos, ypos
        if loc.x - size.x < location[0] < loc.x + size.x and loc.y - size.y < location[1] < loc.y + size.y:
            return 0

        return -1  # Hit detected, return 0 or any positive int to indicate a specific part of the gizmo was hit

    def build(self, geo):
        tris = geo
        self.custom_shape = self.new_custom_shape('TRIS', tris)

class NSOLVE_OT_ButtonRunScript(bpy.types.Operator):
    bl_label = 'nsolve run script'
    bl_idname = "nsolve.button_run_script"
    bl_options = {'REGISTER', 'INTERNAL'}

    script: bpy.props.StringProperty()
    script_description: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, props):
        return props.script_description


    def execute(self, context):
        import bpy, math, mathutils
        try:
            exec(self.script)

        except Exception as e:
            self.report({'ERROR'}, str(e))

        return {'FINISHED'}