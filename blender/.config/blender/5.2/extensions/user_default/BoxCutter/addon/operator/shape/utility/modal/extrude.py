from .. import mesh, lattice, nodes


def shape(op, context, event, extrude_only=False):
    if op.workflow_nodes:
        return shape_nodes(op, context, event, extrude_only)

    return shape_classic(op, context, event, extrude_only)

def shape_classic(op, context, event, extrude_only=False):
    bc = context.scene.bc

    if op.shape_type == 'NGON':
        mesh.extrude(op, context, event, extrude_only=extrude_only)

    lattice.extrude(op, context, event)

    for mod in bc.shape.modifiers:
        if mod.type != 'BEVEL' or mod.show_viewport:
            continue

        mod.show_viewport = True

def shape_nodes(op, context, event, extrude_only=False):

    nodes.deform_modal.extrude(op, context, event)
