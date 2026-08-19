import bpy
import bmesh

from . import loops


class NSOLVE_OT_PencilQaud(bpy.types.Operator):
    bl_idname = "nsolve.pencilquad"
    bl_label = "Draw Quad"
    bl_description = "Create quad"
    bl_options = {'REGISTER', 'BLOCKING', 'UNDO', 'GRAB_CURSOR', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'MESH' and
                context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        context.window.cursor_set('SCROLL_XY')
        context.window_manager.modal_handler_add(self)
        bpy.ops.nsolve.fading_text('INVOKE_DEFAULT', text="nSuite")
        bpy.ops.nsolve.interface_header('INVOKE_DEFAULT', text=f"Fill Quads", position=(50, 2))
        return {'RUNNING_MODAL'}

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        # Use selected vertices to calculate grid points
        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        _loops = loops.find(bm)

        # Process only the first loop if it meets the criteria
        for loop in _loops:
            grid_points, _before_start, after_start = loops.process(loop)

            # Create vertices and update grid points with new vertex references
            create_vertices(bm, grid_points)
            # Pass updated grid points to geometry creation function
            create_faces(bm, grid_points, len(after_start) + 1)

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

        return {'FINISHED'}


def create_vertices(bm, grid_points):
    '''Create new vertices for interpolated points and update the grid points list.'''
    for i, (vert, co) in enumerate(grid_points):
        if vert is None:  # Indicates a need for a new vertex
            new_vert = bm.verts.new(co)
            bm.verts.index_update()  # Update immediately to maintain correct indexing
            grid_points[i] = (new_vert, co)  # Update grid point with new vertex


def create_faces(bm, grid_points, num_cols):
    '''Handles the creation of geometry based on the processed data.'''
    create_faces_from_grid_points(bm, grid_points, num_cols)
    bm.faces.index_update()  # Ensure the face list is updated after all operations


def create_faces_from_grid_points(bm, grid_points, num_cols):
    '''Create faces from the grid points list.'''
    num_rows = ((len(grid_points) - 1) // num_cols) + 1

    for row in range(num_rows - 1):
        for col in range(num_cols - 1):
            indices = [row * num_cols + col,
                       row * num_cols + col + 1,
                       (row + 1) * num_cols + col + 1,
                       (row + 1) * num_cols + col]

            if indices[-1] < len(grid_points):
                face_verts = []
                for idx in indices:
                    vert, _ = grid_points[idx]
                    face_verts.append(vert)

                try:
                    bm.faces.new(face_verts)
                except ValueError as e:
                    print(f"Error creating face: {e}")
                    continue
