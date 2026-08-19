# from ..... import toolbar
# from ... import shape as _shape
from .. import mesh, lattice, nodes


def shape(op, context, event):
    if op.workflow_nodes:
        return shape_nodes(op, context, event)

    return shape_classic(op, context, event)

def shape_classic(op, context, event):
    ngon = op.shape_type == 'NGON'

    op.custom_offset = True

    if op.shape_type == 'NGON':
        if not op.extruded:
            mesh.extrude(op, context, event)

    if not ngon:
        lattice.offset(op, context, event)
    else:
        mesh.offset(op, context, event)

def shape_nodes(op, context, event):
    ngon = op.shape_type == 'NGON'

    op.custom_offset = True

    nodes.deform_modal.offset(op, context, event)
