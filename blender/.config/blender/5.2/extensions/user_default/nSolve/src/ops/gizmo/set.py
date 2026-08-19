import bpy
from ....utils import addon

from ... import analytics

gizmo_props = [
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


class NSOLVE_OT_SetGizmo(bpy.types.Operator):
    bl_idname = "nsolve.set_gizmo"
    bl_label = "Set Gizmo"
    bl_description = "Set Gizmo"
    bl_options = {'REGISTER', 'BLOCKING', 'GRAB_CURSOR', 'INTERNAL'}

    mode: bpy.props.EnumProperty(
        name="Select Mode",
        description="Select Mode",
        items=[
            ('SET', 'Set', 'Set'),
            ('UP', 'Up', 'Up'),
            ('DOWN', 'Down', 'Down'),
            ('ADD', 'Add', 'Add')
        ],
        default='SET'
    )
    only_list: bpy.props.BoolProperty(name="Only Chosen", description="Only Chosen", default=False)
    gizmo: bpy.props.EnumProperty(name="Gizmo", description="Gizmo", items=gizmo_props, default='JOIN')
    description: bpy.props.StringProperty(name="Description", description="Description", default="")

    button: str

    @classmethod
    def poll(cls, context):
        if context.area.type == 'VIEW_3D':
            return context.mode == 'EDIT_MESH'
        return False

    @classmethod
    def description(cls, context, properties):
        return properties.description

    def invoke(self, context, event):
        if event.shift:
            self.button = 'SHIFT'
        elif event.ctrl:
            self.button = 'CTRL'
        else:
            self.button = 'LMB'

        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSolve")
        return self.execute(context)

    def execute(self, context):

        prop = addon.pref().tools.nsolve

        if self.mode == 'SET':
            if self.button == 'SHIFT':
                prop.aux.operator = self.gizmo
            elif self.button == 'CTRL':
                prop.sub.operator = self.gizmo
            else:
                prop.main.operator = self.gizmo

        main_operators = (
            'SELECT',
            'JOIN',
            'MERGE',
            'SLIDE',
            'LINE',
            'COLLAPSE',
            'DISSOLVE',
            'OFFSET',
            'KNIFE',
            'HIDE'
        )

        if self.mode in {'UP', 'DOWN'}:
            if self.only_list:
                operators_list = prop.main_gizmo_list_items
                index = prop.main_gizmo_list_index

                if self.mode == 'UP':
                    index = (index + 1) % len(operators_list)
                elif self.mode == 'DOWN':
                    index = (index - 1) % len(operators_list)

                prop.main_gizmo_list_index = index
                prop.main.operator = operators_list[index].operator
            else:
                index = main_operators.index(prop.main.operator)
                if self.mode == 'UP':
                    index = (index + 1) % len(main_operators)
                elif self.mode == 'DOWN':
                    index = (index - 1) % len(main_operators)
                prop.main.operator = main_operators[index]

        analytics.stats(f"nSolve: Set {self.gizmo}")
        return {'FINISHED'}
