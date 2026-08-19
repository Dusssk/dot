import bpy, pathlib
from ...... utility.geometry_nodes import NodeModifier


NODES_FOLDER = 'BC_Nodes'
INPUTS = {'Flipped Faces', 'Mark Sharp Angle', 'Mark Sharp', 'Remove Attrs', 'Geometry'}



class Clean(NodeModifier):
    default_name = 'BC_Clean'
    asset_name = 'BC_Clean'
    blend_filename = 'BC_Shape_nodes.blend'

    @property
    def geometry(self):
        return self.input_get("Geometry")

    @geometry.setter
    def geometry(self, val):
        self.input_set("Geometry", val)
        self.update_tag()

    @property
    def flipped_faces(self):
        return self.input_get("Flipped Faces")

    @flipped_faces.setter
    def flipped_faces(self, val):
        self.input_set("Flipped Faces", val)
        self.update_tag()

    @property
    def remove_attrs(self):
        return self.input_get("Remove Attrs")

    @remove_attrs.setter
    def remove_attrs(self, val):
        self.input_set("Remove Attrs", val)
        self.update_tag()

    @property
    def mark_sharp(self):
        return self.input_get("Mark Sharp")

    @mark_sharp.setter
    def mark_sharp(self, val):
        self.input_set("Mark Sharp", bool(val))
        self.update_tag()

    @property
    def mark_sharp_angle(self):
        return self.input_get("Mark Sharp Angle")

    @mark_sharp_angle.setter
    def mark_sharp_angle(self, val):
        self.input_set("Mark Sharp Angle", float(val))
        self.update_tag()

    @classmethod
    def is_valid_node_group(cls, node_group) -> bool:
        return INPUTS.issubset(node_group.interface.items_tree.keys())

    @classmethod
    def get_or_load_node_group(cls):
        if not cls.last_valid_group_name:
            node_groups = list(filter(cls.is_asset_node_group, bpy.data.node_groups))

            for ng in node_groups:
                if cls.is_valid_node_group(ng):
                    return ng

        try:
            node_group = bpy.data.node_groups[cls.last_valid_group_name]
            if cls.is_asset_node_group(node_group) and cls.is_valid_node_group(node_group):
                return node_group

        except KeyError:
            pass

        # if last loaded group isn't valid, load a new one
        path = cls.get_filepath()

        with bpy.data.libraries.load(path) as (data_from, data_to):
            data_to.node_groups.append(cls.asset_name)

        node_group = data_to.node_groups[0]

        cls.last_valid_group_name = data_to.node_groups[0].name

        return data_to.node_groups[0]

    @classmethod
    def calc_asset_path(cls):
        blend = cls.blend_filename

        path = pathlib.Path(__file__).parent / NODES_FOLDER

        return str(path / blend)

    def update_tag(self):
        self.modifier.id_data.update_tag()
