import bpy

from .. import modifier
# from .... utility import modifier



# TODO: move shape display here
class shape:


    def boolean(op, display=False):
        bc = bpy.context.scene.bc
        show = op.live if not display else display

        depsgraph = bpy.context.evaluated_depsgraph_get()

        eval_shape = bc.shape.evaluated_get(depsgraph)
        original_active = bpy.context.view_layer.objects.active

        if eval_shape.dimensions[2] > 0.001:
            for obj in op.datablock['targets']:
                if not op.workflow_nodes and op.mode == 'INSET':
                    for mod in reversed(obj.modifiers):
                        mod_object = modifier.bool_object_get(mod)
                        if mod_object and mod_object.bc.inset:
                            shown = mod.show_viewport
                            mod.show_viewport = show

                            if show and not shown:
                                bc.shape.hide_set(False)
                                bpy.context.view_layer.objects.active = bc.shape
                                bc.shape.select_set(True)

                                bc.shape.hide_set(True)
                                bc.shape.select_set(False)

                                bpy.context.view_layer.objects.active = original_active

                            break

                mod = modifier.shape_bool(obj)
                if mod:
                    mod.show_viewport = show if op.workflow_nodes or op.mode != 'INSET' else False

            for obj in op.datablock['slices']:
                mod = modifier.shape_bool(obj)
                if mod:
                    mod.show_viewport = show

        else:
            for obj in op.datablock['targets']:
                if op.mode == 'INSET':
                    for mod in reversed(obj.modifiers):
                        mod_object = modifier.bool_object_get(mod)
                        if mod_object and mod_object.bc.inset:
                            mod.show_viewport = False
                            break

                if modifier.shape_bool(obj):
                    modifier.shape_bool(obj).show_viewport = False

            for obj in op.datablock['slices']:
                if modifier.shape_bool(obj):
                    modifier.shape_bool(obj).show_viewport = False
