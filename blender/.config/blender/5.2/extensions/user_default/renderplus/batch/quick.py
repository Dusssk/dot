# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright (C) 2014 Diego Gangl
#   <diego@sinestesia.co>
#
#   This file is part of Render+.
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ## END GPL LICENSE BLOCK ##

"""Functions and operators for quick batches."""

import logging
from itertools import product

import bpy
from bpy.props import EnumProperty, IntProperty

from ..single import utils
from . import state
from . import data as batch_data

from bpy.types import Context, Operator, UILayout


# Logging
log = logging.getLogger(__name__)


class SafeDict(dict):
    """Safe Dictionary class to use with string formatting."""

    def __missing__(self, key):
        return "{" + key + "}"


def jobs_for_layers(scene) -> list[dict]:
    """Generate settings for view layers in a scene."""

    return [{"layer": layer} for layer in scene.view_layers if layer.use]


def jobs_for_large_renders(tiles_x: int, tiles_y: int) -> list[dict]:
    """Generate settings for view layers in a scene."""

    result = []

    step_x = 1 / tiles_x
    step_y = 1 / tiles_y

    y = 0
    x = 0

    for _ in range(tiles_x):
        for _ in range(tiles_y):
            result.append(
                {
                    "use_section": True,
                    "section_x": x,
                    "section_y": y,
                    "section_width": step_x,
                    "section_height": step_y,
                }
            )

            y += step_y

        x += step_x

    return result


def jobs_for_markers(scene) -> list[dict]:
    """Generate settings for view layers in a scene."""

    markers = list(scene.timeline_markers)
    markers.sort(key=lambda m: m.frame)

    result = []
    frame_start = 0

    for marker in markers:
        if marker.frame == 0:
            continue

        result.append(
            {
                "scene": scene,
                "marker_name": marker.name,
                "frame_custom": True,
                "frame_still": marker.frame,
                "frame_start": frame_start,
                "frame_end": marker.frame,
            }
        )

        frame_start = marker.frame

    return result


def settings_to_dict(settings) -> dict[str, list]:
    scenes = []
    all_objs = []

    if settings.all_scenes:
        scenes = [s for s in bpy.data.scenes]
    else:
        scenes = [s.scene for s in settings.scenes]

    data = {
        "scene": [s for s in set(scenes)],
    }

    # Create list of objects from all selected scenes
    for scene in scenes:
        all_objs += list(scene.objects)

    if settings.use_worlds:
        if settings.all_worlds:
            data["worlds"] = [w for w in bpy.data.worlds]
        else:
            data["worlds"] = [w.world for w in settings.worlds]

    if settings.use_cameras:
        if settings.all_cameras:
            data["cameras"] = [
                c for c in bpy.data.objects if c.type == "CAMERA" and c in all_objs
            ]
        else:
            data["cameras"] = [
                c.camera for c in settings.cameras if c.camera in all_objs
            ]

    if settings.use_layers:
        data["layers"] = []

        for scene in scenes:
            data["layers"] += [l for l in scene.view_layers if l.use]

    if settings.use_markers:
        data['markers'] = []

        for s in scenes:
            markers = jobs_for_markers(s)

            if markers:
                data["markers"] += markers

    if settings.use_large:
        data["large"] = jobs_for_large_renders(settings.tiles_x, settings.tiles_y)

    return data


def remove_empty(settings) -> dict:
    """Remove empty lists from settings dict."""

    return {key: value for key, value in settings.items() if value}


def combine(settings) -> list[dict]:
    """Combine settings into per-job dictionaries"""

    settings = remove_empty(settings)
    return [dict(zip(settings, v)) for v in product(*settings.values())]


class RP_OT_Quick_SceneProps(Operator):
    """Generate render jobs from scene properties."""

    bl_idname = "renderplus.batch_quick"
    bl_label = "Generate Render Jobs"
    bl_options = {"UNDO"}

    def output(self, recipe: dict) -> dict:

        output = {
            "scene": recipe["scene"].name,
        }

        try:
            output["world"] = recipe["worlds"].name
        except KeyError:
            pass

        try:
            output["camera"] = recipe["cameras"].name
        except KeyError:
            pass

        try:
            output["marker"] = recipe["markers"]["marker_name"]
        except KeyError:
            pass

        try:
            output["tile_x"] = recipe["large"]["section_x"]
        except KeyError:
            pass

        try:
            output["tile_x"] = recipe["large"]["section_y"]
        except KeyError:
            pass

        try:
            output["layer"] = recipe["layers"].name
        except KeyError:
            pass

        return output

    def execute(self, context: Context) -> set[str]:

        jobs = context.scene.renderplus.batch.jobs
        settings = context.scene.renderplus.batch_ops.quick_batch
        data = settings_to_dict(settings)
        combined = combine(data)
        seen = set()

        for recipe in combined:
            output = self.output(recipe)
            hashed = frozenset(output.values())

            # Using output to check for duplis
            if hashed in seen:
                continue

            scene = recipe["scene"]
            camera = recipe.get("cameras")
            marker = recipe.get("markers")
            layer = recipe.get("layers")

            if camera and camera.name not in scene.objects:
                continue

            if marker and marker['scene'] != scene:
                continue

            if layer and layer.name not in scene.view_layers:
                continue

            job = jobs.add()
            context.scene.renderplus.batch.index = len(jobs) - 1
            batch_data.fill_render_passes(job)

            job.scene = scene
            job.camera = camera

            try:
                job.world = recipe["worlds"]
            except KeyError:
                pass

            try:
                job.layer = recipe["layers"].name
            except KeyError:
                pass

            try:
                large = recipe["large"]
                job.use_section = True
                job.section_x = large["section_x"]
                job.section_y = large["section_y"]
                job.section_width = large["section_width"]
                job.section_height = large["section_height"]
            except KeyError:
                pass

            try:
                marker = recipe["markers"]
                job.frame_custom = True
                job.frames = str(marker["frame_still"])
                job.frame_start = marker["frame_start"]
                job.frame_end = marker["frame_end"]

            except KeyError:
                pass

            job.animation = settings.use_animation
            job.name = settings.name.format_map(SafeDict(**output))
            job.output = settings.output_path.format_map(SafeDict(**output))
            seen.add(hashed)

        state.mode = "NORMAL"
        return {"FINISHED"}


class RP_OT_QuickOutputHelp(Operator):
    """Useful information about custom frames"""

    bl_idname = "renderplus.quick_output_help"
    bl_label = "Template Help"

    def execute(self, context) -> set[str]:
        def draw(self, context):
            self.layout.label(
                text="These inputs take placeholders which are auto-filled "
            )
            self.layout.label(text="with information from the render job.")
            self.layout.label(text="")
            self.layout.label(text="The placeholders are: ")
            self.layout.label(text="- {scene}")
            self.layout.label(text="- {camera}")
            self.layout.label(text="- {world}")
            self.layout.label(text="- {layer}")
            self.layout.label(text="- {marker}")
            self.layout.label(text="- {tile_x} (for large render)")
            self.layout.label(text="- {tile_y} (for large render)")

        bpy.context.window_manager.popup_menu(draw, title="Help", icon="INFO")
        return {"FINISHED"}


class RP_OT_Quick_AddConfig(Operator):
    """Add a config for quick batch"""

    bl_idname = "renderplus.batch_quick_add"
    bl_label = "Add"
    bl_options = {"UNDO"}

    mode: EnumProperty(
        items=(
            ("SCENE", "", ""),
            ("CAMERA", "", ""),
            ("WORLD", "", ""),
        )
    )

    def execute(self, context) -> set:

        settings = bpy.context.scene.renderplus.batch_ops.quick_batch

        match self.mode:
            case "SCENE":
                configs = settings.scenes
            case "CAMERA":
                configs = settings.cameras
            case "WORLD":
                configs = settings.worlds
            case _:
                return {"CANCELLED"}

        configs.add()

        return {"FINISHED"}


class RP_OT_Quick_RemoveConfig(Operator):
    """Remove a config for quick batch"""

    bl_idname = "renderplus.batch_quick_remove"
    bl_label = "Remove"
    bl_options = {"UNDO"}

    mode: EnumProperty(
        items=(
            ("SCENE", "", ""),
            ("CAMERA", "", ""),
            ("WORLD", "", ""),
        )
    )

    index: IntProperty(default=0)

    def execute(self, context) -> set:

        settings = bpy.context.scene.renderplus.batch_ops.quick_batch

        match self.mode:
            case "SCENE":
                configs = settings.scenes
            case "CAMERA":
                configs = settings.cameras
            case "WORLD":
                configs = settings.worlds
            case _:
                return {"CANCELLED"}

        configs.remove(self.index)

        return {"FINISHED"}


class Section:
    """General section for the quickbatch UI."""

    def __init__(self, layout, settings, name: str):
        self.layout = layout.box()
        self.settings = settings
        self.icon = ""
        self.name = name
        self.mode = "NONE"
        self.use_all = ""
        self.prop = None
        self.prop_name = "scene"
        self.toggle = None

    def build(self) -> None:

        row = self.layout.row()
        row.label(text=self.name, icon=self.icon)

        if self.toggle:
            row.prop(self.settings, self.toggle, text="")

        if self.toggle and not self.settings.get(self.toggle):
            return

        sub_col = self.layout.column(align=True)
        sub_col.row().prop(self.settings, self.use_all)
        sub_col.separator()

        if self.toggle:
            sub_col.enabled = bool(self.settings.get(self.toggle))

        for i, item in enumerate(self.prop):
            row = sub_col.row(align=True)
            row.enabled = not self.settings.get(self.use_all)
            row.prop(item, self.prop_name, text="")

            if i > 0 or self.mode != "SCENE":
                op = row.operator(
                    "renderplus.batch_quick_remove", text="", icon="TRASH"
                )
                op.mode = self.mode
                op.index = i

        sub_col.separator()
        split = sub_col.split(factor=0.6)
        split.separator()
        split.enabled = not self.settings.get(self.use_all)
        op = split.operator("renderplus.batch_quick_add", text="Add", icon="ADD")
        op.mode = self.mode

        self.layout.separator()


def large_render(layout: UILayout, settings) -> None:
    """Large Render config ui"""

    box = layout.box()
    row = box.row()
    row.label(text="Large Render", icon="IMGDISPLAY")
    row.prop(settings, "use_large", text="")

    if not settings.use_large:
        return

    layout.separator()
    col = box.column(align=True)
    col.prop(settings, "size_x")
    col.prop(settings, "size_y")
    col.separator()

    col.prop(settings, "tiles_x")
    col.prop(settings, "tiles_y")

    col = box.column(align=True)
    col.label(text=f"Tile width: {(settings.size_x // settings.tiles_x)} px")
    col.label(text=f"Tile height: {(settings.size_y // settings.tiles_y)} px")
    col.separator()
    col.label(text=f"{settings.tiles_x * settings.tiles_y} tiles in total")


def markers(layout: UILayout, settings) -> None:
    """Markers config ui"""

    box = layout.box()
    row = box.row()
    row.label(text="Markers", icon="MARKER")
    row.prop(settings, "use_markers", text="")


def layers(layout: UILayout, settings) -> None:
    """Markers config ui"""

    box = layout.box()
    row = box.row()
    row.label(text="View Layers", icon="RENDERLAYERS")
    row.prop(settings, "use_layers", text="")


def quick_mode(layout: UILayout) -> None:
    """UI code for quick batch config mode"""

    settings = bpy.context.scene.renderplus.batch_ops.quick_batch

    utils.title(layout, "Quick Batch", "SHADERFX")

    column = layout.column(align=True)

    scenes = Section(column, settings, "Scene(s)")
    scenes.icon = "SCENE_DATA"
    scenes.mode = "SCENE"
    scenes.prop = settings.scenes
    scenes.prop_name = "scene"
    scenes.use_all = "all_scenes"

    scenes.build()

    cameras = Section(column, settings, "Camera(s)")
    cameras.icon = "CAMERA_DATA"
    cameras.mode = "CAMERA"
    cameras.prop = settings.cameras
    cameras.prop_name = "camera"
    cameras.use_all = "all_cameras"
    cameras.toggle = "use_cameras"

    cameras.build()

    world = Section(column, settings, "World(s)")
    world.icon = "WORLD_DATA"
    world.mode = "WORLD"
    world.prop = settings.worlds
    world.prop_name = "world"
    world.use_all = "all_worlds"
    world.toggle = "use_worlds"

    world.build()

    layers(column, settings)
    markers(column, settings)
    large_render(column, settings)

    layout.separator()
    layout.row().prop(settings, "use_animation", text="Set as animations")

    row = layout.row(align=True)
    row.prop(settings, "name", text="Name")
    row.operator("renderplus.quick_output_help", icon="QUESTION", text="")

    row = layout.row(align=True)
    row.prop(settings, "output_path", text="Output")
    row.operator("renderplus.quick_output_help", icon="QUESTION", text="")

    layout.separator()

    row = layout.row(align=True)
    row.scale_y = 1.5
    row.scale_x = 1.5
    row.enabled = settings.has_scene()
    row.operator(
        "renderplus.batch_quick", text="Create Render Jobs", icon="PREFERENCES"
    )
    row.operator('renderplus.batch_toggle_mode', text='', icon='LOOP_BACK')
    layout.separator()
