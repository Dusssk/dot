
import bpy
from ... utility import geometry_nodes, ct_modifier, addon

FILTER_PROP = {
    'debug_options',
    'execution_time',
    'is_override_data',
    'persistent_uid',
    'rna_type',
    'type',
    'use_pin_to_last'
}

# map default type to node group wrapper constructor
TYPE_MAP = {'BOOLEAN': geometry_nodes.NodeBoolean.from_object}

class HOPS_OT_Nodyify(bpy.types.Operator):
    bl_idname = 'hops.nodify'
    bl_label = 'Hops Nodify'
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = '''Replace default modifiers with supported node implementations\n
Shift - Replace supported node groups with current version'''

    replace = False
    @classmethod
    def poll(cls, context):
        return addon.preference().property.workflow_modifier == 'NODES'

    def invoke(self, context, event):
        self.replace = event.shift

        return self.execute(context)


    def execute(self, context):
        supported_types = {'MESH'}
        objects = [o for o in context.selected_objects if o.type in supported_types]
        self.notify = lambda val: bpy.ops.hops.display_notification(info=val) if addon.preference().ui.Hops_extra_info else lambda val: None

        counter = 0

        type_func = {'BOOLEAN': geometry_nodes.NodeBoolean.get_or_load_node_group}

        if self.replace:
            type_mods = {'BOOLEAN': []}
            for obj in objects:
                for mod in obj.modifiers:
                    if mod.type != 'NODES': continue
                    if not mod.node_group: continue

                    if geometry_nodes.NodeBoolean.is_asset_node_group(mod.node_group):
                        if not geometry_nodes.NodeBoolean.is_valid_node_group(mod.node_group):
                            type_mods['BOOLEAN'].append(mod)
                            counter += 1

            for key, mods in type_mods.items():
                if not mods: continue

                fn = type_func[key]
                node_group  = fn()
                node_group.is_modifier = False # keep modifier dropdown clean
                node_group.asset_clear() # match ops behavior
                for mod in mods:
                    mod.node_group = node_group


            self.notify(F'Modifiers Reloaded: {counter}')

            return {'FINISHED'}

        for obj in objects:
            mod_types = []
            # BOOLEANS
            mod_types.append(('BOOLEAN', [m for m in obj.modifiers if m.type == 'BOOLEAN']))

            for t, mods in mod_types:
                wrapper_fn = TYPE_MAP[t]

                for mod in mods:
                    nodes = wrapper_fn(obj)

                    for prop in mod.bl_rna.properties:
                        if prop.is_hidden or prop.is_readonly: continue
                        if prop.identifier in FILTER_PROP: continue

                        # only copy matching props
                        if hasattr(nodes, prop.identifier):
                            setattr(nodes, prop.identifier, getattr(mod, prop.identifier))

                    ct_modifier.mod_swap(mod, nodes.modifier)

                    name = str(mod.name)
                    obj.modifiers.remove(mod)
                    nodes.name = name
                    counter += 1

            obj.update_tag()

        self.notify(F'Modifiers Converted: {counter}')

        return {'FINISHED'}