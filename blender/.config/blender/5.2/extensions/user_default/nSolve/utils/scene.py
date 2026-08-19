import bpy
import bmesh

from mathutils import Vector
from .view3d import region_2d_to_origin_3d, region_2d_to_vector_3d


def prepare_ray_cast(context, position):
    '''Prepare for ray casting'''

    region = context.region
    rv3d = context.region_data

    # Prepare for ray casting
    x, y = position
    origin = Vector(region_2d_to_origin_3d(region, rv3d, (x, y)))
    direction = Vector(region_2d_to_vector_3d(region, rv3d, (x, y)))

    return origin, direction


def ray_cast(context, origin, direction, objects):
    # Start ray casting
    depsgraph = context.view_layer.depsgraph
    hit, location, normal, index, obj, matrix = context.scene.ray_cast(depsgraph, origin, direction)

    hidden = []

    # Hide objects that are not in the selection and not visible in the viewport
    while obj and obj not in objects and (not obj.visible_in_viewport_get(context.space_data) or obj.visible_get()):
        hidden.append(obj)
        obj.hide_viewport = True

        hit, location, normal, index, obj, matrix = context.scene.ray_cast(depsgraph, origin, direction)

    for h in hidden:
        h.hide_viewport = False

    ray = {'hit': hit, 'location': location, 'normal': normal, 'index': index, 'obj': obj, 'matrix': matrix}
    return ray


def ray_cast_selected(context, position):
    '''Cast a ray in the scene to detect the selected objects'''

    origin, direction = prepare_ray_cast(context, position)

    types = {'MESH'}
    selection = {obj for obj in context.selected_objects if obj.type in types}

    ray = ray_cast(context, origin, direction, selection)

    return ray


def ray_cast_visible(context, position, modes=('OBJECT')):
    '''Cast a ray in the scene'''

    origin, direction = prepare_ray_cast(context, position)

    # Start ray casting
    types = {'MESH'}
    objects = {obj for obj in context.visible_objects if obj.type in types and obj.mode in modes}
    ray = ray_cast(context, origin, direction, objects)
    return ray


def set_active_object(context, mouse_pos):
    '''Set the active object'''

    ray = ray_cast_selected(context, mouse_pos)
    if ray['hit']:
        if ray['obj'] in context.selected_objects:
            bpy.context.view_layer.objects.active = ray['obj']
