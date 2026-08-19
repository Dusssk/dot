import bpy, bmesh, numpy
from mathutils import Vector, Matrix, Euler

from . import addon, math, geometry_nodes, mesh


def valid_active_mesh(context):
    obj = context.active_object
    if obj == None: return False
    if obj.type != 'MESH': return False
    if not obj.select_get(): return False
    return True


def duplicate(obj, name='', link=False):
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()

    if name:
        duplicate.name = name
        duplicate.data.name = name

    addon.log(value=F'Duplicated {obj.name} as: {duplicate.name}', indent=2)

    if link:
        bpy.context.scene.collection.objects.link(duplicate)
        addon.log(value=F'Linked {duplicate.name} to the scene', indent=2)

    return duplicate


def center(obj, matrix=Matrix()):
    return 0.125 * math.vector_sum(bound_coordinates(obj, matrix=matrix))


def bound_coordinates(obj, matrix=Matrix()):
    return [matrix @ Vector(coord) for coord in obj.bound_box]


def mesh_duplicate(obj, depsgraph, apply_modifiers=True):
    mesh = obj.to_mesh()

    if apply_modifiers:
        obj = obj.evaluated_get(depsgraph)
        mesh = obj.to_mesh()

    return mesh


def apply_scale(obj):
    obj.data.transform(math.get_sca_matrix(obj.scale))
    obj.scale = Vector((1,1,1))


def apply_location(obj):
    obj.data.transform(math.get_loc_matrix(obj.location))
    obj.location = Vector((0,0,0))


def apply_rotation(obj):
    obj.data.transform(math.get_rot_matrix(obj.rotation_quaternion))
    obj.rotation_euler = Euler()


def apply_transforms(obj):
    obj.data.transform(obj.matrix_world)
    clear_transforms(obj)


def clear_transforms(obj):
    obj.matrix_world = Matrix()


def apply_transform_bpy_version():
    '''Apply the transform on the active object.'''

    # TODO: Make a low level version of this.

    if bpy.context.active_object.mode == "EDIT":
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if bpy.context.active_object.mode == "OBJECT":
        bpy.ops.object.mode_set(mode='EDIT')


def set_origin(obj, transform_world, preserve_scale=True):
    '''
    Set origin origin of an object. \n
    transform_world - world space 4x4 Matrix or 3d Vector\n
    preserve_scale - preserve or apply basis scale of the object\n

    setting world space scale is not supported; negative scale might not be preserved.
    '''
    parent_transform = obj.parent.matrix_world @ obj.matrix_parent_inverse if obj.parent else Matrix()
    if isinstance(transform_world, Matrix):

        local = parent_transform.inverted() @ transform_world
        loc, rot, _ = local.decompose()

        scale = Matrix.Diagonal((*obj.matrix_basis.decompose()[2], 1)) if preserve_scale else Matrix()
        local = Matrix.Translation(loc) @ rot.to_matrix().to_4x4() @ scale
        matrix_world = parent_transform @ local

    else:
        local = obj.matrix_basis.copy()
        local.translation = parent_transform.inverted() @ transform_world
        matrix_world = obj.matrix_world.copy()
        matrix_world.translation = transform_world

    delta_matrix = obj.matrix_basis.inverted() @ local
    delta_matrix_inv = delta_matrix.inverted()


    def update_children(obj, matrix):
        for child in obj.children:
            child.matrix_parent_inverse = matrix @ child.matrix_parent_inverse

    if obj.mode == 'OBJECT':
        if hasattr(obj.data, 'transform'):
            obj.data.transform(delta_matrix_inv)

        child_delta = obj.matrix_world.inverted() @ parent_transform @ local
        obj.matrix_basis = local
        obj.matrix_world = matrix_world
        update_children(obj, child_delta.inverted())

    elif obj.mode == 'EDIT' and obj.type == 'MESH':
        bm = bmesh.from_edit_mesh(obj.data)
        bmesh.ops.transform(bm, verts=bm.verts, matrix=delta_matrix_inv)
        bmesh.update_edit_mesh(obj.data)

        child_delta = obj.matrix_world.inverted() @ parent_transform @ local
        obj.matrix_basis = local
        obj.matrix_world = matrix_world
        update_children(obj, child_delta.inverted())


def hide_set(obj, value=False, viewport=True, render=True):
    if hasattr(obj, 'cycles_visibility'):
        obj.cycles_visibility.camera = not value
        obj.cycles_visibility.diffuse = not value
        obj.cycles_visibility.glossy = not value
        obj.cycles_visibility.transmission = not value
        obj.cycles_visibility.scatter = not value
        obj.cycles_visibility.shadow = not value

    if hasattr(obj, 'visible_camera'):
        obj.visible_camera = not value

    if hasattr(obj, 'visible_diffuse'):
        obj.visible_diffuse = not value

    if hasattr(obj, 'visible_glossy'):
        obj.visible_glossy = not value

    if hasattr(obj, 'visible_transmission'):
        obj.visible_transmission = not value

    if hasattr(obj, 'visible_volume_scatter'):
        obj.visible_volume_scatter = not value

    if hasattr(obj, 'visible_shadow'):
        obj.visible_shadow = not value

    if viewport:
        obj.hide_set(value)

    if render:
        obj.hide_render = value


def get_auto_smooth(obj)-> tuple[bool, float]:
    '''Wrapper for buituit Smooth By Angle modiifer as pre 4.1 use_auto_smooth and use_auto_sauto_smooth_anglemooth_angle mesh props\n
    if mod is present retruns mod.show_viewport, Angle. Otherwise False, 0.0\n
    Pre 4.1 returns  use_auto_smooth and auto_smooth_angle of object's mesh data. False and 0.0 for non-mesh objects\n
    obj - object to get data from
    '''

    if bpy.app.version[:2] < (4, 1):
        if obj.type != 'MESH': return (False, 0.0)

        return (obj.data.use_auto_smooth, obj.data.auto_smooth_angle)

    mod = None
    for mod in reversed(obj.modifiers):
        smooth = geometry_nodes.SmoothByAngle.new(mod)
        if smooth:
            return (True, smooth.angle)

    return (False, 0.0)


def set_auto_smooth(obj, enable:bool, angle=None, remove=True):
    '''Wrapper for buituit Smooth By Angle modiifer as pre 4.1 use_auto_smooth and use_auto_sauto_smooth_angle mesh props\n
    obj - object to operate on\n
    enable - bool to enable/disable auto smooth\n
    angle - angle in radians or None to keep current angle\n
    remove - bool remove or disable modifier(s) when enable is False\n
    '''
    if bpy.app.version[:2] < (4, 1):
        if obj.type != 'MESH': return

        obj.data.use_auto_smooth = enable
        if angle is not None: obj.data.auto_smooth_angle = angle

        return

    auto_smooth_mods = list(filter(geometry_nodes.SmoothByAngle.is_valid_modifier, obj.modifiers))

    if enable:
        if not auto_smooth_mods:
            mod = geometry_nodes.SmoothByAngle.from_object(obj)
            if angle is not None: mod.angle = angle
            mod.name = '!!' + mod.name
            mod.use_pin_to_last = True

        else:
            mod = geometry_nodes.SmoothByAngle.new(auto_smooth_mods[-1])
            mod.show_viewport = True
            if angle is not None: mod.angle = angle

        return

    else:
        for mod in auto_smooth_mods:
            if remove:
                obj.modifiers.remove(mod)

            else:
                mod.show_viewport = False


def smooth_set(obj, val):
    '''Set smoothing of object's data'''
    if not obj.data: return

    if obj.type == 'MESH':
        mesh.face_smooth_set(obj.data, val)
        return

    splines = getattr(obj.data, 'splines', [])
    for spline in splines:
        spline.use_smooth = True


def smooth_batch_set(objects, val):
    '''Set smoothing of object's data for all objects\n
    More efficient than calling smooth_set for on each object'''
    array = []

    for obj in objects:
        if not obj.data: continue

        if obj.type == 'MESH':
            sharp_face = mesh.sharp_face_get(obj.data)

            if sharp_face and val:
                obj.data.attributes.remove(sharp_face)
                continue

            ln = len(obj.data.polygons)
            if ln > len(array):
                if val:
                    array = numpy.ones(ln, dtype=bool)
                else:
                    array = numpy.zeros(ln, dtype=bool)

            obj.data.polygons.foreach_set('use_smooth', array)

            continue

        splines = getattr(obj.data, 'splines', [])
        for spline in splines:
            spline.use_smooth = True
