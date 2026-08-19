import bpy
from .... import __package__ as base_package

class NSOLVE_MT_GizmoPie(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_gizmo_pie"
    bl_label = "nSolve"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Get preferences
        preferences = context.preferences.addons[base_package].preferences

        def draw_nsolve_item(layout, item):
            if item.nsolve_item != 'NONE':
                op = layout.operator("nsolve.set_gizmo", text=item.nsolve_item)
                op.gizmo = item.nsolve_item

        def draw_nsuite_item(layout, item):
            if item.nsuite_item != 'NONE':
                layout.operator(item.nsuite_item)

        def draw_operator_item(layout, item):
            if item.operator_string:
                layout.operator(item.operator_string)

        def draw_row_elements(layout, row_item):
            # Create a single row for all elements
            row = layout.row(align=True)
            
            for element in row_item.elements:
                if element.type == 'NSOLVE':
                    draw_nsolve_item(row, element)
                elif element.type == 'NSUITE':
                    draw_nsuite_item(row, element)
                elif element.type == 'OPERATOR':
                    draw_operator_item(row, element)

        def draw_column(layout, column):
            col = layout.column(align=True)
            
            # Draw items from the rows collection
            for row_item in column.rows:
                if row_item.type == 'NSOLVE':
                    draw_nsolve_item(col, row_item)
                elif row_item.type == 'NSUITE':
                    draw_nsuite_item(col, row_item)
                elif row_item.type == 'OPERATOR':
                    draw_operator_item(col, row_item)
                elif row_item.type == 'ROW':
                    draw_row_elements(col, row_item)

        # Draw pie menu elements
        directions = ['left', 'right', 'bottom', 'top', 'top_left', 'top_right', 'bottom_left', 'bottom_right']
        
        for direction in directions:
            prop_value = getattr(preferences, f"pie_gizmo_{direction}")
            
            if prop_value == 'NONE':
                pie.separator()
            elif prop_value == 'NSOLVE':
                # Get column for this direction
                columns = getattr(preferences, f"columns_{direction}")
                if len(columns) > 0:
                    active_index = getattr(preferences, f"active_column_index_{direction}")
                    column = columns[active_index]
                    if column.nsolve_item != 'NONE':
                        draw_nsolve_item(pie, column)
                    else:
                        pie.separator()
                else:
                    pie.separator()
            elif prop_value == 'NSUITE':
                # Get column for this direction
                columns = getattr(preferences, f"columns_{direction}")
                if len(columns) > 0:
                    active_index = getattr(preferences, f"active_column_index_{direction}")
                    column = columns[active_index]
                    if column.nsuite_item != 'NONE':
                        draw_nsuite_item(pie, column)
                    else:
                        pie.separator()
                else:
                    pie.separator()
            elif prop_value == 'OPERATOR':
                # Get column for this direction
                columns = getattr(preferences, f"columns_{direction}")
                if len(columns) > 0:
                    active_index = getattr(preferences, f"active_column_index_{direction}")
                    column = columns[active_index]
                    if column.operator_string:
                        draw_operator_item(pie, column)
                    else:
                        pie.separator()
                else:
                    pie.separator()
            elif prop_value == 'COLUMN':
                # Get column for this direction
                columns = getattr(preferences, f"columns_{direction}")
                if len(columns) > 0:
                    active_index = getattr(preferences, f"active_column_index_{direction}")
                    column = columns[active_index]
                    draw_column(pie, column)
                else:
                    pie.separator()

classes = (
    NSOLVE_MT_GizmoPie,
)
