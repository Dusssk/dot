import bpy, pathlib
from .node_modifier import NodeModifier


NODES_FOLDER = 'HOPS_Nodes'
INPUTS = {'Solver', 'Merge Threshold', 'Material', 'Clean Attribute 4', 'Object', 'Tag Faces Value', 'Inset Slice Offset', 'Clean Attribute 5', 'Tag Edge Boundary Value', 'Transfer Normals', 'Clean Attribute 1', 'Weld', 'Clean Attribute 2', 'Clean Attribute 3', 'Input Geometry', 'Material Cut', 'Operation', 'Tag Faces Name', 'Inset Thickness', 'Tag Inset Slice Face Value', 'Tag Inset Slice Edge Name', 'Inset Slice', 'Non Manifold', 'Tag Edge Boundary Name', 'Tag Inset Slice Edge Value', 'Stitch Distance', 'Tag Inset Slice Face Name'}
OPERATION_INPUT = {0: 'INTERSECT', 'INTERSECT': 0, 1: 'UNION', 'UNION': 1, 2: 'DIFFERENCE', 'DIFFERENCE': 2, 3: 'INSET', 'INSET': 3, 4: 'KNIFE', 'KNIFE': 4}
OPERATION_INPUT_STR = {'Intersect': 'INTERSECT', 'INTERSECT': 'Intersect', 'Union': 'UNION', 'UNION': 'Union', 'Difference': 'DIFFERENCE', 'DIFFERENCE': 'Difference', 'Inset': 'INSET', 'INSET': 'Inset', 'Knife': 'KNIFE', 'KNIFE': 'Knife'}
SOLVER_INPUT = {itm.identifier: itm.value for itm in bpy.types.BooleanModifier.bl_rna.properties['solver'].enum_items}
SOLVER_INPUT.update({itm.value: itm.identifier for itm in bpy.types.BooleanModifier.bl_rna.properties['solver'].enum_items}) # FLOAT/FAST, EXACT, MANIFOLD
SOLVER_INPUT_STR = {'Float': 'FLOAT', 'FLOAT': 'Float', 'Exact': 'EXACT', 'EXACT': 'Exact', 'Manifold': 'MANIFOLD', 'MANIFOLD': 'Manifold'}

class NodeBoolean(NodeModifier):
    default_name = 'HOPS_Boolean'
    asset_name = 'HOPS_Boolean'
    blend_filename = 'HOPS_Boolean.blend'

    # input wrappers
    @property
    def input_geometry(self):
        return self.input_get("Input Geometry")

    @input_geometry.setter
    def input_geometry(self, val):
        self.input_set("Input Geometry", val)
        self.update_tag()

    @property
    def operation(self):
        '''DIFFERNCE, UNION, INTERSECT, INSET, KNIFE'''
        return OPERATION_INPUT_STR[self.input_get("Operation")] if self.str_enum else OPERATION_INPUT[self.input_get("Operation")]

    @operation.setter
    def operation(self, val):
        self.input_set("Operation", OPERATION_INPUT_STR[val] if self.str_enum else OPERATION_INPUT[val])
        self.update_tag()

    @property
    def object(self):
        return self.input_get("Object")

    @object.setter
    def object(self, val):
        self.input_set("Object", val)
        self.update_tag()

    @property
    def solver(self):
        '''FLOAT, EXACT, MANIFOLD'''
        return SOLVER_INPUT_STR[self.input_get("Solver")] if self.str_enum else SOLVER_INPUT[self.input_get("Solver")]

    @solver.setter
    def solver(self, val):
        self.input_set("Solver", SOLVER_INPUT_STR[val] if self.str_enum else SOLVER_INPUT[val])
        self.update_tag()

    @property
    def inset_thickness(self):
        return self.input_get("Inset Thickness")

    @inset_thickness.setter
    def inset_thickness(self, val):
        self.input_set("Inset Thickness", float(val))
        self.update_tag()

    @property
    def stitch_distance(self):
        return self.input_get("Stitch Distance")

    @stitch_distance.setter
    def stitch_distance(self, val):
        self.input_set("Stitch Distance", float(val))
        self.update_tag()

    @property
    def non_manifold(self):
        return self.input_get("Non Manifold")

    @non_manifold.setter
    def non_manifold(self, val):
        self.input_set("Non Manifold", bool(val))
        self.update_tag()

    @property
    def inset_slice(self):
        return self.input_get("Inset Slice")

    @inset_slice.setter
    def inset_slice(self, val):
        self.input_set("Inset Slice", bool(val))
        self.update_tag()

    @property
    def inset_slice_offset(self):
        return self.input_get("Inset Slice Offset")

    @inset_slice_offset.setter
    def inset_slice_offset(self, val):
        self.input_set("Inset Slice Offset", float(val))
        self.update_tag()

    @property
    def transfer_normals(self):
        return self.input_get("Transfer Normals")

    @transfer_normals.setter
    def transfer_normals(self, val):
        self.input_set("Transfer Normals", bool(val))
        self.update_tag()

    @property
    def material_cut(self):
        return self.input_get("Material Cut")

    @material_cut.setter
    def material_cut(self, val):
        self.input_set("Material Cut", bool(val))
        self.update_tag()

    @property
    def material(self):
        return self.input_get("Material")

    @material.setter
    def material(self, val):
        self.input_set("Material", val)
        self.update_tag()

    @property
    def weld(self):
        return self.input_get("Weld")

    @weld.setter
    def weld(self, val):
        self.input_set("Weld", bool(val))
        self.update_tag()

    @property
    def merge_threshold(self):
        return self.input_get("Merge Threshold")

    @merge_threshold.setter
    def merge_threshold(self, val):
        self.input_set("Merge Threshold", float(val))
        self.update_tag()

    @property
    def tag_faces_name(self):
        return self.input_get("Tag Faces Name")

    @tag_faces_name.setter
    def tag_faces_name(self, val):
        self.input_set("Tag Faces Name", val)
        self.update_tag()

    @property
    def tag_faces_value(self):
        return self.input_get("Tag Faces Value")

    @tag_faces_value.setter
    def tag_faces_value(self, val):
        self.input_set("Tag Faces Value", float(val))
        self.update_tag()

    @property
    def tag_edge_boundary_name(self):
        return self.input_get("Tag Edge Boundary Name")

    @tag_edge_boundary_name.setter
    def tag_edge_boundary_name(self, val):
        self.input_set("Tag Edge Boundary Name", val)
        self.update_tag()

    @property
    def tag_edge_boundary_value(self):
        return self.input_get("Tag Edge Boundary Value")

    @tag_edge_boundary_value.setter
    def tag_edge_boundary_value(self, val):
        self.input_set("Tag Edge Boundary Value", float(val))
        self.update_tag()

    @property
    def tag_inset_slice_face_name(self):
        return self.input_get("Tag Inset Slice Face Name")

    @tag_inset_slice_face_name.setter
    def tag_inset_slice_face_name(self, val):
        self.input_set("Tag Inset Slice Face Name", val)
        self.update_tag()

    @property
    def tag_inset_slice_face_value(self):
        return self.input_get("Tag Inset Slice Face Value")

    @tag_inset_slice_face_value.setter
    def tag_inset_slice_face_value(self, val):
        self.input_set("Tag Inset Slice Face Value", float(val))
        self.update_tag()

    @property
    def tag_inset_slice_edge_name(self):
        return self.input_get("Tag Inset Slice Edge Name")

    @tag_inset_slice_edge_name.setter
    def tag_inset_slice_edge_name(self, val):
        self.input_set("Tag Inset Slice Edge Name", val)
        self.update_tag()

    @property
    def tag_inset_slice_edge_value(self):
        return self.input_get("Tag Inset Slice Edge Value")

    @tag_inset_slice_edge_value.setter
    def tag_inset_slice_edge_value(self, val):
        self.input_set("Tag Inset Slice Edge Value", float(val))
        self.update_tag()

    @property
    def clean_attribute_1(self):
        return self.input_get("Clean Attribute 1")

    @clean_attribute_1.setter
    def clean_attribute_1(self, val):
        self.input_set("Clean Attribute 1", val)
        self.update_tag()

    @property
    def clean_attribute_2(self):
        return self.input_get("Clean Attribute 2")

    @clean_attribute_2.setter
    def clean_attribute_2(self, val):
        self.input_set("Clean Attribute 2", val)
        self.update_tag()

    @property
    def clean_attribute_3(self):
        return self.input_get("Clean Attribute 3")

    @clean_attribute_3.setter
    def clean_attribute_3(self, val):
        self.input_set("Clean Attribute 3", val)
        self.update_tag()

    @property
    def clean_attribute_4(self):
        return self.input_get("Clean Attribute 4")

    @clean_attribute_4.setter
    def clean_attribute_4(self, val):
        self.input_set("Clean Attribute 4", val)
        self.update_tag()

    @property
    def clean_attribute_5(self):
        return self.input_get("Clean Attribute 5")

    @clean_attribute_5.setter
    def clean_attribute_5(self, val):
        self.input_set("Clean Attribute 5", val)
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