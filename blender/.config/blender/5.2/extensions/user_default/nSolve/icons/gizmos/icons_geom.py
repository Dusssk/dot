import bpy
import os


def get_material_color(obj):
    # Check if the object has an active material
    if not obj.active_material:
        raise ValueError(f"Object {obj.name} does not have an active material.")

    # Extract the diffuse color from the active material
    color = obj.active_material.diffuse_color

    # Check if the color is properly defined
    if color is None:
        raise ValueError(f"Material on object {obj.name} does not have a diffuse color defined.")

    return tuple(color)


def generate_2d_tris_from_evaluated_object(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    mesh.calc_loop_triangles()
    tris_positions_flat = []

    for tri in mesh.loop_triangles:
        for loop_index in tri.loops:
            vert = mesh.vertices[mesh.loops[loop_index].vertex_index]
            x, y = vert.co[:2]
            tris_positions_flat.append((x, y))

    eval_obj.to_mesh_clear()
    return tris_positions_flat


def process_objects():
    # Path where the Blender file is saved
    file_path = bpy.data.filepath
    file_dir = os.path.dirname(file_path)

    # Iterate through objects in the main collection that have no parents
    for obj in bpy.data.collections['Collection'].all_objects:
        if obj.parent is None:
            child_data = []
            for child in obj.children:
                try:
                    color = get_material_color(child)
                    tris = generate_2d_tris_from_evaluated_object(child)
                    child_data.append((color, tris))
                except ValueError as e:
                    print(e)
                    return  # Stop processing if an error occurs

            # Generate Python file content
            py_content = f"icon = {child_data}\n"

            # Save to a Python file named after the parent object
            file_name = f"{obj.name}.py"
            with open(os.path.join(file_dir, file_name), 'w') as f:
                f.write(py_content)


process_objects()
