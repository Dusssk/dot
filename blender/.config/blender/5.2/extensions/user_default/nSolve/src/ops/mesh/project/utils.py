import bpy
import bmesh
from mathutils import Matrix


def create_polyline_object(polyline_points):
    '''Create a polyline object from the vertices'''

    # Create a new mesh and object
    mesh_data = bpy.data.meshes.new("Nsolve_Polyline_mesh")
    obj = bpy.data.objects.new("Nsolve_Polyline_obj", mesh_data)
    bpy.context.collection.objects.link(obj)

    # Create a new BMesh, add verts, and make edges
    bm = bmesh.new()
    bm_verts = [bm.verts.new(p) for p in polyline_points]
    for i in range(len(bm_verts) - 1):
        bm.edges.new((bm_verts[i], bm_verts[i + 1]))

    # Write the bmesh back to the mesh data
    bm.to_mesh(mesh_data)
    bm.free()

    return obj


def project_polylines(polylines, cut_through=False):
    '''Cut the polyline into a mesh'''

    for polyline in polylines:

        polyline_obj = create_polyline_object(polyline)
        polyline_obj.select_set(True)

        bpy.ops.mesh.knife_project(cut_through=cut_through)

        polyline_data = polyline_obj.data
        bpy.data.objects.remove(polyline_obj, do_unlink=True)
        bpy.data.meshes.remove(polyline_data)


def create_polyline_object_index(polyline, indices):
    '''Create a polyline object from the vertices and edge indices'''

    mesh_data = bpy.data.meshes.new("Nsolve_Polyline_mesh")
    obj = bpy.data.objects.new("Nsolve_Polyline_obj", mesh_data)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()
    bm_verts = [bm.verts.new(p) for p in polyline]
    for i, j in indices:
        bm.edges.new((bm_verts[i], bm_verts[j]))

    bm.to_mesh(mesh_data)
    bm.free()

    return obj

def project_polyline_indexed(polyline, indices, cut_through=False, matrix=Matrix()):
    '''Project poliline into mesh\n
    polyline: list of 3d float vectors
    indices: list of 2d int vectors for defining edges
    matrix: 4x4 Matrix for object transfrom before projection
    '''

    polyline_obj = create_polyline_object_index(polyline, indices)
    polyline_obj.matrix_world = matrix
    polyline_obj.select_set(True)

    bpy.ops.mesh.knife_project(cut_through=cut_through)

    polyline_data = polyline_obj.data
    bpy.data.objects.remove(polyline_obj, do_unlink=True)
    bpy.data.meshes.remove(polyline_data)

