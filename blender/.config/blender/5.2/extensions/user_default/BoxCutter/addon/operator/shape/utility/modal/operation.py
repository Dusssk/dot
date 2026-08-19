import bpy, numpy
from mathutils import Matrix, Vector

from . import refresh, bevel

from ..... import toolbar

from ...... utility import addon, view3d, math, modifier, version
from .. import mesh, lattice, data, nodes
from ... import utility


def change(op, context, event, to='NONE', modified=True, init=False, clear_mods=[], dot=False):
    if op.workflow_nodes:
        return change_nodes(op, context, event, to, modified, init, clear_mods, dot)

    return change_classic(op, context, event, to, modified, init, clear_mods, dot)

def change_classic(op, context, event, to='NONE', modified=True, init=False, clear_mods=[], dot=False):
    from .. import bound_box, dimensions

    preference = addon.preference()
    bc = context.scene.bc
    op.modified = modified

    ngon = op.shape_type == 'NGON' or op.ngon_fit
    boxgon = op.shape_type == 'BOX' and not op.ngon_fit and (op.ngon_point_index != -1 or op.ngon_point_bevel)
    op.element_snap_vec = None

    clamp = bevel.clamp(op)

    if modified and op.lmb:
        op.modified_lock = True
    else:
        op.modified_lock = False

    if to == 'BEVEL_Q':
        bc.q_bevel = not bc.q_bevel
        bc.shape.data.bc.q_beveled = bc.q_bevel
        to = 'BEVEL'

    if to == 'BEVEL_INSET':
        if not preference.behavior.inset_bevel:
            preference.behavior.inset_bevel = True

        bc.shape.data.bc.inset_bevel = True
        to = 'BEVEL'

    elif bc.shape.data.bc.inset_bevel:
        bc.shape.data.bc.inset_bevel = False

    if to in {'SOLIDIFY', 'BEVEL'} and bc.bevel:
        to = 'BEVEL'
        bc.shape.data.bc.inset_bevel = True

    if not init:
        op.last['operation'] = op.operation

    for mod in bc.shape.modifiers:
        if mod.type in clear_mods:
            if hasattr(bc.shape.bc, mod.type.lower()):
                setattr(bc.shape.bc, mod.type.lower(), False)
            bc.shape.modifiers.remove(mod)

    op.last['lattice_corner'] = lattice.center(Matrix(), 'front') * 2 - Vector(bound_box(lattice=True)[op.draw_dot_index])
    op.last['lattice_center'] = lattice.center(Matrix(), None)

    front = (1, 2, 5, 6)
    back = (0, 3, 4, 7)
    side = front
    side = back if op.inverted_extrude else front

    op.input_plane = math.vector_sum([(op.bounds[i] if op.shape_type != 'NGON' or op.ngon_fit else Vector(bound_box()[i])) for i in side]) / 4
    op.front_plane = math.vector_sum([(op.bounds[i] if op.shape_type != 'NGON' or op.ngon_fit else Vector(bound_box()[i])) for i in front]) / 4
    op.back_plane = math.vector_sum([(op.bounds[i] if op.shape_type != 'NGON' or op.ngon_fit else Vector(bound_box()[i])) for i in back]) / 4

    if op.inverted_extrude:
        front = Vector(op.front_plane)
        op.back_plane = op.front_plane
        op.front_plane = op.back_plane

    # op.ray['location'] = math.vector_sum([bc.shape.matrix_world @ op.bounds[i] for i in (1, 2, 5, 6)]) / 4

    if not init:
        op.last['draw_delta'] = Vector(op.bounds[op.draw_dot_index]) - Vector(bound_box()[op.draw_dot_index]) if op.extruded else Vector((0,0,0))

    preference.shape['dimension_x'] = preference.shape['circle_diameter'] =  dimensions().x / (bc.lattice.scale.x if bc.lattice.scale.x else 1)
    preference.shape['dimension_y'] = dimensions().y / (bc.lattice.scale.y if bc.lattice.scale.y else 1)
    preference.shape['dimension_z'] = dimensions().z / (bc.lattice.scale.z if bc.lattice.scale.z else 1)

    if op.operation == 'NONE':
        for mod in bc.shape.modifiers:
            if mod.type != 'BEVEL':
                continue

            width_type = 'bevel_width' if mod.name.startswith('Bevel') else F'{mod.name.split(" ")[0].lower()}_bevel_width'

            clmp = clamp if 'Quad' not in mod.name else bevel.clamp(op, q=True)

            if mod.width > clmp:
                op.last['modifier'][width_type] = mod.width

    if op.operation == 'DRAW':
        if op.shape_type == 'NGON' and not op.add_point:
            mesh.remove_point(op, context, event)

        op.last['accucut_distance'] = 0.0
        op.last['accucut_depth'] = preference.shape.offset if preference.behavior.boolean_solver == version.bsolver_fast() else 0
        op.snap_lock_type = ''

        if op.shape_type == 'BOX' and preference.shape.box_grid and not op.ngon_fit and not op.extruded:
            for i in op.geo['indices']['offset']:
                bc.shape.data.vertices[i].co.z = 0.5

        if not hasattr(op, 'draw_exit_width'):
            op.draw_exit_width = view3d.location2d_to_location3d(*op.mouse['location'], op.ray['location'])

        if to == 'EXTRUDE' and op.live and not op.modified and preference.behavior.accucut and not op.lazorcut_performed:
            prev_mode = op.mode
            op.last['accucut_distance'], op.last['accucut_depth'] = utility.accucut(op, context, reset=True)

            if not (op.shape_type == 'CUSTOM' and op.proportional_draw) and op.last['accucut_depth'] < min(op.datablock['dimensions'][:]) * 0.1:
                preference.behavior.accucut = False

    elif op.operation in {'EXTRUDE', 'OFFSET', 'SCALE', 'ROTATE', 'MOVE'}:
        bc.plane.matrix_world = bc.shape.matrix_world
        op.start['matrix'] = bc.plane.matrix_world.copy()
        extrude_index = 1 if op.inverted_extrude else 0
        op.start['extrude'] = op.last['depth'] = bound_box()[extrude_index][2]

        # op.ray['location'] = math.vector_sum([bc.shape.matrix_world @ Vector(bound_box[i]) for i in (1, 2, 5, 6)]) / 4

    elif op.operation == 'ARRAY':
        axis_index = [bc.shape.bc.array_axis == axis for axis in 'XYZ'].index(True)

        for mod in bc.shape.modifiers:
            if mod.type == 'ARRAY':
                op.last['modifier']['offset'] = mod.constant_offset_displace[axis_index]
                op.last['modifier']['count'] = mod.count
                break

        if to == 'ARRAY' and not bc.shape.bc.array_circle:
            bc.shape.bc['array_circle'] = True

            mesh.pivot(op, context)

        elif to == 'ARRAY' and op.operation == 'ARRAY' and bc.shape.bc.array_circle:
            bc.shape.bc['array_circle'] = False
            for mod in bc.shape.modifiers:
                if mod.type == 'ARRAY':
                    bc.shape.modifiers.remove(mod)
                elif mod.type == 'DISPLACE':
                    bc.shape.modifiers.remove(mod)

    elif op.operation == 'SOLIDIFY':
        obj = bc.shape if op.mode != 'INSET' else (op.datablock['insets'][-1] if op.datablock['insets'] else None)
        if obj:
            for mod in obj.modifiers:
                if mod.type == 'SOLIDIFY':
                    if op.mode != 'INSET':
                        op.last['modifier']['thickness'] = mod.thickness
                    else:
                        op.last['thickness'] = mod.thickness
                    break

            if modified:
                if to == 'SOLIDIFY': to = 'NONE'

        del obj

    elif op.operation == 'BEVEL':
        for mod in bc.shape.modifiers:
            if mod.type == 'BEVEL' and not init:
                width_type = 'bevel_width' if mod.name.startswith('Bevel') else F'{mod.name.split(" ")[0].lower()}_bevel_width'

                clmp = clamp if 'Quad' not in mod.name else bevel.clamp(op, q=True)

                if mod.width > clmp:
                    op.last['modifier'][width_type] = mod.width

                op.last['modifier']['segments'] = mod.segments
                op.last['modifier']['limit_method'] = mod.limit_method
                preference.shape['bevel_segments'] = mod.segments
                if bpy.app.version[:2] < (2, 90):
                    op.last['modifier']['use_only_vertices'] = mod.use_only_vertices
                else:
                    op.last['modifier']['affect'] = mod.affect
                op.last['modifier']['use_clamp_overlap'] = mod.use_clamp_overlap
                #break

        op.last['mouse'] = op.mouse['location']

        if to == 'NONE' and clear_mods and op.ngon_point_index != -1:
            indices = op.geo['indices']['offset'] if not op.inverted_extrude else op.geo['indices']['extrusion']
            for index, vindex in enumerate(indices):
                if vindex != op.ngon_point_index:
                    continue

                mesh.index_weight(index, value=0)
                mesh.index_weight(vindex, vert=True, value=0)

        op.ngon_point_index = -1

        if modified:
            if to == 'BEVEL':
                for mod in bc.shape.modifiers:
                    if mod.type not in {'WELD', 'VERTEX_WEIGHT_MIX', 'VERTEX_WEIGHT_EDIT'}:
                        continue

                    bc.shape.modifiers.remove(mod)

                to = 'NONE'

    elif op.operation == 'ROTATE':
        op.rotated = True

    elif op.operation == 'SCALE':
        op.scaled = True

    elif op.operation == 'MOVE':
        op.translated = True

    elif op.operation == 'TAPER':
        if to == 'TAPER':
            to = 'NONE'

    rebevel = False
    if boxgon:
        if op.operation == 'DRAW' and to == 'NONE':
            if not op.extruded and op.ngon_point_index == -1:
                bc.shape.data.transform(Matrix.Scale(-1, 4, Vector((0, 0, 1))))

            lattice.fit(op, context, ngon=False)

            if not op.extruded:
                op.extruded = True

            op.ngon_point_index = -1

    if ngon:
        if to in {'EXTRUDE', 'OFFSET'} and not op.extruded:
            for mod in bc.shape.modifiers:
                if mod.type == 'BEVEL':
                    bc.shape.modifiers.remove(mod)

                    rebevel = True

            amount = -1
            if op.ngon_fit:
                amount = -0.5

                matrix = Matrix.Translation((0, 0, 0.5))
                bc.shape.data.transform(matrix)

                preference.shape.taper = preference.shape.taper

                op.start['extrude'] = bc.lattice.data.points[lattice.front[0]].co_deform.z

                for i in lattice.back:
                    bc.lattice.data.points[i].co_deform.z = op.start['extrude']

            mesh.extrude(op, context, event, amount=amount)

        if to != 'DRAW' and not op.ngon_fit:
            lattice.fit(op, context)

            if op.extruded:
                preference.shape.taper = preference.shape.taper

            op.shape_type = 'BOX'
            op.ngon_fit = True
            op.last['lattice_corner'] = lattice.center(Matrix(), 'front') * 2 - Vector(bound_box()[op.draw_dot_index])
            op.last['lattice_center'] = lattice.center(Matrix(), None)
            op.bounds = [Vector(c) for c in bound_box()]

    if op.modified and op.alt_lock:
        op.alt_lock = False

    if to == 'ROTATE':
        op.last['mouse'] = op.mouse['location']
        op.last['local_pivot'] = mesh.pivot(op, context, transform=False)
        op.last['global_pivot'] = bc.shape.matrix_world @ op.last['local_pivot']
        op.last['matrix'] = bc.shape.matrix_world.copy()
        if bc.snap.operator:
            if hasattr(bc.snap.operator, 'grid_handler'):
                bc.snap.operator.grid_handler.draw = True # force snap
                bc.snap.operator.grid_handler.update(context, event)
                op.last['snap_location'] = bc.snap.operator.grid_handler.snap_world.copy()

            else:
                bc.snap.operator.handler.update(context, Vector((event.mouse_region_x, event.mouse_region_y)))
                op.last['snap_location'] = Vector(bc.snap.location)

    if to == 'SCALE':
        op.last['mouse'] = op.mouse['location']
        op.last['local_pivot'] = mesh.pivot(op, context, transform=False)
        op.last['global_pivot'] = bc.shape.matrix_world @ op.last['local_pivot']
        op.last['lattice_points'] = [p.co_deform[:] for p in bc.lattice.data.points]
        op.last['matrix'] = bc.shape.matrix_world.copy()
        op.last['scale'] = (view3d.location3d_to_location2d(op.last['global_pivot']) - op.last['mouse']).length
        op.last['axis'] = 'XYZ'
        if bc.snap.operator:
            if hasattr(bc.snap.operator, 'grid_handler'):
                bc.snap.operator.grid_handler.draw = True # force snap
                bc.snap.operator.grid_handler.update(context, event)
                op.last['snap_location'] = bc.snap.operator.grid_handler.snap_world.copy()

            else:
                bc.snap.operator.handler.update(context, Vector((event.mouse_region_x, event.mouse_region_y)))
                op.last['snap_location'] = Vector(bc.snap.location)

    if to == 'MOVE':
        op.last['location'] = bc.shape.matrix_world @ bc.shape.location
        op.last['view3d_location'] = op.view3d['location']
        op.last['matrix'] = bc.shape.matrix_world.copy()
        op.last['axis'] = 'XY'

    if to == 'BEVEL':
        bc.shape.data.bc.q_beveled = bc.q_bevel

        if ngon or boxgon:
            for index, vindex in enumerate(op.geo['indices']['offset']):
                op.last['vert_weight'][index] = mesh.index_weight(vindex, vert=True)

            op.last['edge_weight'] = [mesh.index_weight(edge.index) for edge in bc.shape.data.edges]

            # from . bevel import clamp_and_visual_weight
            # clamp_and_visual_weight(op, bc, preference, clamp, set=op.shape_type == 'NGON' and op.ngon_point_index == -1 and not op.ngon_point_bevel)

    else:
        op.ngon_point_index = -1

    if to != 'MIRROR':
        preference.shape['mirror_gizmo'] = False

    elif preference.shape.mirror_gizmo:
        context.window_manager.gizmo_group_type_ensure("BC_GGT_mirror")
        mod = None

        for m in reversed(bc.shape.modifiers):
            if m.type == 'MIRROR':
                mod = m
                break

        if mod and any(mod.use_axis):
            eval = bc.shape.evaluated_get(context.evaluated_depsgraph_get())

            if not len(eval.data.vertices):
                    bc.shape.modifiers.remove(mod)
                    bc.shape.data.update()

    if to == 'DRAW':
        if dot:
            widget = bc.shader.widgets.active
            loc3d = bc.shape.matrix_world @ bound_box(True)[op.draw_dot_index] if widget.type == 'DRAW' else widget.transform @ widget.location
            loc2d = view3d.location3d_to_location2d(loc3d)
            op.mouse['offset'] = loc2d - op.mouse['location']

    else:
        op.mouse['offset'] = Vector((0, 0))

    value = to

    op.operation = value
    toolbar.change_prop(context, 'operation', value)

    if value in {'EXTRUDE', 'OFFSET'}:
        mouse = op.mouse['location']

        bc.plane.matrix_world = bc.shape.matrix_world
        matrix = bc.plane.matrix_world
        inverse = matrix.inverted()

        if not op.inverted_extrude:
            front = (1, 2, 5, 6)
            back = (0, 3, 4, 7)
        else:
            back = (1, 2, 5, 6)
            front = (0, 3, 4, 7)

        front_center = (0.25 * sum((op.bounds[point] for point in front), Vector()))
        back_center = (0.25 * sum((op.bounds[point] for point in back), Vector()))
        coord = matrix @ (front_center if value == 'OFFSET' else back_center)

        op.start['intersect'] = inverse @ view3d.location2d_to_location3d(mouse.x, mouse.y, coord)

        op.start['offset'] = front_center.z
        op.start['extrude'] = back_center.z
        op.start['matrix'] = bc.shape.matrix_world.copy()
        op.last['bounds_center'] = (front_center + back_center) / 2

    elif value == 'ROTATE':
        op.angle = 0

        op.last['track'] = op.mouse['location'] - view3d.location3d_to_location2d(bc.lattice.matrix_world.translation)
        op.last['mouse'] = op.mouse['location']

        bc.axis = 'Z' if bc.axis == 'NONE' else bc.axis

    elif value == 'ARRAY':
        bc.shape.bc.array = True
        refresh.input_update_classic(op, context)
        op.start['displace'] = preference.shape.displace
        op.last['view3d_location'] = op.view3d['location']

        if bc.flip:
            bc.flip = False

        axis_index = [bc.shape.bc.array_axis == axis for axis in 'XYZ'].index(True)

        for mod in bc.shape.modifiers:
            if mod.type == 'ARRAY':
                op.last['modifier']['offset'] = mod.constant_offset_displace[axis_index]
                op.last['modifier']['count'] = mod.count
                op.last['mouse'] = op.mouse['location']

                break

    elif value == 'SOLIDIFY':
        bc.shape.bc.solidify = True
        obj = bc.shape if op.mode != 'INSET' else (op.datablock['insets'][-1] if op.datablock['insets'] else None )

        if obj:
            for mod in obj.modifiers:
                if mod.type == 'SOLIDIFY':
                    if op.mode != 'INSET':
                        op.last['modifier']['thickness'] = mod.thickness

                    else:
                        op.last['thickness'] = mod.thickness

                    break

        del obj

        op.last['mouse'] = op.mouse['location']

    elif value == 'BEVEL':
        bc.shape.bc.bevel = True
        for mod in bc.shape.modifiers[:]:
            if mod.type == 'BEVEL':
                clmp = clamp if 'Quad' not in mod.name else bevel.clamp(op, q=True)

                if mod.name.startswith('Quad'):
                    preference.shape['quad_bevel_segments'] = mod.segments

                    if mod.width > clmp:
                        op.last['modifier']['quad_bevel_width'] = mod.width

                elif mod.name.startswith('Front'):
                    preference.shape['front_bevel_segments'] = mod.segments

                    if mod.width > clmp:
                        op.last['modifier']['front_bevel_width'] = mod.width

                else:
                    preference.shape['bevel_segments'] = mod.segments

                    if mod.width > clmp:
                        op.last['modifier']['bevel_width'] = mod.width

                bc.shape.modifiers.remove(mod)

            elif mod.type in {'WELD', 'VERTEX_WEIGHT_MIX', 'VERTEX_WEIGHT_EDIT'}:
                bc.shape.modifiers.remove(mod)

        op.last['mouse'] = op.mouse['location']

    elif value == 'DISPLACE':
        displace = None
        refresh.input_update_classic(op, context)
        op.last['view3d_location'] = op.view3d['location']

        for mod in bc.shape.modifiers:
            if mod.type == 'DISPLACE':
                displace = mod

                break

        if displace:
            op.start['displace'] = displace.strength

    elif value == 'TAPER':
        op.last['taper'] = preference.shape.taper
        op.last['mouse'] = op.mouse['location']

    if not init:
        if value == 'NONE':
            op.report({'INFO'}, 'Shape Locked')

        else:
            op.report({'INFO'}, '{}{}{}'.format(
                'Added ' if value == 'ARRAY' else '',
                value.title()[:-1 if value in {'MOVE', 'ROTATE', 'SCALE', 'EXTRUDE', 'DISPLACE'} else len(value)],
                'ing' if value not in {'ARRAY', 'GRID'} else ''))

        refresh.shape(op, context, event, dot=dot)

    elif value != 'DRAW':
        refresh.shape(op, context, event)

    if rebevel:
        bevel.shape(op, context, event)

    if to != 'MOVE':
        op.move_lock = False

def change_nodes(op, context, event, to='NONE', modified=True, init=False, clear_mods=[], dot=False):
    from .. import bound_box

    preference = addon.preference()
    bc = context.scene.bc
    op.modified = modified

    ngon = op.shape_type == 'NGON' or op.ngon_fit
    boxgon = op.shape_type == 'BOX' and not op.ngon_fit and (op.ngon_point_index != -1 or op.ngon_point_bevel)
    op.element_snap_vec = None

    if modified and op.lmb:
        op.modified_lock = True
    else:
        op.modified_lock = False

    if to == 'BEVEL_Q':
        bc.q_bevel = not bc.q_bevel
        bc.shape.data.bc.q_beveled = bc.q_bevel
        to = 'BEVEL'

    if to == 'BEVEL_INSET':
        if not preference.behavior.inset_bevel:
            preference.behavior.inset_bevel = True

        bc.shape.data.bc.inset_bevel = True
        to = 'BEVEL'

    elif bc.shape.data.bc.inset_bevel:
        bc.shape.data.bc.inset_bevel = False

    if to in {'SOLIDIFY', 'BEVEL'} and bc.bevel:
        to = 'BEVEL'
        bc.shape.data.bc.inset_bevel = True

    if not init:
        op.last['operation'] = op.operation

    # old semantics. modifier stack is persistent
    for mod in bc.shape.modifiers:
        if mod.type in clear_mods:
            if hasattr(bc.shape.bc, mod.type.lower()):
                setattr(bc.shape.bc, mod.type.lower(), False)
                mod.show_viewport = False

    mod_stack: data.ModifierStack = op.modifier_stack
    deform = mod_stack.deform
    deform_min = Vector(deform.min)
    deform_max = Vector(deform.max)
    deform_center = (deform_min + deform_max) * 0.5

    op.input_plane = deform_max.copy()
    op.front_plane = deform_max.copy()
    op.back_plane = deform_min.copy()
    dims = deform_max - deform_min

    for i in range(3):
        dims[i] = abs(dims[i])

    op.last['deform_min'] = deform_min
    op.last['deform_max'] = deform_max
    op.last['deform_center'] = deform_center

    bounds = math.coordinate_bounds((deform_min, deform_max))
    top_center = deform_center.copy()
    top_center.z = deform_max.z
    op.last['deform_corner'] = (top_center * 2) - bounds[op.draw_dot_index]
    op.mesh_min, op.mesh_max = nodes.deform_modal.mesh_min_max(bc.shape.data)

    if not init:
        #TODO:?
        #op.last['draw_delta'] = Vector(op.bounds[op.draw_dot_index]) - Vector(bound_box()[op.draw_dot_index]) if op.extruded else Vector((0,0,0))
        op.last['draw_delta'] = Vector()

    preference.shape['dimension_x'] = preference.shape['circle_diameter'] =  dims.x
    preference.shape['dimension_y'] = dims.y
    preference.shape['dimension_z'] = dims.z

    if op.operation == 'DRAW':
        if op.shape_type == 'NGON' and not op.add_point:
            mesh.remove_point(op, context, event)

        op.last['accucut_distance'] = 0.0
        op.last['accucut_depth'] = preference.shape.offset if preference.behavior.boolean_solver == version.bsolver_fast() else 0
        op.snap_lock_type = ''

        if not hasattr(op, 'draw_exit_width'):
            op.draw_exit_width = view3d.location2d_to_location3d(*op.mouse['location'], op.ray['location'])

        if op.shape_type == 'NGON' and not op.extruded:
            nodes.deform_modal.fit(op, context)
            op.shape_type = 'BOX'
            op.ngon_fit = True

        if to == 'EXTRUDE' and op.live and not op.modified and preference.behavior.accucut and not op.lazorcut_performed:
            prev_mode = op.mode
            op.last['accucut_distance'], op.last['accucut_depth'] = utility.accucut(op, context, reset=True)

            if not (op.shape_type == 'CUSTOM' and op.proportional_draw) and op.last['accucut_depth'] < min(op.datablock['dimensions'][:]) * 0.1:
                preference.behavior.accucut = False

    elif op.operation in {'EXTRUDE', 'OFFSET', 'SCALE', 'ROTATE', 'MOVE'}:
        bc.plane.matrix_world = bc.shape.matrix_world
        op.start['matrix'] = bc.plane.matrix_world.copy()
        op.start['extrude'] = op.last['depth'] = deform.min[2]

    elif op.operation == 'ARRAY':
        axis_index = [bc.shape.bc.array_axis == axis for axis in 'XYZ'].index(True)
        array = mod_stack.array

        op.last['modifier']['offset'] = array.offset[axis_index]
        op.last['modifier']['count'] = array.count

        if to == 'ARRAY' and not bc.shape.bc.array_circle:
            bc.shape.bc['array_circle'] = True

            array.mode = 'LINEAR'

        elif to == 'ARRAY' and op.operation == 'ARRAY' and bc.shape.bc.array_circle:
            bc.shape.bc['array_circle'] = False
            array.mode = 'LINEAR'
            array.show_viewport = False

    elif op.operation == 'SOLIDIFY':
        obj = bc.shape if op.mode != 'INSET' else (op.datablock['insets'][-1] if op.datablock['insets'] else None)
        if obj:
            for mod in obj.modifiers:
                if mod.type == 'SOLIDIFY':
                    if op.mode != 'INSET':
                        op.last['modifier']['thickness'] = mod.thickness
                    else:
                        op.last['thickness'] = mod.thickness
                    break

            if modified:
                if to == 'SOLIDIFY': to = 'NONE'

        del obj

    elif op.operation == 'BEVEL':
        bevel_main = mod_stack.bevel_main
        bevel_quad = mod_stack.bevel_quad
        bevel_front = mod_stack.bevel_front
        weld_main = mod_stack.weld_main
        weld_quad = mod_stack.weld_quad
        weld_front = mod_stack.weld_front
        bevel.sync_bevel_val(op, context)

        op.last['mouse'] = op.mouse['location']

        op.ngon_point_index = -1

        if modified:
            to = 'NONE'
            weld_main.show_viewport = bevel_main.show_viewport
            weld_quad.show_viewport = bevel_quad.show_viewport
            weld_front.show_viewport = bevel_front.show_viewport


    elif op.operation == 'ROTATE':
        op.rotated = True

    elif op.operation == 'SCALE':
        op.scaled = True

    elif op.operation == 'MOVE':
        op.translated = True

    elif op.operation == 'TAPER':
        if to == 'TAPER':
            to = 'NONE'

    rebevel = False
    if op.modified and op.alt_lock:
        op.alt_lock = False

    if to == 'ROTATE':
        op.last['mouse'] = op.mouse['location']
        op.last['local_pivot'] = mesh.pivot(op, context, transform=False)
        op.last['global_pivot'] = bc.shape.matrix_world @ op.last['local_pivot']
        op.last['matrix'] = bc.shape.matrix_world.copy()
        if bc.snap.operator:
            if hasattr(bc.snap.operator, 'grid_handler'):
                bc.snap.operator.grid_handler.draw = True # force snap
                bc.snap.operator.grid_handler.update(context, event)
                op.last['snap_location'] = bc.snap.operator.grid_handler.snap_world.copy()

            else:
                bc.snap.operator.handler.update(context, Vector((event.mouse_region_x, event.mouse_region_y)))
                op.last['snap_location'] = Vector(bc.snap.location)

    if to == 'SCALE':
        op.last['mouse'] = op.mouse['location']
        op.last['local_pivot'] = mesh.pivot(op, context, transform=False)
        op.last['global_pivot'] = bc.shape.matrix_world @ op.last['local_pivot']
        op.last['scale'] = (view3d.location3d_to_location2d(op.last['global_pivot']) - op.last['mouse']).length
        op.last['axis'] = 'XYZ'
        op.last['matrix'] = bc.shape.matrix_world.copy()
        if not deform.show_viewport: deform.show_viewport = True

        array =  mod_stack.array
        op.last['modifier']['displace_vec'] = Vector(array.displacement)
        op.last['modifier']['offset_vec'] = Vector(array.offset)

        if bc.snap.operator:
            if hasattr(bc.snap.operator, 'grid_handler'):
                bc.snap.operator.grid_handler.draw = True # force snap
                bc.snap.operator.grid_handler.update(context, event)
                op.last['snap_location'] = bc.snap.operator.grid_handler.snap_world.copy()

            else:
                bc.snap.operator.handler.update(context, Vector((event.mouse_region_x, event.mouse_region_y)))
                op.last['snap_location'] = Vector(bc.snap.location)

    if to == 'MOVE':
        op.last['location'] = bc.shape.matrix_world @ bc.shape.location
        op.last['view3d_location'] = op.view3d['location']
        op.last['matrix'] = bc.shape.matrix_world.copy()
        op.last['axis'] = 'XY'

    if to == 'BEVEL':
        bc.shape.data.bc.q_beveled = bc.q_bevel
        vert_bevel = bc.shape.data.attributes.get('bevel_weight_vert')
        if not vert_bevel:
            vert_bevel = bc.shape.data.attributes.new('bevel_weight_vert', 'FLOAT', 'POINT')

        op.last['vert_weight'] = [d.value for d in vert_bevel.data]
        #TODO:edge bevel values


    else:
        op.ngon_point_index = -1

    if to != 'MIRROR':
        preference.shape['mirror_gizmo'] = False

    elif preference.shape.mirror_gizmo:
        context.window_manager.gizmo_group_type_ensure("BC_GGT_mirror")
        mod = None

        for m in reversed(bc.shape.modifiers):
            if m.type == 'MIRROR':
                mod = m
                break

        if mod and any(mod.use_axis):
            eval = bc.shape.evaluated_get(context.evaluated_depsgraph_get())

            if not len(eval.data.vertices):
                    bc.shape.modifiers.remove(mod)
                    bc.shape.data.update()

    if to == 'DRAW':
        if dot:
            widget = bc.shader.widgets.active
            loc3d = bc.shape.matrix_world @ op.bounds[op.draw_dot_index] if widget.type == 'DRAW' else widget.transform @ widget.location
            loc2d = view3d.location3d_to_location2d(loc3d)
            op.mouse['offset'] = loc2d - op.mouse['location']
            if widget.type == 'VERT':
                nodes.deform_modal.apply(op, context)
                nodes.deform_modal.deform_method(op, 'Z ONLY')

    else:
        op.mouse['offset'] = Vector((0, 0))

    value = to

    op.operation = value
    toolbar.change_prop(context, 'operation', value)

    if value in {'EXTRUDE', 'OFFSET'}:
        mouse = op.mouse['location']

        bc.plane.matrix_world = bc.shape.matrix_world
        matrix = bc.plane.matrix_world
        inverse = matrix.inverted()

        side_center = deform_center.copy()
        side_center.z = deform_min.z if op.operation =='EXTRUDE' else deform_max.z
        coord = matrix @ side_center

        op.start['intersect'] = inverse @ view3d.location2d_to_location3d(mouse.x, mouse.y, coord)

        op.start['offset'] = deform_max.z
        op.start['extrude'] = deform_min.z
        op.start['matrix'] = bc.shape.matrix_world.copy()
        op.last['bounds_center'] = (Vector(deform.max) + Vector(deform.min)) / 2

    elif value == 'ROTATE':
        op.angle = 0

        op.last['track'] = op.mouse['location'] - view3d.location3d_to_location2d(bc.shape.matrix_world.translation)
        op.last['mouse'] = op.mouse['location']

        bc.axis = 'Z' if bc.axis == 'NONE' else bc.axis

    elif value == 'ARRAY':
        bc.shape.bc.array = True
        array = mod_stack.array
        refresh.input_update_nodes(op, context)
        op.start['displace'] = array.displacement[0]

        if bc.flip:
            bc.flip = False

        axis_index = [bc.shape.bc.array_axis == axis for axis in 'XYZ'].index(True)

        op.last['modifier']['offset'] = array.offset[axis_index]
        op.last['modifier']['count'] = array.count
        op.last['mouse'] = op.mouse['location']
        op.last['view3d_location'] = Vector(op.view3d['location'])

    elif value == 'DISPLACE':
        refresh.input_update_nodes(op, context)
        array = mod_stack.array
        op.start['displace'] = array.displacement[0]
        op.last['mouse'] = op.mouse['location']
        op.last['view3d_location'] = Vector(op.view3d['location'])


    elif value == 'SOLIDIFY':
        bc.shape.bc.solidify = True
        obj = bc.shape if op.mode != 'INSET' else (op.datablock['insets'][-1] if op.datablock['insets'] else None )

        if obj:
            for mod in obj.modifiers:
                if mod.type == 'SOLIDIFY':
                    if op.mode != 'INSET':
                        op.last['modifier']['thickness'] = mod.thickness

                    else:
                        op.last['thickness'] = mod.thickness

                    break

        del obj

        op.last['mouse'] = op.mouse['location']

    elif value == 'BEVEL':
        bevel.sync_bevel_val(op, context)

        op.last['mouse'] = op.mouse['location']

    elif value == 'TAPER':
        op.last['taper'] = preference.shape.taper
        op.last['mouse'] = op.mouse['location']

    if not init:
        if value == 'NONE':
            op.report({'INFO'}, 'Shape Locked')

        else:
            op.report({'INFO'}, '{}{}{}'.format(
                'Added ' if value == 'ARRAY' else '',
                value.title()[:-1 if value in {'MOVE', 'ROTATE', 'SCALE', 'EXTRUDE', 'DISPLACE'} else len(value)],
                'ing' if value not in {'ARRAY', 'GRID'} else ''))

        refresh.shape(op, context, event, dot=dot)

    elif value != 'DRAW':
        refresh.shape(op, context, event)

    if to != 'MOVE':
        op.move_lock = False

