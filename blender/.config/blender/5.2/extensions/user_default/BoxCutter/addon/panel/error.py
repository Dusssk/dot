import bpy

from bpy.types import Panel
from bpy.props import StringProperty, BoolProperty

from .. toolbar import version
from ... import utility


class BC_PT_error_log(Panel):
    bl_label = 'Error Encountered'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'


    @classmethod
    def poll(cls, context):
        active = utility.tool.active()
        return active and active.idname == utility.tool.name


    def draw(self, context):
        layout = self.layout

        primary = True
        secondary = False

        # UI Width
        units_x = 30
        layout.ui_units_x = units_x

        column = layout.column()
        row = column.row()

        sub = row.row()
        sub.alignment = 'LEFT'
        sub.label(text=utility.name.upper())

        sub = row.row()
        sub.alert = True
        sub.alignment = 'CENTER'
        sub.label(text=F'Error Report')

        sub = row.row()
        sub.enabled = False
        sub.alignment = 'RIGHT'
        sub.label(text=version)

        column.separator()

        row = column.row()
        for error, elem in utility.error_elem.items():
            if primary:
                sub = row.row()
                sub.alignment = 'LEFT'
                sub.label(text='Failure:')
                primary = False

            elif not secondary:
                row = column.row()
                sub = row.row()
                sub.alignment = 'LEFT'
                sub.label(text='Resulting in:')
                secondary = True

            row = column.row()
            for i, e in enumerate(elem['header'].split(':')):
                sub = row.row()
                sub.alignment = 'LEFT' if i == 0 else 'CENTER'
                sub.alert = i == 0
                sub.label(text=F'  {e}{":" if i == 0 else ""}')

            # UI Width
            # _units_x = len(elem['header'] + str(elem['count'])) / 2
            # if _units_x > units_x:
            #     units_x = _units_x

            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.alert = True
            sub.label(text=F'    Count: {elem["count"]}')

            for line in elem['body'].splitlines():
                column.row().label(text=line)

        column.separator()

        row = column.row()
        row.enabled = False
        row.label(text=F'    Blender:  {bpy.app.version_string}')
