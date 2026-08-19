# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright (C) 2018 Diego Gangl
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

"""Data structures and operators for external render jobs."""


import os
import logging

import bpy
from bpy.types import PropertyGroup, Context, Operator, OperatorFileListElement
from bpy.props import StringProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper
from pathlib import Path

from typing import Any

from ..vendor import blendfile
from ..single import utils
from . import state
from . import ops


log = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Helper functions to get external blend data
# ------------------------------------------------------------------------------


def datablock_name(block: Any) -> str:
    """Return name property of datablock."""

    return block.get((b"id", b"name"))[2:]


def get_name(block: Any) -> str:
    """Return name property of datablock."""

    return block[b"id", b"name"][2:].decode("utf8")


def is_camera(block: Any) -> bool:
    """Determine if datablock object is a camera."""

    return block[b"type"] == 11


def find_engine(job: PropertyGroup, scene: str) -> str:
    """Find engine used in scene."""

    try:
        blend = blendfile.open_cached(Path(job.blend_file))
        scene_blocks = blend.find_blocks_from_code(b"SC")
        for sc in scene_blocks:
            if get_name(sc) == scene:
                engine = sc[b"r", b"engine"].decode("utf8")
                log.debug(f"Found engine {engine} for scene {scene}")
                return engine

    except Exception as e:
        log.error(("Can't open blend file. File may be " f'corrupted. Error: "{e}"'))

        return ""


def get_default_output(job: PropertyGroup, scene: str) -> str:
    """Find output in Blend file."""

    try:
        blend = blendfile.open_cached(Path(job.blend_file))
        scene_blocks = blend.find_blocks_from_code(b"SC")
        for sc in scene_blocks:
            if get_name(sc) == scene:
                output = sc[b"r", b"pic"].decode("utf-8")
                log.debug(f"Found Output {output} for scene {scene}")
                return output

    except Exception as e:
        log.error(("Can't open blend file. File may be " f'corrupted. Error: "{e}"'))

        return ""


def fill_props(self, context: Context) -> None:
    """Callback to fill external job on update."""

    if not self.blend_file:
        return

    if not os.path.isfile(self.blend_file):
        log.error(f"Can't find blend file {self.blend_file}")
        state.external_error = True
        return

    state.external_error = False
    log.debug(f"Loading job info from file {self.blend_file}")

    scenes = []
    worlds = []
    cameras = []
    view_layers = []
    scripts = []
    scene = None

    try:
        blend = blendfile.open_cached(Path(self.blend_file))

        scene_blocks = blend.find_blocks_from_code(b"SC")
        scenes = [get_name(block) for block in scene_blocks]

        for block in blend.blocks:
            if block.dna_type_name == "World":
                worlds.append(get_name(block))

            elif block.dna_type_name == "Text":
                scripts.append(get_name(block))

            elif block.dna_type_name == "ViewLayer":
                view_layers.append(block[b"name"].decode("utf8"))

            elif block.dna_type_name == "Object" and is_camera(block):
                cameras.append(get_name(block))

            elif block.code == b"WM":
                window = block.get_pointer(b"winactive")

                if blend.header.version < 280:
                    screen = window.get_pointer(b"screen")
                    scene = screen.get_pointer(b"scene")
                else:
                    scene = window.get_pointer(b"scene")

                world = scene.get_pointer(b"world")
                camera = scene.get_pointer(b"camera")

                self.ex_scene = get_name(scene)

                # We might not find a world or camera in the blend file
                try:
                    self.ex_world = get_name(world)
                except AttributeError:
                    log.debug("No default world in file")
                    self.ex_world = ""

                try:
                    self.ex_camera = get_name(camera)
                except AttributeError:
                    log.debug("No default camera in file")
                    self.ex_camera = ""

                self.frame_still = scene[b"r", b"cfra"]
                self.frame_start = scene[b"r", b"sfra"]
                self.frame_end = scene[b"r", b"efra"]
                self.output = scene[b"r", b"pic"].decode("utf8")

            # Loop end

        try:
            # View layers needs to be full before setting the default
            # so it has to be done outside the loop
            layer_index = int(scene[b"lay"]) - 1
            self.ex_layer = view_layers[layer_index]

        except IndexError:
            # There's always at least one view layer
            # in the scene in 2.8. For older versions we can skip this.
            if blend.header.version >= 280:
                self.ex_layer = view_layers[0]

    except Exception as e:
        log.error(("Can't open blend file. File may be " f'corrupted. Error: "{e}"'))
        state.external_error = True
        return

    log.debug(f"Scenes found in file: {scenes}")
    log.debug(f"Worlds found in file: {worlds}")
    log.debug(f"Cameras found in file: {cameras}")
    log.debug(f"View Layers found in file: {view_layers}")
    log.debug(f"Scripts found in file: {scripts}")

    filename = utils.base_filename(self.blend_file)
    self.name = filename

    prop_collection = bpy.context.window_manager.renderplus

    try:
        props = prop_collection[filename]
        props.scenes.clear()
        props.worlds.clear()
        props.cameras.clear()
        props.view_layers.clear()
        props.scripts.clear()

    except KeyError:
        props = prop_collection.add()
        props.name = filename

    for s in scenes:
        props.scenes.add().name = s

    for w in worlds:
        props.worlds.add().name = w

    for c in cameras:
        props.cameras.add().name = c

    for l in view_layers:
        props.view_layers.add().name = l

    for s in scripts:
        props.scripts.add().name = s


# ------------------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------------------


class RP_PG_ExternalBlendProperty(PropertyGroup):
    """Hold a property from an external blend file."""

    name: StringProperty(name="Data")


class RP_PG_ExternalBlendData(PropertyGroup):
    """Hold data from an external blend file."""

    name: StringProperty(
        name="Blend file Name",
        description="Name of the blend file associated with this data",
        default="",
    )

    scenes: CollectionProperty(type=RP_PG_ExternalBlendProperty)
    worlds: CollectionProperty(type=RP_PG_ExternalBlendProperty)
    cameras: CollectionProperty(type=RP_PG_ExternalBlendProperty)
    view_layers: CollectionProperty(type=RP_PG_ExternalBlendProperty)
    scripts: CollectionProperty(type=RP_PG_ExternalBlendProperty)


# ------------------------------------------------------------------------------
# Operators
# ------------------------------------------------------------------------------


class RP_OT_SetExternalBlendFile(Operator, ImportHelper):
    """Set the external blendfile path for a render job."""

    bl_idname = "renderplus.batch_set_external_file"
    bl_label = "Set external file for job"
    poll = ops.ready_to_run

    filter_glob: StringProperty(
        default="*.blend;",
        options={"HIDDEN"},
    )

    files: CollectionProperty(
        name="File Path",
        type=OperatorFileListElement,
    )

    directory: StringProperty(subtype="DIR_PATH")
    filename_ext: str = ""

    def execute(self, context):
        job = ops.current_job()
        job.blend_file = os.path.join(self.directory, self.files[0].name)

        return {"FINISHED"}


class RP_OT_AddExternalRenderJobs(Operator, ImportHelper):
    """Add multiple external blendfiles as render jobs."""

    bl_idname = "renderplus.add_external_render_jobs"
    bl_label = "Add external render jobs"

    filter_glob: StringProperty(
        default="*.blend;",
        options={"HIDDEN"},
    )

    files: CollectionProperty(
        name="File Path",
        type=OperatorFileListElement,
    )

    directory: StringProperty(subtype="DIR_PATH")

    filename_ext: str = ""

    @classmethod
    def poll(self, context):
        return state.mode != "RUNNING"

    def execute(self, context):
        batch_list = context.scene.renderplus.batch.jobs
        scene = context.scene

        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)

            if os.path.isfile(filepath):
                job = batch_list.add()
                job.use_external = True
                job.blend_file = filepath

                job.output = ""

        return {"FINISHED"}


class RP_OT_ReloadExternalBlendData(Operator):
    """Reload external blend data for all renderjobs."""

    bl_idname = "renderplus.reload_external_blend_data"
    bl_label = "Reload data from external blend files"
    poll = ops.ready_to_run

    def execute(self, context):
        [
            fill_props(job, context)
            for job in context.scene.renderplus.batch.jobs
            if job.use_external
        ]

        return {"FINISHED"}
