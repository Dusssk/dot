import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper
import json

from ....utils import addon
from ... import analytics


def snap_settings_to_dict(snap):
    return {
        "vert": snap.vert,
        "edge": snap.edge,
        "face": snap.face,
        "mid_edge": snap.mid_edge,
        "perp_edge": snap.perp_edge,
        "center_face": snap.center_face,
    }


def snap_settings_from_dict(snap, data):
    snap.vert = data.get("vert", True)
    snap.edge = data.get("edge", False)
    snap.face = data.get("face", False)
    snap.mid_edge = data.get("mid_edge", False)
    snap.perp_edge = data.get("perp_edge", False)
    snap.center_face = data.get("center_face", False)


def gizmo_collection_to_dict(collection):
    dictionary = {}

    def col_to_dict(collection, dictionary):
        filter = {'rna_type', 'name'} #blender default

        for key in collection.bl_rna.properties.keys():
            if key in filter: continue
            val = getattr(collection, key)

            if isinstance(val, bpy.types.PropertyGroup):
                nested_dict = dict()
                dictionary[key] = nested_dict
                col_to_dict(val, nested_dict)

            else:
                if hasattr(val, '__len__') and type(val) != str:
                    val = [v for v in val]

                dictionary[key] = val

    col_to_dict(collection, dictionary)

    return dictionary


def gizmo_collection_from_dict(collection, data):

    def dict_to_col(collection, data):

        for key, val in data.items():
            if type(val) == dict:
                dict_to_col(getattr(collection, key), val)

            else:
                setattr(collection, key, val)

    dict_to_col(collection, data)


class NSOLVE_OT_ExportPersona(bpy.types.Operator, ExportHelper):
    bl_idname = "nsolve.export_persona"
    bl_label = "Export Personas"
    bl_description = "Export the personas list to a .json file"

    filename_ext = ".nso"
    filter_glob: bpy.props.StringProperty(default="*.nso", options={'HIDDEN'})

    def execute(self, context):
        prop = addon.pref().tools.nsolve
        personas_list = [
            {
                "persona": item.persona,
                "main": gizmo_collection_to_dict(item.main),
                "aux": gizmo_collection_to_dict(item.aux),
                "sub": gizmo_collection_to_dict(item.sub),
                "ext": gizmo_collection_to_dict(item.ext),
            }
            for item in prop.personas_list_items
        ]

        data = {"personas_list_items": personas_list}

        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=4)

        self.report({'INFO'}, f"Exported {len(personas_list)} personas")
        analytics.stats("nSolve: Export personas")
        return {'FINISHED'}


class NSOLVE_OT_ImportPersona(bpy.types.Operator, ImportHelper):
    bl_idname = "nsolve.import_persona"
    bl_label = "Import Personas"
    bl_description = "Import the personas list from a .json file"

    filename_ext = ".nso"
    filter_glob: bpy.props.StringProperty(default="*.nso", options={'HIDDEN'})

    def execute(self, context):
        prop = addon.pref().tools.nsolve

        with open(self.filepath, 'r') as f:
            data = json.load(f)

        personas_list = data.get("personas_list_items", [])

        prop.personas_list_items.clear()
        for item in personas_list:
            new_item = prop.personas_list_items.add()
            new_item.persona = item["persona"]
            gizmo_collection_from_dict(new_item.main, item["main"])
            gizmo_collection_from_dict(new_item.aux, item["aux"])
            gizmo_collection_from_dict(new_item.sub, item["sub"])
            gizmo_collection_from_dict(new_item.ext, item["ext"])

        self.report({'INFO'}, f"Imported {len(personas_list)} personas")
        analytics.stats("nSuite: Import personas")
        return {'FINISHED'}
