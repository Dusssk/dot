import bpy
from ...... utility import addon, screen, modifier


def shape(op, context, event):
    if op.workflow_nodes:
        return shape_nodes(op, context, event)
    return shape_classic(op, context, event)

def shape_classic(op, context, event):
    preference = addon.preference()
    bc = context.scene.bc
    snap = preference.snap.enable and preference.snap.incremental

    objects = [bc.shape] if op.mode != 'INSET' else op.datablock['insets']
    targets = op.datablock['targets']
    last = op.last['modifier']['thickness'] if op.mode != 'INSET' else op.last['thickness']

    thickness = (op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True) * 0.001

    if snap and event.ctrl:
        if event.shift and op.prior_to_shift == 'NONE':
            thickness = -round(thickness, 1)

        else:
            thickness = -round(thickness)

    elif event.shift and op.prior_to_shift == 'NONE':
        thickness = (op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True) * 0.0001

    absolute = bpy.app.version > (2, 9) and op.shape_type == 'BOX' and preference.shape.box_grid
    for i, obj in enumerate(objects):
        solidify = None
        for mod in obj.modifiers:
            if mod.type == 'SOLIDIFY':
                solidify = mod

                if op.mode != 'INSET':
                    mod.thickness = last + thickness
                    preference.shape['solidify_thickness'] = mod.thickness
                else:
                    val = last + thickness

                    for tmod in reversed(targets[i].modifiers):
                        if tmod.type != 'BOOLEAN': continue
                        if tmod.object is not obj: continue

                        tmod.operation = 'DIFFERENCE' if val > 0 else 'UNION'
                        break

                    mod.thickness = val
                    preference.shape['inset_thickness'] = mod.thickness

                if event.ctrl:
                    mod.thickness = round(mod.thickness, 2 if event.shift and op.prior_to_shift == 'NONE' else 1)
                else:
                    if op.mode != 'INSET':
                        op.last['modifier']['thickness'] = mod.thickness
                    else:
                        op.last['thickness'] = mod.thickness

                    op.last['mouse'].x = op.mouse['location'].x

                if absolute and op.mode != 'INSET':
                    mod.thickness = abs(mod.thickness)

                break

        if not solidify:
            mod = obj.modifiers.new(name='Solidify', type='SOLIDIFY')
            mod.show_in_editmode = False
            mod.offset = -1 if (op.shape_type != 'NGON' or op.extruded) else 0
            mod.use_even_offset = True
            mod.use_quality_normals = True
            mod.thickness = last

            if op.mode == 'INSET':
                val = last
                for tmod in reversed(targets[i].modifiers):
                    if tmod.type != 'BOOLEAN': continue
                    if tmod.object is not obj: continue

                    tmod.operation = 'DIFFERENCE' if val > 0 else 'UNION'
                    break

                mod.thickness = val
                preference.shape['inset_thickness'] = mod.thickness

            elif absolute:
                mod.thickness = abs(mod.thickness)

            if hasattr(mod, 'solidify_mode') and preference.shape.box_grid and op.shape_type == 'BOX' and not op.ngon_fit:
                mod.solidify_mode = 'NON_MANIFOLD'
                mod.offset = 0

    del objects

def shape_nodes(op, context, event):
    preference = addon.preference()
    bc = context.scene.bc
    snap = preference.snap.enable and preference.snap.incremental

    last = op.last['modifier']['thickness'] if op.mode != 'INSET' else op.last['thickness']

    thickness = (op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True) * 0.001

    if snap and event.ctrl:
        if event.shift and op.prior_to_shift == 'NONE':
            thickness = -round(thickness, 1)

        else:
            thickness = -round(thickness)

    elif event.shift and op.prior_to_shift == 'NONE':
        thickness = (op.mouse['location'].x - op.last['mouse'].x) / screen.dpi_factor(ui_scale=False, integer=True) * 0.0001

    absolute = op.shape_type == 'BOX' and preference.shape.box_grid

    if op.mode == 'INSET':
        if not op.datablock['bevels']:
            for obj in op.datablock['targets'] + op.datablock['slices']:
                for mod in obj.modifiers:
                    mod = modifier.bool_mod_get(mod)
                    if not mod or mod.object != bc.shape: continue

                    mod.inset_thickness = last + thickness
                    preference.shape['inset_thickness'] = mod.inset_thickness

                    if event.ctrl:
                        mod.inset_thickness = round(mod.thickness, 2 if event.shift and op.prior_to_shift == 'NONE' else 1)
                    else:
                        op.last['thickness'] = mod.inset_thickness
                        op.last['mouse'].x = op.mouse['location'].x

                    break

    else:
        solidify = op.modifier_stack.solidify
        if not solidify.show_viewport:
            solidify.show_in_editmode = False
            solidify.offset = -1 if (op.shape_type != 'NGON' or op.extruded) else 0
            solidify.use_even_offset = True
            solidify.use_quality_normals = True
            solidify.thickness = last

            if absolute:
                solidify.thickness = abs(solidify.thickness)

            if preference.shape.box_grid and op.shape_type == 'BOX' and not op.ngon_fit:
                solidify.solidify_mode = 'NON_MANIFOLD'
                solidify.offset = 0

        solidify.thickness = last + thickness

        preference.shape['solidify_thickness'] = solidify.thickness

        if event.ctrl:
            solidify.thickness = round(solidify.thickness, 2 if event.shift and op.prior_to_shift == 'NONE' else 1)
        else:
            op.last['modifier']['thickness'] = solidify.thickness
            op.last['mouse'].x = op.mouse['location'].x

        if absolute:
            solidify.thickness = abs(solidify.thickness)

