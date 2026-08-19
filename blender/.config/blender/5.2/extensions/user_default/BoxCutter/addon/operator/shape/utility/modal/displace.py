import bpy
from mathutils import Vector

from math import radians

# from .... utility import modifier
from .. import modifier
from ...... utility import addon, screen
from .. import nodes

def shape(op, context, event):
    if op.workflow_nodes:
        return shape_nodes(op, context, event)

    return shape_classic(op, context, event)


def shape_classic(op, context, event):
    bc = context.scene.bc
    preference = addon.preference()

    displace = None

    for mod in bc.shape.modifiers:
        if mod.type == 'DISPLACE':
            displace = mod

            break

    if not displace:
        displace = bc.shape.modifiers.new('Displace', 'DISPLACE')
        displace.direction = 'X'
        displace.strength = preference.shape.displace
        displace.mid_level = 0

    location = op.view3d['location'].x - op.last['view3d_location'].x + op.start['displace']

    displace.strength = location

    #XXX: updating tracked states array distance using this intersect_distance
    from .. import tracked_states
    tracked_states.array_distance = abs(location)

    op.last['modifier']['displace'] = displace.strength

    preference.shape['array_distance'] = displace.strength
    preference.shape['displace'] = displace.strength

def shape_nodes(op, context, event):
    bc = context.scene.bc
    preference = addon.preference()
    array: nodes.Array = op.modifier_stack.array

    displace_vec = Vector()
    displace_vec.x = op.view3d['location'].x - op.last['view3d_location'].x + op.start['displace']

    #XXX: updating tracked states array distance using this intersect_distance
    from .. import tracked_states
    tracked_states.array_distance = abs(displace_vec.x)

    op.last['modifier']['displace'] = displace_vec.x

    preference.shape['array_distance'] = displace_vec.x
    preference.shape['displace'] = displace_vec.x
    array.displacement = displace_vec
