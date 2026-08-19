import bpy

from math import radians
from mathutils import Vector

from .. import mesh, nodes, data
from ...... utility import addon, screen, modifier

VERT_NAME = 'bevel_weight_vert'
MAIN_NAME = 'bevel_weight_edge'
QUAD_NAME = 'bevel_weight_edge_quad'
FRONT_NAME = 'bevel_weight_edge_front'
DEF_SEGMENTS = 2
DEF_WIDTH = 0.02

rounded = lambda n: round(n, 8)

# XXX: bevel before array
def shape(op, context, event):
    if op.workflow_nodes:
        return shape_nodes(op, context, event)

    return shape_classic(op, context, event)

def shape_classic(op, context, event):
    from .. import dimensions

    preference = addon.preference()
    bc = context.scene.bc

    if bc.shape.data.bc.inset_bevel:
        segment_state = False
        update = True

        mod = None
        for m in bc.bevel.modifiers:
            if m.type == 'BEVEL':
                mod = m
                break

        # snap = preference.snap.enable and preference.snap.incremental

        # max_dimension = max(bc.lattice.dimensions[:-1])
        max_dimension = max(dimensions()[:-1])
        clamped = False
        clamp_offset = clamp(op)

        width_input = ((op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True)) * max_dimension
        factor = 0.0001 / max_dimension if event and event.shift else 0.001 / max_dimension

        _input = lambda n: rounded(n + width_input * factor)
        last = op.last['thickness']
        width = (_input(last) if last < clamp_offset else _input(clamp_offset))

        if width < 0.0004:
            width = 0.0004

        if width >= clamp_offset:
            clamped = True
            width = clamp_offset
            update = False

        # if snap and event and event.ctrl:
        #     width = round(width, 2 if event and event.shift else 1) # and op.prior_to_shift == 'NONE' else 1)

        if not clamped:
            if width < 0.001 and not op.width_state or segment_state:
                segment_state = True
                op.width_state = True

                if mod.segments == 1 and op.segment_state:
                    mod.segments = preference.shape.bevel_segments if preference.shape.bevel_segments != 1 else preference.shape.bevel_segments_default

                else:
                    op.segment_state = True
                    mod.segments = 1

            elif width > 0.0011 and op.width_state:
                op.width_state = False

        # if update:
        #     op.last['thickness'] = width
        #     preference.shape[width_type] = width

        # mod.width = width
        preference.shape.inset_thickness = width

        op.last['mouse'] = op.mouse['location']
        return

    # TODO: lasso bevel support
    if (op.shape_type == 'NGON' or op.ngon_fit) and preference.shape.lasso:
        return

    ngon = op.shape_type == 'NGON' or op.ngon_fit
    boxgon = op.shape_type == 'BOX' and not op.ngon_fit and (op.ngon_point_index != -1 or op.ngon_point_bevel)

    snap = preference.snap.enable and preference.snap.incremental

    straight_edge = preference.shape.straight_edges or bc.q_back_only

    # max_dimension = max(bc.lattice.dimensions[:-1])
    max_dimension = max(dimensions()[:-1])
    clamped = False

    clamp_offset = clamp(op)

    width_input = ((op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True)) * max_dimension
    factor = 0.0001 if event and event.shift and op.prior_to_shift == 'NONE' else 0.001

    if op.shape_type == 'CIRCLE' and preference.shape.circle_type == 'POLYGON' and preference.shape.circle_vertices > preference.shape.circle_bevel_threshold:
        bc['q_bevel'] = bc.shape.data.bc.q_beveled = True
        bc.q_back_only = False
        op.geo['indices']['mid_edge'] = []

    if preference.shape.quad_bevel:
        if not straight_edge or op.shape_type == 'CIRCLE' or bc.q_back_only:
            mesh.bevel_weight(op, context, event)

        else:
            mesh.vertex_group(op, context, event)
    else:
        mesh.bevel_weight(op, context, event)

    m = None
    for mod in bc.shape.modifiers:
        if mod.type == 'BEVEL':
            m = mod
            break

    if not m:
        for mod in modifier.collect(bc.shape, types={'WELD', 'VERTEX_WEIGHT_EDIT', 'VERTEX_WEIGHT_MIX'}):
            bc.shape.modifiers.remove(mod)

        vertex_only = ngon and not op.extruded
        quad_bevel = not preference.shape.quad_bevel or (preference.shape.quad_bevel and not straight_edge)

        if vertex_only:
            mod = bc.shape.modifiers.new(name='Bevel', type='BEVEL')
            mod.show_render = False
            mod.show_expanded = False

            if bpy.app.version[:2] < (2, 90):
                mod.use_only_vertices = True

            else:
                mod.affect = 'VERTICES'

            mod.width = op.last['modifier']['bevel_width'] if not ngon and not boxgon else clamp_offset
            mod.segments = preference.shape.bevel_segments
            mod.limit_method = 'WEIGHT'
            mod.offset_type = 'OFFSET'

            if bpy.app.version[:2] < (3, 4):
                bc.shape.data.use_customdata_vertex_bevel = True

            for v in bc.shape.data.vertices:
                value = mesh.index_weight(v.index, vert=True)
                mesh.index_weight(v.index, vert=True, value=value if op.ngon_point_bevel else 1)

            mod = bc.shape.modifiers.new(name='Bevel Weld', type='WELD')
            mod.show_render = False
            mod.show_expanded = False
            # mod.merge_threshold = max(bc.lattice.dimensions) * 0.001
            mod.merge_threshold = max(dimensions()) * 0.001

            modifier.sort(bc.shape, types=['LATTICE', 'BEVEL'], first=True, typed_order=True)

        elif quad_bevel or (op.shape_type == 'CIRCLE' and preference.shape.circle_type == 'MODIFIER'):
            mod = bc.shape.modifiers.new(name='Bevel', type='BEVEL')

            mod.show_render = False
            mod.show_expanded = False

            mod.width = op.last['modifier']['bevel_width'] if not ngon and not boxgon else clamp_offset

            mod.segments = preference.shape.bevel_segments
            mod.limit_method = 'WEIGHT'
            mod.offset_type = 'OFFSET'

            # if op.mode in {'MAKE', 'JOIN'} and (op.shape_type == 'BOX' and not op.ngon_fit):
            #     mesh.mesh.recalc_normals(bc.shape, face=True, index=4, inside=True)

            mod = bc.shape.modifiers.new(name='Bevel Weld', type='WELD')
            mod.show_render = False
            mod.show_expanded = False
            # mod.merge_threshold = max(bc.lattice.dimensions) * 0.001
            mod.merge_threshold = max(dimensions()) * 0.001

            if (op.shape_type == 'NGON' or op.ngon_fit) and preference.shape.ngon_type != 'FACE':
                modifier.sort(bc.shape, types=['LATTICE', 'BEVEL'], first=True, typed_order=True)

        vertex_groups = bc.shape.vertex_groups if not straight_edge else reversed(bc.shape.vertex_groups)
        front_bevel = bc.bevel_front_face and (bc.q_bevel and not bc.q_back_only and op.geo['indices']['top_face']) and vertex_groups

        if not front_bevel or preference.shape.bevel_both:
            for group in vertex_groups:
                mod = bc.shape.modifiers.new(name=group.name, type='VERTEX_WEIGHT_EDIT')
                mod.vertex_group = group.name
                mod.use_remove = True
                mod.remove_threshold = 0.99

                mod = bc.shape.modifiers.new(name='Quad Bevel', type='BEVEL')
                mod.show_viewport = op.extruded
                mod.show_expanded = False

                mod.width = op.last['modifier']['quad_bevel_width']
                mod.segments = preference.shape.quad_bevel_segments
                mod.limit_method = 'VGROUP'
                mod.vertex_group = group.name
                mod.offset_type = 'OFFSET'
                mod.use_clamp_overlap = True if ngon or boxgon else False

                if mod.vertex_group == 'bottom' and not straight_edge:
                    mod.offset_type = 'WIDTH'

                if width_input > clamp(op):
                    mod.width = clamp_offset

                mod = bc.shape.modifiers.new(name='Quad Bevel Weld', type='WELD')
                mod.show_render = False
                mod.show_expanded = False
                # mod.merge_threshold = max(bc.lattice.dimensions) * 0.001
                mod.merge_threshold = max(dimensions()) * 0.001

        if front_bevel:
            mesh.mesh.recalc_normals(bc.shape, face_indices=op.geo['indices']['top_face'], inside=not op.inverted_extrude)

            mod = bc.shape.modifiers.new(name='Vgroup', type='VERTEX_WEIGHT_MIX')
            mod.vertex_group_a = 'bottom'
            mod.vertex_group_b = 'bottom'
            mod.mix_mode = 'ADD'

            mod = bc.shape.modifiers.new(name='Front Bevel', type='BEVEL')
            mod.show_viewport = op.extruded
            mod.show_expanded = False

            mod.width = op.last['modifier']['front_bevel_width']
            mod.segments = preference.shape.front_bevel_segments
            mod.limit_method = 'VGROUP'
            mod.vertex_group = 'bottom'
            mod.invert_vertex_group = True
            mod.offset_type = 'WIDTH'
            mod.angle_limit = radians(50)

            if width_input > clamp(op):
                mod.width = clamp_offset

            mod = bc.shape.modifiers.new(name='Front Bevel Weld', type='WELD')
            mod.show_render = False
            mod.show_expanded = False
            # mod.merge_threshold = max(bc.lattice.dimensions) * 0.001
            mod.merge_threshold = max(dimensions()) * 0.001

        elif not bc.q_bevel:
            mesh.mesh.recalc_normals(bc.shape, inside=op.inverted_extrude)

        modifier.sort(bc.shape, types=['LATTICE', 'MIRROR'], first=True, typed_order=True)

        if preference.shape.ngon_type != 'FACE':
            modifier.sort(bc.shape, types=['SOLIDIFY', 'SCREW'], last=True)

        else:
            modifier.sort(bc.shape, types=['VERTEX_WEIGHT_EDIT', 'VERTEX_WEIGHT_MIX', 'BEVEL', 'WELD'])

        return

    if ngon or boxgon:
        factor = 0.005 / max_dimension

        shape = mesh.eval_shape(bpy.context)
        for index, vindex in enumerate(op.geo['indices']['offset'] if not op.inverted_extrude else op.geo['indices']['extrusion']):
            vert = bc.shape.data.vertices[vindex]

            if op.ngon_point_index == -1:

                segment_state = False
                for mod in bc.shape.modifiers:
                    if mod.type != 'BEVEL':
                        continue

                    if not mesh.index_weight(vert.index, vert=True):
                        continue

                    weighted_width = op.last['vert_weight'][index] + width_input * factor
                    if weighted_width != 0.0 and weighted_width <= 0.0001 and not op.width_state or segment_state:
                        segment_state = True
                        op.width_state = True

                        if mod.segments == 1 and op.segment_state:
                            mod.segments = preference.shape.bevel_segments if preference.shape.bevel_segments != 1 else preference.shape.bevel_segments_default

                        else:
                            op.segment_state = True
                            mod.segments = 1

                    elif weighted_width > 0.0011 and op.width_state:
                        op.width_state = False

            if vert.index == op.ngon_point_index or op.ngon_point_index == -1:

                mesh.index_weight(index, vert=True, value=op.last['vert_weight'][index] + width_input * factor)

                # update = True
                for eindex in op.geo['indices']['top_edge']:
                    edge = bc.shape.data.edges[eindex]

                    if vert.index not in edge.vertices:
                        continue

                    vert1 = shape.vertices[edge.vertices[0]]
                    vert2 = shape.vertices[edge.vertices[1]]

                    weight = 0
                    if vert.index != vert1.index:
                        weight = mesh.index_weight(vert1.index, vert=True)

                    if vert.index != vert2.index:
                        weight = mesh.index_weight(vert2.index, vert=True)

                    length = (vert1.co - vert2.co).length

                    if op.ngon_point_index != -1:
                        length = length - (length * weight)

                    vert_weight = mesh.index_weight(vert.index, vert=True)

                    # if clamp_offset * vert_weight > length:
                    #   update = False
                    #   continue

                    if op.ngon_point_index == -1 and not vert_weight:
                        op.last['vert_weight'][index] = preference.shape.bevel_width - (clamp_offset * vert_weight)

                # if update:
                mesh.index_weight(vindex, vert=True, value=op.last['vert_weight'][index] + width_input * factor)

                for eindex in op.geo['indices']['mid_edge']:
                    edge = bc.shape.data.edges[eindex]

                    if vert.index not in edge.vertices:
                        continue

                    value = mesh.index_weight(vert.index, vert=True)
                    mesh.index_weight(eindex, value=value)
                    mesh.index_weight(edge.vertices[0], vert=True, value=value)
                    mesh.index_weight(edge.vertices[1], vert=True, value=value)

        if not preference.shape.quad_bevel and op.extruded and op.ngon_point_index == -1 and bc.q_bevel:
            if not op.last['edge_weight']:
                op.last['edge_weight'] = [mesh.index_weight(edge.index) for edge in bc.shape.data.edges]

            for index in op.geo['indices']['bot_edge']:
                edge = bc.shape.data.edges[index]

                mesh.index_weight(edge.index, value=op.last['edge_weight'][index] + width_input * factor)

        op.last['bevel_width'] = clamp_offset

        if preference.shape.ngon_type == 'LINE':
            edge_ids = op.geo['indices']['mid_edge']

            if  len(op.geo['indices']['mid_edge']) > 2:
                for i in (0, -1):
                    mesh.index_weight(edge_ids[i], vert=False, value=0.0)
                    edge = bc.shape.data.edges[edge_ids[i]]
                    mesh.index_weight(edge.vertices[0], vert=True, value=0.0)
                    mesh.index_weight(edge.vertices[1], vert=True, value=0.0)

        return

    segment_state = False
    update = True
    for mod in bc.shape.modifiers:
        if mod.type == 'BEVEL':
            width_type = 'bevel_width' if mod.name.startswith('Bevel') else F'{mod.name.split(" ")[0].lower()}_bevel_width'

            _input = lambda n: rounded(n + width_input * factor)
            last = op.last['modifier'][width_type]
            width = (_input(last) if last < clamp_offset else _input(clamp_offset))

            if width < 0.0004:
                width = 0.0004

            if width >= clamp_offset:
                clamped = True
                width = clamp_offset
                update = False

            if snap and event and event.ctrl:
                width = round(width, 2 if event and event.shift and op.prior_to_shift == 'NONE' else 1)

            if not clamped:
                if width < 0.001 and not op.width_state or segment_state:
                    segment_state = True
                    op.width_state = True

                    if mod.segments == 1 and op.segment_state:
                        mod.segments = preference.shape.bevel_segments if preference.shape.bevel_segments != 1 else preference.shape.bevel_segments_default

                    else:
                        op.segment_state = True
                        mod.segments = 1

                elif width > 0.0011 and op.width_state:
                    op.width_state = False

            if update:
                op.last['modifier'][width_type] = width
                preference.shape[width_type] = width

            mod.width = width

    op.last['mouse'] = op.mouse['location']


def shape_nodes(op, context, event):

    preference = addon.preference()
    bc = context.scene.bc
    modifier_stack = op.modifier_stack
    generate: nodes.Generate = modifier_stack.generate
    deform: nodes.Deform = modifier_stack.deform
    bevel_main = modifier_stack.bevel_main #main
    bevel_quad = modifier_stack.bevel_quad
    bevel_front = modifier_stack.bevel_front
    weld_main = modifier_stack.weld_main
    weld_quad = modifier_stack.weld_quad
    weld_front = modifier_stack.weld_front

    dmin = Vector(deform.min)
    dmax = Vector(deform.max)

    dimensions = dmax - dmin

    for i in range(3):
        dimensions[i] = abs(dimensions[i])


    # inset bevel
    # TODO: make compatible with shape bevel?
    if op.datablock['bevels']:

        max_dimension = max(dimensions()[:-1])
        width_input = ((op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True)) * max_dimension
        factor = 0.0001 / max_dimension if event and event.shift else 0.001 / max_dimension

        _input = lambda n: rounded(n + width_input * factor)
        last = op.last['thickness']
        width = _input(last)

        for obj in op.datablock['bevels']:
            for mod in obj.modifiers:
                if mod.type == 'BEVEL':
                    mod.width = width
                    mod.segments = preference.shape.bevel_segments

                    preference.shape['inset_thickness'] = mod.width

                    op.last['thickness'] = mod.width

                    break

        op.last['mouse'] = op.mouse['location']
        return

    # TODO: lasso bevel support
    if (op.shape_type == 'NGON' or op.ngon_fit) and preference.shape.lasso:
        return

    ngon = op.shape_type == 'NGON' or op.ngon_fit
    boxgon = op.shape_type == 'BOX' and not op.ngon_fit and (op.ngon_point_index != -1 or op.ngon_point_bevel)

    snap = preference.snap.enable and preference.snap.incremental
    front_bevel = bc.bevel_front_face and (bc.q_bevel and not bc.q_back_only)
    back_bevel = bc.q_bevel

    if preference.shape.bevel_both:
        front_bevel = back_bevel = True

    straight_edge = preference.shape.straight_edges or bc.q_back_only
    point_bevel = op.ngon_point_index > -1
    is_quad_bevel = preference.shape.quad_bevel

    # max_dimension = max(bc.lattice.dimensions[:-1])
    max_dimension = max(dimensions[:-1])

    delta_input = 0.0
    if event:
        width_input = ((op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True)) * max_dimension
        op.last['mouse'] = op.mouse['location']
        factor = 0.0001 if event and event.shift and op.prior_to_shift == 'NONE' else 0.001
        delta_input = width_input * factor


    if op.shape_type in {'BOX', 'NGON'}:
        vertex_bevel = attr_layer_get(bc.shape.data, VERT_NAME, 'FLOAT', 'POINT')
        value = delta_input
        max_weight = 0
        if not bevel_main.show_viewport:

            generate.vertex_bevel = VERT_NAME
            generate.mid_edges_float = MAIN_NAME
            bevel_main.limit_method = 'WEIGHT'
            bevel_main.edge_weight = MAIN_NAME
            bevel_main.width = 1.0
            bevel_main.segments = preference.shape.bevel_segments
            bevel_main.show_viewport = True
            weld_main.show_viewport = True
            default = 0 if point_bevel else preference.shape.bevel_width
            max_weight = default
            for v in vertex_bevel.data: v.value = default

        else:
            if point_bevel:
                attr = vertex_bevel.data[op.ngon_point_index]
                new_val = attr.value + value
                if new_val < 0: new_val = 0
                attr.value = new_val

                if new_val > max_weight: max_weight = new_val
                preference.shape['bevel_width']
                op.last['modifier']['bevel_width'] = max_weight
                return

            else:
                for v in vertex_bevel.data:
                    new_val = v.value + value
                    if new_val < 0: new_val = 0
                    v.value = new_val
                    if new_val > max_weight: max_weight = new_val

        op.last['modifier']['bevel_width'] = max_weight
        preference.shape['bevel_width'] = max_weight

        if not is_quad_bevel:
            # cync to main bevel
            op.last['modifier']['quad_bevel_width'] = max_weight
            op.last['modifier']['front_bevel_width'] = max_weight
            preference.shape['quad_bevel_width'] = max_weight
            preference.shape['front_bevel_width'] = max_weight
            weld_front.show_viewport = False
            weld_quad.show_viewport = False

            if back_bevel:
                generate.bot_edges_float = MAIN_NAME
                generate.bot_edges_float_val = max_weight

            else:
                generate.bot_edges_float = ''

            if front_bevel:
                generate.top_edges_float = MAIN_NAME
                generate.top_edges_float_val = max_weight

            else:
                generate.top_edges_float  = ''

            return


        if back_bevel:
            if not bevel_quad.show_viewport:
                bevel_quad.show_viewport = True
                bevel_quad.edge_weight = QUAD_NAME
                bevel_quad.width = preference.shape.bevel_width
                bevel_quad.segments = preference.shape.quad_bevel_segments
                weld_quad.show_viewport = True
                generate.bot_edges_float_val = 1.0
                generate.bot_edges_float = QUAD_NAME

            bevel_quad.width += delta_input
            op.last['modifier']['quad_bevel_width'] = bevel_quad.width
            preference.shape['quad_bevel_width'] = bevel_quad.width

        else:
            generate.bot_edges_float = ''
            bevel_quad.show_viewport = False
            weld_quad.show_viewport = False

        if front_bevel:
            if not bevel_front.show_viewport:
                bevel_front.show_viewport = True
                bevel_front.edge_weight = FRONT_NAME
                bevel_front.width = preference.shape.front_bevel_width
                bevel_front.segments = preference.shape.front_bevel_segments
                weld_front.show_viewport = True
                generate.top_edges_float = FRONT_NAME
                generate.top_edges_float_val = 1.0

            bevel_front.width += delta_input
            op.last['modifier']['front_bevel_width'] = bevel_quad.width
            preference.shape['front_bevel_width'] = bevel_quad.width

        else:
            generate.top_edges_float = ''
            bevel_front.show_viewport = False
            weld_front.show_viewport = False

    elif op.shape_type == 'CIRCLE':
        circle_back_bevel = True
        main_bevel = False

        if preference.shape.circle_type == 'STAR' or preference.shape.circle_vertices < preference.shape.circle_bevel_threshold:
            main_bevel = True
            circle_back_bevel = back_bevel

        if circle_back_bevel:
            if not bevel_quad.show_viewport:
                bevel_quad.show_viewport = True
                bevel_quad.edge_weight = QUAD_NAME
                bevel_quad.segments = preference.shape.quad_bevel_segments
                bevel_quad.width = preference.shape.quad_bevel_width
                weld_quad.show_viewport = True
                generate.bot_edges_float = QUAD_NAME
                generate.bot_edges_float_val = 1.0

            bevel_quad.width += delta_input
            op.last['modifier']['quad_bevel_width'] = bevel_quad.width
            preference.shape['quad_bevel_width'] = bevel_quad.width

        else:
            generate.bot_edges_float = ''
            bevel_quad.show_viewport = False
            weld_quad.show_viewport = False

        if front_bevel:
            if not bevel_front.show_viewport:
                bevel_front.show_viewport = True
                bevel_front.edge_weight = FRONT_NAME
                bevel_front.width = preference.shape.front_bevel_width
                weld_front.show_viewport = True
                generate.top_edges_float_val = 1.0
                generate.top_edges_float = FRONT_NAME

            bevel_front.width += delta_input
            op.last['modifier']['front_bevel_width'] = bevel_quad.width
            preference.shape['front_bevel_width'] = bevel_quad.width

        else:
            generate.top_edges_float = ''
            bevel_front.show_viewport = False
            weld_front.show_viewport = False

        if main_bevel:
            if not bevel_main.show_viewport:
                bevel_main.show_viewport = True
                bevel_main.edge_weight = MAIN_NAME
                bevel_main.segments = preference.shape.bevel_segments
                bevel_main.width = preference.shape.bevel_width
                weld_main.show_viewport = True
                generate.mid_edges_float = MAIN_NAME
                generate.mid_edges_float_val = 1.0

            bevel_main.width += delta_input
            op.last['modifier']['bevel_width'] = bevel_main.width
            preference.shape['bevel_width'] = bevel_main.width

        else:
            generate.mid_edges_float = ''
            bevel_main.show_viewport = False
            weld_main.show_viewport = False


def attr_layer_get(mesh, name:str, type:str, domain:str):
    '''Get or create attribute'''
    attr = mesh.attributes.get(name)

    if not attr:
        attr = mesh.attributes.new(name, type, domain)

    return attr


def clamp(op, q = False):
    from .. import bound_box, dimensions
    preference = addon.preference()
    bc = bpy.context.scene.bc

    offset = 0.0025 if bpy.app.version[:2] < (2, 82) else 0

    taper = preference.shape.taper

    ngon = op.shape_type == 'NGON' or op.ngon_fit
    boxgon = op.shape_type == 'BOX' and not op.ngon_fit and (op.ngon_point_index != -1 or op.ngon_point_bevel)
    if (ngon or boxgon) and not preference.shape.lasso and not q:
        dist = 0
        shape = mesh.eval_shape(bpy.context)
        indices = {i for i in range(len(shape.edges))}
        for index in op.geo['indices']['top_edge']:
            if index not in indices:
                continue

            edge = shape.edges[index]

            vert1 = shape.vertices[edge.vertices[0]]
            vert2 = shape.vertices[edge.vertices[1]]

            length = (vert1.co - vert2.co).length

            if length > dist:
                dist = length

        return dist * taper - offset

    bb = bound_box()
    vector1 = Vector(bb[0][:])
    vector2 = Vector(bb[1][:])
    vector3 = Vector(bb[5][:])
    vector4 = Vector(bb[6][:])

    distances = [vector4 - vector3, vector3 - vector2]

    if op.shape_type == 'CIRCLE' and not preference.shape.circle_type == 'STAR':
        z_height = dimensions()[2]

        if not op.flip_z and max(min(distances)) * 0.5 <= z_height:
            return max(min(distances)) * 0.7037037037037 * taper - offset

        return z_height * 1.42105263 * taper - offset

    if not offset:
        offset = -max(min(distances)) * 0.01

    if q: distances.append((vector2 - vector1) * 2.7037037037037)

    return max(min(distances)) * 0.5 * taper - offset


def clamp_and_visual_weight(op, bc, pref, clamp, set=True):
    prev = op.last['modifier']['bevel_width']

    vindices = op.geo['indices']['offset'] if not op.inverted_extrude else op.geo['indices']['extrusion']
    eindices = op.geo['indices']['mid_edge']

    for index, vindex in enumerate(vindices):
        vert = bc.shape.data.vertices[vindex]

        if op.last['modifier']['bevel_width'] > clamp:
            op.last['modifier']['bevel_width'] = clamp

        if mesh.index_weight(vert.index, vert=True) == 1.0:
            mesh.index_weight(vert.index, vert=True, value=clamp * (prev / 100) * 100)

        elif set:
            mesh.index_weight(vert.index, vert=True, value=pref.shape.bevel_width * (clamp / 100) * 100)

        # if vert.index == op.ngon_point_index:

        op.last['vert_weight'][index] = mesh.index_weight(vindex, vert=True)

        for eindex in eindices:
            edge = bc.shape.data.edges[eindex]

            if vert.index not in edge.vertices:
                continue

            mesh.index_weight(edge.index, value=mesh.index_weight(vert.index, vert=True))

def sync_bevel_val(op, context):
    preference = addon.preference()
    bc = context.scene.bc
    mod_stack:data.ModifierStack = op.modifier_stack
    bevel_main = mod_stack.bevel_main
    bevel_quad = mod_stack.bevel_quad
    bevel_front = mod_stack.bevel_front
    deform = mod_stack.deform
    dmin = Vector(deform.min)
    dmax = Vector(deform.max)

    dims = dmax - dmin

    max_dim = 0
    for f in dims:
        f = abs(f)
        if f > max_dim:
            max_dim = f

    if max_dim < data.MIN_DIM: return

    bevel_max = max_dim * 0.55

    op.last['modifier']['use_clamp_overlap'] = bevel_main.use_clamp_overlap


    if op.shape_type in {'BOX', 'NGON'}:
        # main
        vert_weight = attr_layer_get(bc.shape.data, VERT_NAME, 'FLOAT', 'POINT')
        max_val = 0
        for w in vert_weight.data:
            value = w.value
            if value > bevel_max:
                value = bevel_max
                w.value = value

            if value > max_val: max_val = value

        if preference.shape.bevel_width > bevel_max: preference.shape['bevel_width'] = bevel_max

        if bevel_main.show_viewport:
            preference.shape['bevel_width'] = max_val
            preference.shape['bevel_segments'] = bevel_main.segments
            op.last['modifier']['bevel_width'] = max_val

        # Z-
        if bevel_quad.width > bevel_max:bevel_quad.width = bevel_max
        if preference.shape.quad_bevel_width > bevel_max: preference.shape['quad_bevel_width'] = bevel_max

        if bevel_quad.show_viewport:
            preference.shape['quad_bevel_segments'] = bevel_quad.segments
            preference.shape['quad_bevel_width'] = bevel_quad.width
            op.last['modifier']['quad_bevel_width'] = bevel_quad.width

        # Z+
        if bevel_front.width > bevel_max:bevel_front.width = bevel_max
        if preference.shape.front_bevel_width > bevel_max: preference.shape['front_bevel_width'] = bevel_max

        if bevel_front.show_viewport:
            preference.shape['front_bevel_segments'] = bevel_front.segments
            preference.shape['front_bevel_width'] = bevel_front.width
            op.last['modifier']['front_bevel_width'] = bevel_front.width


    elif op.shape_type == 'CIRCLE':

        if bevel_main.width > bevel_max:bevel_main.width = bevel_max
        if preference.shape.bevel_width > bevel_max: preference.shape['bevel_width'] = bevel_max

        if bevel_main.show_viewport:
            preference.shape['bevel_segments'] = bevel_main.segments
            preference.shape['bevel_width'] = bevel_main.width
            op.last['modifier']['bevel_width'] = bevel_main.width

        # Z-
        if bevel_quad.width > bevel_max:bevel_quad.width = bevel_max
        if preference.shape.quad_bevel_width > bevel_max: preference.shape['quad_bevel_width'] = bevel_max

        if bevel_quad.show_viewport:
            preference.shape['quad_bevel_segments'] = bevel_quad.segments
            preference.shape['quad_bevel_width'] = bevel_quad.width
            op.last['modifier']['quad_bevel_width'] = bevel_quad.width

        # Z+
        if bevel_front.width > bevel_max:bevel_front.width = bevel_max
        if preference.shape.front_bevel_width > bevel_max: preference.shape['front_bevel_width'] = bevel_max

        if bevel_front.show_viewport:
            if bevel_front.width > bevel_max:bevel_front.width = bevel_max
            preference.shape['front_bevel_segments'] = bevel_front.segments
            preference.shape['front_bevel_width'] = bevel_front.width
            op.last['modifier']['front_bevel_width'] = bevel_front.width

def reset_nodes(op, context):
    preference = addon.preference()
    bc = context.scene.bc
    modifier_stack = op.modifier_stack
    generate: nodes.Generate = modifier_stack.generate
    bevel_main = modifier_stack.bevel_main #main
    bevel_quad = modifier_stack.bevel_quad
    bevel_front = modifier_stack.bevel_front

    if op.shape_type in {'BOX', 'NGON'}:
        # main
        vert_weight = attr_layer_get(bc.shape.data, VERT_NAME, 'FLOAT', 'POINT')
        max_val = 0
        for w in vert_weight.data:
            w.value = DEF_WIDTH

    else:
        bevel_main.width = DEF_WIDTH

    bevel_front.width = DEF_WIDTH
    bevel_quad.width = DEF_WIDTH
    bevel_main.segments = DEF_SEGMENTS
    bevel_quad.segments = DEF_SEGMENTS
    bevel_front.segments = DEF_SEGMENTS

    generate.bot_edges_float_val = 1
    generate.mid_edges_float_val = 1
    generate.top_edges_float_val = 1


    preference.shape['bevel_segments'] = DEF_SEGMENTS
    preference.shape['bevel_width'] = DEF_WIDTH
    preference.shape['quad_bevel_segments'] = DEF_SEGMENTS
    preference.shape['quad_bevel_width'] = DEF_WIDTH
    preference.shape['front_bevel_segments'] = DEF_SEGMENTS
    preference.shape['front_bevel_width'] = DEF_WIDTH