import bpy
import os
from pathlib import Path
from .... import bl_info


def sort_numerically(items):
    import re

    def alphanum_key(key):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', key)]
    return sorted(items, key=alphanum_key)


def populate_menu(menu, context, path):
    files_and_folders = os.listdir(path)
    sorted_items = sort_numerically(files_and_folders)

    for item in sorted_items:
        full_path = os.path.join(path, item)
        if item.lower().endswith('.blend'):
            menu.layout.operator("nsolve.load_file", text=item).filepath = full_path


class NSOLVE_MT_FilesMenu(bpy.types.Menu):
    bl_idname = "NSOLVE_MT_FilesMenu"
    bl_label = f"nSolve: {bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"

    def draw(self, context):
        demo_files_dir = Path(__file__).parent.parent.parent.parent / "Files"
        populate_menu(self, context, demo_files_dir)
