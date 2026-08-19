import bmesh

from mathutils import Matrix, Vector
from .... utility import addon
from .. import data


def shape(op, context, event, report=True):
    if op.workflow_nodes:
        return shape_nodes(op, context, event, report=report)

    return shape_classic(op, context, event, report=report)

def shape_classic(op, context, event, report=True):
    preference = addon.preference()
    bc = context.scene.bc

    bc.shape.data.transform(Matrix.Scale(-1, 4, Vector((0, 0, 1))))

    bm = bmesh.new()
    bm.from_mesh(bc.shape.data)

    bm.faces.ensure_lookup_table()
    #bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)

    if bc.shape.data.bc.q_beveled and (op.shape_type == 'BOX' or (op.shape_type == 'CIRCLE' and addon.preference().shape.circle_type != 'MODIFIER')):
        op.reverse_bevel = True
        indices = op.geo['indices']['bot_face']# if op.flip_z else []
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[index] for index in indices])
    preference.shape.bevel_both = preference.shape.bevel_both

    bm.to_mesh(bc.shape.data)
    bm.free()

    if report:
        op.report({'INFO'}, 'Flipped Shape on Z')


def shape_nodes(op, context, event, report=True):
    preference = addon.preference()
    bc = context.scene.bc

    generate = op.modifier_stack.generate
    clean = op.modifier_stack.clean
    if op.shape_type == 'CUSTOM':
        generate.flip_z = not generate.flip_z

    elif op.shape_type == 'CIRCLE' or bc.shape.data.bc.q_beveled:
        flip_z = not op.reverse_bevel
        op.reverse_bevel = flip_z
        if flip_z:
            generate.flip_face_name = data.FLIP_NAME
            generate.flip_bottom_faces = True
            generate.flip_z = True
            clean.show_viewport = True
            clean.flipped_faces = data.FLIP_NAME

        else:
            generate.flip_face_name = ''
            generate.flip_bottom_faces = False
            generate.flip_z = False
            clean.flipped_faces = ''

    if report:
        op.report({'INFO'}, 'Flipped Shape on Z')
