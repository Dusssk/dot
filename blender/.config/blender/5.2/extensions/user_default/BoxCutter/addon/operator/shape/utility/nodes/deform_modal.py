import bpy
import bmesh
import sys

from mathutils import Vector, Matrix, geometry
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d

from ......utility import addon, math, modifier, view3d, screen, mesh
from math import radians, copysign
from . import Generate, Deform

def dimensions(op):
    deform: Deform = op.modifier_stack.deform
    dimensions = Vector(deform.min) - Vector(deform.max)
    dimensions.x = abs(dimensions.x)
    dimensions.y = abs(dimensions.y)
    dimensions.z = abs(dimensions.z)

    return dimensions

def thickness_clamp(op, context):
    preference = addon.preference()
    if not preference.shape.clamp_min: return 0

    bc = context.scene.bc

    factor = 0.005
    # thickness = min(bc.lattice.dimensions[:-1]) * factor
    thickness = min(dimensions(op)[:-1]) * factor

    offset = preference.shape.offset

    clamp = thickness if thickness < offset else offset - 0.001
    return abs(clamp)


def draw(op, context, event):
    preference = addon.preference()
    bc = context.scene.bc

    snap = preference.snap.enable and (preference.snap.incremental or (preference.snap.grid and bc.snap.display))
    snap_lock = snap and preference.snap.increment_lock

    deform: Deform = op.modifier_stack.deform
    deform_min_obj = Vector(deform.min)
    deform_max_obj = Vector(deform.max)
    generate: Generate = op.modifier_stack.generate
    auto_flip = preference.shape.auto_flip_xy and (op.shape_type == 'CUSTOM' or op.shape_type == 'BOX')

    # not_snap_grid = preference.snap.enable and not preference.snap.grid and not op.modified
    # snap_operator_handler = (bc.snap.operator.handler if hasattr(bc.snap.operator, 'handler') else bc.snap.operator.snap) if bc.snap.operator else None
    # snap_operator_point_exists = snap_operator_handler and (snap_operator_handler.points.active if hasattr(snap_operator_handler, 'points') else snap_operator_handler.point)

    # if snap_operator_point_exists and not_snap_grid:
    #     if preference.snap.edges and bc.snap.operator.snap.point.type == 'VERT':
    #         op.snap_lock_type = 'VERT'

    #     if preference.snap.edges and bc.snap.operator.snap.point.type == 'EDGE' and op.custom_orient:
    #         op.snap_lock_type = 'EDGE'

    #     if preference.snap.edges and bc.snap.operator.snap.point.type == 'FACE':
    #         op.snap_lock_type = 'FACE'

    if event.alt or event.shift:
        op.snap_lock_type = ''

    vert_lock = op.snap_lock_type == 'VERT'
    edge_lock = op.snap_lock_type == 'EDGE'
    face_lock = op.snap_lock_type == 'FACE'

    if op.init_mouse == op.mouse['location']:
        return

    if op.origin == 'CENTER' or event.alt:
        origin_offset = op.last['deform_center']

    else:
        origin_offset = op.last['deform_corner']

    mask_shift = False
    if bc.snap.operator:
        if hasattr(bc.snap.operator, 'grid_handler'):
            grid_handler = bc.snap.operator.grid_handler

            if grid_handler.snap_type == 'DOTS':
                if grid_handler.dot_divisions:
                    vert_lock = edge_lock = face_lock = False

                if preference.snap.dot_dot_snap:
                    grid_handler.update(context, event)

                    if grid_handler.nearest_dot:
                        location = bc.shape.matrix_world.inverted() @ grid_handler.snap_world
                        op.view3d['location'].x = location.x
                        op.view3d['location'].y = location.y

                        snap = snap_lock = False
            else:
                grid_handler.mode = 'NONE'

                grid_lock = preference.snap.increment_lock and preference.snap.grid
                grid_handler.draw = (grid_lock or grid_handler.frozen) != event.ctrl
                grid_handler.update(context, event)

                location = bc.shape.matrix_world.inverted() @ grid_handler.snap_world
                op.view3d['location'].x = location.x
                op.view3d['location'].y = location.y

                snap = snap_lock = False

        elif not bc.snap.operator.handler.exit and not preference.snap.static_grid and preference.snap.grid and bc.snap.operator.handler.grid.display and bc.snap.display:
            location = bc.shape.matrix_world.inverted() @ Vector(bc.snap.location)
            op.view3d['location'].x = location.x
            op.view3d['location'].y = location.y

            snap = snap_lock = False

            if bc.snap.operator.handler.micro:
                mask_shift = True

    location_x = op.view3d['location'].x - origin_offset.x
    location_y = op.view3d['location'].y - origin_offset.y
    deform_min = deform_min_obj - origin_offset
    deform_max = deform_max_obj - origin_offset

    if preference.behavior.draw_line and not op.extruded and not op.ngon_fit and not event.shift and not event.ctrl and not event.alt:
        location_x = op.last['line']

    if snap and event.ctrl or snap_lock:
        increment_amount = round(preference.snap.increment, 8)
        split = str(increment_amount).split('.')[1]

        increment_length = len(split) if int(split) != 0 else 0

        if event.shift:
            location_x = round(round(location_x * 10 / increment_amount) * increment_amount, increment_length)
            location_x *= 0.1
            limit = increment_amount * 0.1

            if op.view3d['location'].x < 0:
                limit = -limit

            if location_x == 0:
                location_x += limit

            location_y = round(round(location_y * 10 / increment_amount) * increment_amount, increment_length)
            location_y *= 0.1

            if location_y == 0:
                location_y += limit

        else:
            location_x = round(round(location_x / increment_amount) * increment_amount, increment_length)
            limit = preference.snap.increment

            if op.view3d['location'].x < 0:
                limit = -limit

            if location_x == 0:
                location_x += limit

            location_y = round(round(location_y / increment_amount) * increment_amount, increment_length)

            if location_y == 0:
                location_y += limit


    use_alt = (event.alt and preference.keymap.alt_draw) or ((vert_lock or edge_lock or face_lock) and not event.alt)
    use_shift = ((event.shift and preference.keymap.shift_draw) or (face_lock or vert_lock or (edge_lock and op.shape_type == 'CIRCLE')) and not event.shift) and not mask_shift

    index1 = 0
    side_vec = deform_min
    clear_vec = deform_max
    draw_dot_index = ((1, 2), (5, 6))
    generate.flip_x = False

    if location_x > 0:
        index1 = 1
        side_vec = deform_max
        clear_vec = deform_min
        generate.flip_x = auto_flip


    if op.shape_type == 'CUSTOM':
        if preference.shape.auto_depth:
            use_shift = use_shift != preference.shape.auto_depth_custom_proportions

        else:
            op.proportional_draw = use_shift = (event.shift and preference.keymap.shift_draw) != preference.shape.auto_proportions
            use_shift = use_shift != (op.origin == 'CENTER' and preference.shape.auto_proportions)

    if use_alt and not use_shift:
        side_vec.x = location_x
        clear_vec.x = -location_x

    elif use_shift and not use_alt:
        side_vec.x = location_x
        clear_vec.x = 0

    elif use_shift and use_alt:
        side_vec.x = location_x
        clear_vec.x = -location_x

    elif not use_alt or not use_shift:
        side_vec.x = location_x

        if op.origin == 'CORNER':
            clear_vec.x = 0

        elif op.origin == 'CENTER':
            clear_vec.x = -location_x

    dim_x = abs(deform_max.x - deform_min.x)
    if op.origin == 'CENTER': dim_x *= 2
    preference.shape['dimension_x'] = preference.shape['circle_diameter'] = dim_x

    side_ratio = op.datablock['shape_proportions'].y


    side_vec = deform_min
    clear_vec = deform_max
    index2 = 0
    generate.flip_y = False

    if location_y > 0:
        index2 = 1
        side_vec = deform_max
        clear_vec = deform_min
        generate.flip_y = auto_flip

    draw_dot_index = draw_dot_index[index1]
    op.draw_dot_index = draw_dot_index[index2]

    if use_alt and not use_shift:
        side_vec.y = location_y
        clear_vec.y = -location_y

    elif use_shift and not use_alt:
        side_vec.y = copysign(location_x, location_y) * side_ratio
        clear_vec.y = 0

    elif use_shift and use_alt:
        side_vec.y =  copysign(location_x, location_y) * side_ratio
        clear_vec.y = -side_vec.y

    elif not use_alt or not use_shift:
        if op.origin == 'CENTER':
            side_vec.y = copysign(location_x, location_y) * side_ratio
            clear_vec.y = -side_vec.y

        else:
            side_vec.y = location_y
            clear_vec.y = 0

    # object space
    deform_min = deform_min + origin_offset
    deform_max = deform_max + origin_offset
    preference.shape['dimension_y'] = abs(deform_max.y - deform_min.y)

    op.last['draw_location'] = op.view3d['location']

    #TODO
    # if preference.shape.auto_depth and not op.align_to_view:
    #     points = bc.lattice.data.points
    #     pairs = ((0, 1), (1, 3), (2, 3), (0, 2))

    #     length = 0.0
    #     for pair in pairs:
    #         current = (points[front[pair[0]]].co_deform.to_2d() - points[front[pair[1]]].co_deform.to_2d()).length

    #         if not preference.shape.auto_depth_large:
    #             if not length or current < length:
    #                 length = current

    #             continue

    #         if current > length:
    #             length = current

    #     length *= preference.shape.auto_depth_multiplier

    #     if (event.shift != (preference.shape.auto_depth_custom_proportions and op.shape_type == 'CUSTOM')):
    #         length = preference.shape['dimension_x'] * op.datablock['shape_proportions'].z

    #     if op.mode in {'MAKE', 'JOIN'}:
    #         length = -length

    #     if op.mode in {'MAKE', 'JOIN'} or not op.clamp_extrude:
    #         delta = -length - points[front[0]].co_deform.z
    #         if (delta > 0 and not op.inverted_extrude) or (delta < 0 and op.inverted_extrude):
    #             op.inverted_extrude = not op.inverted_extrude
    #             op.clamp_extrude = False

    #     op.last['depth'] = -length
    #     op.start['extrude'] = -length

    #     preference.shape.lazorcut_depth = length

    deform.min = deform_min
    deform.max = deform_max

    reference = deform_max - deform_min

    if (not op.modified or not op.extruded) and not preference.shape.auto_depth and preference.behavior.adaptive_wedge:
        op.last['wedge_axis_map'] = dict()
        if abs(reference.x) < abs(reference.y):
            op.last['wedge_axis_map'][False] = 'X'
            op.last['wedge_axis_map'][True] = 'Y'

        else:
            op.last['wedge_axis_map'][False] = 'Y'
            op.last['wedge_axis_map'][True] = 'X'

    op.last['wedge_axis_map']['X'] = location_x < 0
    op.last['wedge_axis_map']['Y'] = location_y < 0

    wedge(op, context)


def draw_line(op, context, event):
    preference = addon.preference()
    bc = context.scene.bc
    deform: Deform = op.modifier_stack.deform
    deform_min = Vector(deform.min)
    deform_max = Vector(deform.max)
    dimensions = deform_max - deform_min

    matrix = bc.shape.matrix_world.copy()

    location = op.view3d['location'].to_2d()

    grid_handler = getattr(bc.snap.operator, 'grid_handler', None)
    if grid_handler:

        grid_handler.update(context, event)

        if grid_handler.snap_type == 'GRID' or (preference.snap.dot_dot_snap and grid_handler.nearest_dot):
            location = (bc.shape.matrix_world.inverted() @ grid_handler.snap_world).to_2d()

    else:
        points = [Vector((0, 1, 0)), Vector((1, -1, 0)), Vector((-1, -1, 0))]
        tri = [matrix @ point for point in points]

        ray = view3d.location2d_to_vector3d(*op.mouse['location'])
        origin =  view3d.location2d_to_origin3d(*op.mouse['location'])

        args = (*tri, ray, origin, False)

        intesect = geometry.intersect_ray_tri(*args)

        if intesect:
            location = (matrix.inverted() @ intesect).to_2d()


    deform.max = Vector()
    deform_min = Vector()
    deform_min.x = location.length
    deform.min = deform_min

    angle = location.angle_signed(Vector((1, 0)), 0)

    if event.ctrl and not preference.snap.angle_lock or not event.ctrl and preference.snap.angle_lock:
        snap_increment = radians(preference.snap.draw_line_angle)
        angle = round(angle / snap_increment) * snap_increment

    bc.shape.matrix_world = matrix @ Matrix.Rotation(angle, 4, 'Z')

    op.last['line'] = location.length


def offset(op, context, event):
    preference = addon.preference()
    bc = context.scene.bc

    deform: Deform = op.modifier_stack.deform
    deform_min = Vector(deform.min)
    deform_max = Vector(deform.max)

    snap = preference.snap.enable and (preference.snap.incremental or preference.snap.grid)
    snap_lock = snap and preference.snap.increment_lock
    double_offset = event.alt and preference.keymap.alt_double_extrude and not preference.keymap.alt_preserve and not bc.operator.alt_e

    shape = bc.shape

    location_z = op.view3d['location'].z
    op.element_snap_vec = None

    if preference.snap.mesh_element != 'NONE' and event.ctrl:
       location_z = element_snap(op, context, location_z)

    elif snap and event.ctrl or snap_lock:
        increment_amount = round(preference.snap.increment, 8)
        split = str(increment_amount).split('.')[1]
        increment_length = len(split) if int(split) != 0 else 0

        if event.shift:
            location_z = round(round(location_z * 10 / increment_amount) * increment_amount, increment_length)
            location_z *= 0.1

        else:
            location_z = round(round(location_z / increment_amount) * increment_amount, increment_length)

    # location = location_z + offset
    # matrix = op.start['matrix'] @ Matrix.Translation(Vector((0, 0, location)))

    extrude = op.start['extrude']
    center = op.last['deform_center']

    delta = op.view3d['location'] - op.back_plane
    dot = delta.dot(Vector((0.0, 0.0, 1.0)))

    limit = thickness_clamp(op, context)

    if double_offset:
        extrude = center.z - (location_z - center.z)
        delta = op.view3d['location'] - center
        dot = delta.dot(Vector((0.0, 0.0, 1.0)))

    if op.mode in {'MAKE', 'JOIN'} or not op.clamp_extrude:
        if (dot < 0 and not op.inverted_extrude) or (dot > 0 and op.inverted_extrude):
            op.inverted_extrude = not op.inverted_extrude
            op.clamp_extrude = False

    else:
        if location_z <= extrude and double_offset:
            extrude = center.z

        if dot < 0:
            location_z = op.back_plane.z + limit

    deform_max.z = location_z
    deform.max = deform_max

    deform_min.z = extrude
    deform.min = deform_min

    if not op.extruded:
        deform_min.z = deform_max.z #TODO add offset?
        deform.min = deform_min

    op.last['depth'] = extrude

def extrude(op, context, event):
    preference = addon.preference()
    bc = context.scene.bc

    snap = preference.snap.enable and (preference.snap.incremental or (preference.snap.grid and (bc.snap.display or event.ctrl)))
    snap_lock = snap and preference.snap.increment_lock
    double_extrude = event.alt and preference.keymap.alt_double_extrude# and not preference.keymap.alt_preserve and not bc.operator.alt_e

    location_z = op.view3d['location'].z

    increment_amount = round(preference.snap.increment, 8)
    split = str(increment_amount).split('.')[1]
    increment_length = len(split) if int(split) != 0 else 0
    op.element_snap_vec = None

    deform: Deform = op.modifier_stack.deform
    deform_min = Vector(deform.min)
    deform_max = Vector(deform.max)

    if not op.extruded:
        op.extruded = True

    if snap and event.ctrl or (snap_lock and not event.ctrl):
        if event.shift:
            location_z = round(round(location_z * 10 / increment_amount) * increment_amount, increment_length)
            location_z *= 0.1

        else:
            location_z = round(round(location_z / increment_amount) * increment_amount, increment_length)

    front_plane = op.input_plane.z
    center = op.last['deform_center']

    if double_extrude:
        front_plane = center.z - (location_z - center.z)

    if op.mode in {'MAKE', 'JOIN'} or not op.clamp_extrude:
        delta = location_z - deform_max.z
        if (delta > 0 and not op.inverted_extrude) or (delta < 0 and op.inverted_extrude):
            op.inverted_extrude = not op.inverted_extrude
            op.clamp_extrude = False

    else:
        if location_z >= front_plane and double_extrude:
            front_plane = center.z

        clamp = thickness_clamp(op, context)
        delta = location_z - front_plane
        location_z = location_z if delta < 0 and abs(delta) > clamp else front_plane - clamp

    deform_max.z = front_plane

    dpi_factor = screen.dpi_factor(ui_scale=False, integer=True)

    threshold = context.preferences.inputs.drag_threshold_mouse * 3 * dpi_factor
    distance = (op.mouse['location'] - op.last['mouse']).length / dpi_factor

    width = -(op.draw_exit_width - view3d.location2d_to_location3d(*op.mouse['location'], op.ray['location'])).length

    if preference.snap.mesh_element != 'NONE' and event.ctrl:
       location_z = element_snap(op, context, location_z)

    elif snap and event.ctrl or (snap_lock and not event.ctrl):

        if event.shift:
            location_z = round(round(location_z * 10 / increment_amount) * increment_amount, increment_length)
            location_z *= 0.1

        else:
            width = round(round(width / increment_amount) * increment_amount, increment_length)

    elif event.ctrl and preference.keymap.ctrl_multiplier > 0 and -width * preference.keymap.ctrl_multiplier > preference.shape.offset:
        width *= -width * preference.keymap.ctrl_multiplier

    if op.alt_toggle_extrude:
        op.alt_extrude = not op.alt_extrude

    view = context.region_data.view_rotation.to_matrix().to_4x4()
    view_changed = op.start['view_rotation'] != view
    view_locked = not view_changed and distance > threshold

    if preference.behavior.accucut and op.live and not view_locked and not view_changed:
        location_z = op.start['extrude']

    location_z = location_z if not preference.keymap.alternate_extrude or not op.alt_extrude or not op.live or not view_locked or op.mode in {'MAKE', 'JOIN'} or not op.clamp_extrude else width

    if event.ctrl:
        if op.shape_type == 'CUSTOM':
            location_z = copysign(preference.shape['dimension_x'] * op.datablock['shape_proportions'].z, location_z)

        elif preference.shape.wedge:
            side = preference.shape['dimension_x'] if deform.wedge_mode == 'X' else preference.shape['dimension_y'];
            location_z = copysign(side, location_z)

    op.last['depth'] = location_z if not preference.behavior.accucut or not op.live or op.modified or abs(location_z) < op.last['accucut_depth'] or preference.shape.wedge or op.mode in {'MAKE', 'JOIN'} or not op.alt_extrude or not op.clamp_extrude else -op.last['accucut_depth']

    thickness = op.last['depth'] - deform_max.z

    if (thickness > 0 and not op.inverted_extrude) or (thickness < 0 and op.inverted_extrude):
        op.last['depth'] = -op.last['depth']

    deform_min.z = op.last['depth']
    deform.min = deform_min
    deform.max = deform_max

def apply(op, context):
    bc = context.scene.bc

    deform: Deform = op.modifier_stack.deform
    mesh_min, mesh_max = mesh_min_max(bc.shape.data)
    deform_min = Vector(deform.min)
    deform_max = Vector(deform.max)

    dmesh = mesh_max - mesh_min

    # degenerate check
    for i in range(3):
        if dmesh[i] == 0.0:
            mesh_min[i] = 0.0
            mesh_max[i] = 1.0

    # flip if draw is flipped
    for i in range(3):
        if deform_max[i] < deform_min:
            v_min = deform_min[i]
            deform_min[i] = deform_max[i]
            deform_max[i] = v_min

    # non-custom shape are 2d
    if op.shape_type != 'CUSTOM':
        center = (deform_max.z + deform_min.z) * 0.5
        deform_min.z = deform_max.z = center

    for v in bc.shape.data.vertices:
        v.co = remap(v.co, mesh_min, mesh_max, deform_min, deform_max)

def fit(op, context):
    preference = addon.preference()
    bc = context.scene.bc

    deform: Deform = op.modifier_stack.deform
    mesh_min, mesh_max = mesh_min_max(bc.shape.data)

    scale = mesh_max - mesh_min
    if deform.method == 'Z ONLY':
        mesh_min.z = deform.z_min
        mesh_max.z = deform.z_max
        deform.method = 'CORNER'
        #scale.z = abs(deform.z_max - deform.z_min)

    preference.shape['dimension_x'] = scale.x
    preference.shape['dimension_y'] = scale.y
    preference.shape['dimension_z'] = scale.z

    op.datablock['shape_proportions'] = scale / scale.x if scale.x else scale
    op.datablock['shape_proportions'].z = 1

    deform.min = mesh_min
    deform.max = mesh_max

    op.draw_dot_index = 1

def element_snap(op, context, location_z) -> float:

    def nearest_edge_pair(eval_data, face_i, location) -> (Vector, Vector, Vector):
        smallest = sys.float_info.max
        v1 = Vector()
        v2 = Vector ()
        projection = Vector ()

        for i, j in eval_data.polygons[face_i].edge_keys:
            co1 = eval_data.vertices[i].co
            co2 = eval_data.vertices[j].co
            dloc = location - co1

            proj = dloc.project(co2 - co1)
            dist = (proj - dloc).magnitude

            if dist < smallest:
                smallest = dist
                projection = proj + co1
                v1 = co1.copy()
                v2 = co2.copy()

        return (v1, v2, projection)

    bc = context.scene.bc
    preference = addon.preference()
    element_type = preference.snap.mesh_element
    op.element_snap_vec = None

    coord2d = op.mouse['location']
    origin = region_2d_to_origin_3d(context.region, context.space_data.region_3d, coord2d)
    direction = region_2d_to_vector_3d(context.region, context.space_data.region_3d, coord2d)
    view_layer = context.view_layer if bpy.app.version[:2] < (2, 91) else context.view_layer.depsgraph
    hit, location, normal, index, object, matrix = context.scene.ray_cast(view_layer, origin, direction)

    if not hit or object.type != 'MESH': return location_z
    eval_data = object.evaluated_get(context.evaluated_depsgraph_get()).data

    if index > len(eval_data.polygons) - 1 : return location_z

    if element_type == 'VERT':
        local = matrix.inverted() @ location
        min_co = Vector()
        smallest = sys.float_info.max

        for i in eval_data.polygons[index].vertices:
            co = eval_data.vertices[i].co

            dist = (co - local).magnitude

            if dist < smallest:
                smallest = dist
                min_co = co

        op.element_snap_vec = bc.shape.matrix_world.inverted() @ matrix @ min_co
        location_z = op.element_snap_vec.z

    elif element_type == 'EDGE':
        local = matrix.inverted() @ location

        *_, projection = nearest_edge_pair(eval_data, index, local)

        op.element_snap_vec = bc.shape.matrix_world.inverted() @ ( matrix @ projection)
        location_z = op.element_snap_vec.z

    elif element_type == 'EDGE_CENTER':
        local = matrix.inverted() @ location

        v1, v2, _ = nearest_edge_pair(eval_data, index, local)
        center = (v1 + v2) * 0.5

        op.element_snap_vec = bc.shape.matrix_world.inverted() @ matrix @ center
        location_z = op.element_snap_vec.z

    elif element_type == 'FACE':
        op.element_snap_vec = bc.shape.matrix_world.inverted() @ location
        location_z = op.element_snap_vec.z

    if preference.snap.mesh_element_exact and not preference.behavior.boolean_solver == 'EXACT':
        preference.behavior.boolean_solver = 'EXACT'

    return location_z

def mesh_min_max(mesh):
    tmp = bpy.data.objects.new('tmp', mesh)
    bounds = [Vector(v) for v in tmp.bound_box]
    bpy.data.objects.remove(tmp)

    # mesh min max vecs
    mesh_min = Vector((sys.float_info.max, sys.float_info.max, sys.float_info.max))
    mesh_max = Vector((sys.float_info.min, sys.float_info.min, sys.float_info.min))

    for vec in bounds:
        for i in range(3):
            if vec[i] < mesh_min[i]:
                mesh_min[i] = vec[i]
            elif vec[i] > mesh_max[i]:
                mesh_max[i] = vec[i]

    return mesh_min, mesh_max

def remap(vector, from_min, from_max, to_min, to_max):
    '''Remap vector from one range to another. Assume difference between from value is non zero'''
    dfrom = from_max - from_min
    dto = to_max - to_min

    new = Vector()
    for i in range(3):
        slope = dto[i] / dfrom[i]
        new[i] = to_min[i] + slope * (vector[i] - from_min[i])


    return new


def deform_method(op, method='CORNER'):
    """Methods: 'CORNER', 'CENTER', 'DIMENSIONS', 'Z ONLY'"""
    deform: Deform = op.modifier_stack.deform

    deform_method_sync(op)

    deform.method = method

def deform_method_sync(op):
    deform: Deform = op.modifier_stack.deform
    method = deform.method

    if method == 'CORNER':
        dmin = Vector(deform.min)
        dmax = Vector(deform.max)
        center = (dmin + dmax) * 0.5
        dimensions = dmin - dmax

        for i in range(3):
            dimensions[i] = abs(dimensions[i])

        # dimensions
        deform.center = center
        deform.dimensions

        # center
        deform.offset = dmin #?

        # z only
        deform.z_min = dmin.z
        deform.z_max = dmax.z

    elif method == 'DIMENSIONS':
        center = Vector(deform.center)
        dimensions = Vector(deform.dimensions)
        half_d = dimensions * 0.5

        dmin = center - half_d
        dmax = center + half_d
        # corner
        deform.min = dmin
        deform.max = dmax

        # center
        deform.offset = dmin #?

        # z only
        deform.z_min = dmin.z
        deform.z_max = dmax.z

    elif method == 'Z ONLY':
        # these should be up to date
        mmin = Vector(op.mesh_min)
        mmax = Vector(op.mesh_max)
        mmin.z = deform.z_min
        mmax.z = deform.z_max

        center = (mmin + mmax) * 0.5
        dimensions = Vector(deform.dimensions)

        # dimensions
        deform.center = center
        deform.dimensions

        # center
        deform.offset = mmin #?

        # corner
        deform.min = mmin
        deform.max = mmax

def wedge(op, context):
    bc = context.scene.bc
    deform: Deform = op.modifier_stack.deform
    preference = addon.preference()


    deform.wedge = preference.shape.wedge
    wedge_mode = op.last['wedge_axis_map'][bc.wedge_slim]

    deform.wedge_mode =  wedge_mode
    deform.wedge_factor = preference.shape.wedge_factor
    deform.wedge_width = preference.shape.wedge_width
    deform.wedge_offset = 0.00001

    deform.wedge_flip =  op.last['wedge_axis_map'][wedge_mode]
