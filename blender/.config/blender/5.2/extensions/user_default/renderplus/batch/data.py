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

"""Data structures for batch settings and render jobs."""

import os
import multiprocessing
import logging
from uuid import uuid4

import bpy
import sys
from bpy.types import PropertyGroup, Context
from bpy.props import (
    IntProperty,
    StringProperty,
    BoolProperty,
    EnumProperty,
    FloatProperty,
    CollectionProperty,
    PointerProperty,
)

from typing import List

from . import external
from ..single import utils


log = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
#  Batch Operator Settings
# ------------------------------------------------------------------------------

suffix_options = (
    ("NONE", "None", ""),
    ("FILENAME", "File Name", ""),
    ("SCENE", "Scene", ""),
    ("VIEWLAYER", "View Layer", ""),
    ("CAMERA", "Camera", ""),
)

passes_list = {
    "ALL": [
        ("use_pass_z", "Z", "Depth"),
        ("use_pass_mist", "Mist", "Mist"),
        ("use_pass_normal", "Normal", "Normal"),
        ("use_pass_emit", "Emission", "Emit"),
        ("use_pass_environment", "Enviroment", "Env"),
        ("use_pass_ambient_occlusion", "Ambient Occlusion", "AO"),
        ("use_pass_cryptomatte_object", "Cryptomatte Object", "CryptoObject00"),
        ("use_pass_cryptomatte_material", "Cryptomatte Material", "CryptoMaterial00"),
        ("use_pass_cryptomatte_asset", "Cryptomatte Asset", "CryptoAsset00"),
    ],
    "BLENDER_EEVEE": [
        ("use_pass_diffuse_direct", "Diffuse Light", "DiffDir"),
        ("use_pass_diffuse_color", "Diffuse Color", "DiffCol"),
        ("use_pass_glossy_direct", "Specular Light", "GlossDir"),
        ("use_pass_glossy_color", "Specular Color", "GlossCol"),
        ("use_pass_volume_direct", "Volume Light", "VolumeDir"),
        ("use_pass_transparent", "Transparent", "Transp"),
        ("use_pass_bloom", "Bloom", "BloomCol"),
    ],
    "CYCLES": [
        ("use_pass_vector", "Vector", "Vector"),
        ("use_pass_uv", "UV", "UV"),
        ("use_pass_object_index", "Object Index", "IndexOB"),
        ("use_pass_material_index", "Material Index", "IndexMA"),
        ("use_pass_diffuse_direct", "Diffuse Direct", "DiffDir"),
        ("use_pass_diffuse_indirect", "Diffuse Indirect", "DiffInd"),
        ("use_pass_diffuse_color", "Diffuse Color", "DiffCol"),
        ("use_pass_glossy_direct", "Glossy Direct", "GlossDir"),
        ("use_pass_glossy_indirect", "Glossy Indirect", "GlossInd"),
        ("use_pass_glossy_color", "Glossy Color", "GlossCol"),
        ("use_pass_transmission_direct", "Transmission Direct", "TransDir"),
        ("use_pass_transmission_indirect", "Transmission Indirect", "TransInd"),
        ("use_pass_transmission_color", "Transmission Color", "TransCol"),
        ("cycles.use_pass_volume_direct", "Volume Direct", "VolumeDir"),
        ("cycles.use_pass_volume_indirect", "Volume Indirect", "VolumeInd"),
        ("cycles.use_pass_shadow_catcher", "Shadow Catcher", "Shadow Catcher"),
    ],
}


class RP_PG_BatchOps_OutputChange(PropertyGroup):
    """Settings for Output Change."""

    base_directory: StringProperty(
        name="Base directory", default="", subtype="FILE_PATH"
    )

    base_filename: StringProperty(
        name="Base filename",
        default="",
    )

    name_suffix_01: EnumProperty(
        items=suffix_options,
        name="First Suffix",
    )

    name_suffix_02: EnumProperty(
        items=suffix_options,
        name="Second Suffix",
    )

    name_suffix_03: EnumProperty(
        items=suffix_options,
        name="Third Suffix",
    )

    subdirs_scene: BoolProperty(
        name="Scenes",
        description="Make subir for each scene",
        default=False,
    )

    subdirs_cam: BoolProperty(
        name="Cameras",
        description="Make subir for each camera",
        default=False,
    )

    subdirs_layer: BoolProperty(
        name="View Layers",
        description="Make subir for each viewlayer",
        default=False,
    )


class RP_PG_BatchOps_QuickScenes(PropertyGroup):
    scene: PointerProperty(
        name="Scene", description="Scenes to render", type=bpy.types.Scene
    )


class RP_PG_BatchOps_QuickWorlds(PropertyGroup):
    world: PointerProperty(
        name="World", description="Worlds to render", type=bpy.types.World
    )


class RP_PG_BatchOps_QuickCameras(PropertyGroup):
    camera: PointerProperty(
        name="Cameras",
        description="Cameras to render",
        type=bpy.types.Object,
        poll=lambda _, o: o.type == "CAMERA",
    )


class RP_PG_BatchOps_QuickBatch(PropertyGroup):
    """Settings for Quick Batch."""

    def has_scene(self) -> bool:
        """Determine if at least one scene has been set up."""

        return any([s for s in self.scenes]) or self.all_scenes


    use_animation: BoolProperty(
        name="Animations",
        description="Make all renderjobs animations",
        default=False,
    )

    output_path: StringProperty(
        name="Output path", default="//render_{scene}.png", subtype="FILE_PATH"
    )
    name: StringProperty(name="Name Template", default="{scene}")

    use_cameras: BoolProperty(
        name="Cameras",
        description="Make a job for each camera",
        default=False,
    )

    use_worlds: BoolProperty(
        name="Worlds",
        description="Make a job for each world",
        default=False,
    )

    use_layers: BoolProperty(
        name="View Layers",
        description="Make a job for each view layer",
        default=False,
    )

    use_markers: BoolProperty(
        name="Markers",
        description="Make a job for each marker",
        default=False,
    )

    use_large: BoolProperty(
        name="Large Render",
        description="Split render jobs in tiles",
        default=False,
    )

    all_scenes: BoolProperty(default=False, name="Use all scenes")
    all_markers: BoolProperty(default=False, name="Use all")
    all_cameras: BoolProperty(default=False, name="Use all")
    all_layers: BoolProperty(default=False, name="Use all")
    all_worlds: BoolProperty(default=False, name="Use all")

    layer: StringProperty(
        name="Layer", description="Specific view layer to render.", default=""
    )

    scenes: CollectionProperty(
        name="Scene", description="Scenes to render", type=RP_PG_BatchOps_QuickScenes
    )

    cameras: CollectionProperty(
        name="Cameras",
        description="Cameras to render",
        type=RP_PG_BatchOps_QuickCameras,
    )

    worlds: CollectionProperty(
        name="Worlds", description="Worlds to render", type=RP_PG_BatchOps_QuickWorlds
    )

    kind: EnumProperty(
        name="Type of Quick Batch",
        items=(
            ("SCENE", "Scenes", "", "SCENE_DATA", 0),
            ("CAMERAS", "Cameras", "", "CAMERA_DATA", 1),
            ("MARKERS", "Markers", "", "MARKER_HLT", 2),
            ("LARGE", "Large Render", "", "IMGDISPLAY", 3),
        ),
    )

    tiles_x: IntProperty(
        name="Horizontal Tiles",
        min=1,
        max=10,
        default=2,
    )

    tiles_y: IntProperty(
        name="Vertical Tiles",
        min=1,
        max=10,
        default=2,
    )

    size_x: IntProperty(
        name="Width",
        min=1,
        max=10000,
        default=1,
        subtype="PIXEL",
    )

    size_y: IntProperty(
        name="Height",
        min=1,
        max=100000,
        default=1,
        subtype="PIXEL",
    )

    layer: StringProperty(
        name="Layer", description="Specific view layer to render.", default=""
    )

    no_camera: BoolProperty(
        name="Don't use cameras",
        default=False,
        description="Don't setup cameras for render jobs",
    )


class RP_PG_BatchOps(PropertyGroup):
    """Settings for operators."""

    output_change: PointerProperty(type=RP_PG_BatchOps_OutputChange)
    quick_batch: PointerProperty(type=RP_PG_BatchOps_QuickBatch)


def fill_render_passes(job: PropertyGroup) -> None:
    """Fill render passes for a render job."""

    for engine, passlist in passes_list.items():
        for renderpass in passlist:
            p = job.passes.add()
            p.key = renderpass[0]
            p.name = renderpass[1]
            p.socket = renderpass[2]
            p.engine = engine
            p.output = f"//passes{os.sep}{p.name}"


class RP_PG_RenderPass(PropertyGroup):
    """A Render pass."""

    name: StringProperty(name="Name")
    key: StringProperty(name="Key")
    socket: StringProperty(name="Key")
    engine: EnumProperty(
        name="Render Engine",
        items=(
            ("ALL", "All Engines", ""),
            ("CYCLES", "Cycles", ""),
            ("BLENDER_EEVEE", "EEVEE", ""),
        ),
    )

    output: StringProperty(name="Output Path", subtype="FILE_PATH")

    enabled: BoolProperty(name="Enabled", description="Enable this hook", default=False)


# ------------------------------------------------------------------------------
# Data for Render job
# ------------------------------------------------------------------------------


class RP_PG_Hook(PropertyGroup):
    """Custom hook."""

    command: StringProperty(
        name="Command",
        description="Command to execute",
        default="",
    )

    enabled: BoolProperty(name="Enabled", description="Enable this hook", default=False)

    script: PointerProperty(
        name="Script", description="Python script to run", type=bpy.types.Text
    )

    kind: EnumProperty(
        name="Type",
        description="Whether to run a script or a command",
        items=(("CMD", "Shell Command", ""), ("SCRIPT", "Python Script", "")),
    )


def prop_item(self, context: Context) -> list:
    output = []

    match self.kind:
        case 'bpy.data.collections':
            output += [('VISIBLE', 'Visible', '')]
        case 'bpy.data.objects':
            output += [('VISIBLE', 'Visible', '')]
            output += [('LOCATION', 'Location', '')]
            output += [('SCALE', 'Scale', '')]
            output += [('ROTATION', 'Rotation', '')]
        case 'bpy.data.lights':
            output += [('COLOR', 'Color', '')]
            output += [('POWER', 'Intensity', '')]
        case 'bpy.data.cameras':
            output += [('FOCAL', 'Focal Length', '')]

    output += [('CUSTOM', 'Custom', '')]

    return output


PROP_PATHS = {
        'VISIBLE': 'hide_render',
        'LOCATION': 'location',
        'SCALE': 'scale',
        'ROTATION': 'rotation_euler',
        'COLOR': 'color',
        'POWER': 'energy',
        'FOCAL': 'lens',
}

def store_id(self, context: Context) -> None:

    # No need to store anything for custom
    if self.prop_type == 'CUSTOM':
        return

    pointer = None

    match self.kind:
        case 'bpy.data.collections':
            pointer = self.col_pointer
        case 'bpy.data.objects':
            pointer = self.obj_pointer
        case 'bpy.data.lights':
            pointer = self.lights_pointer
        case 'bpy.data.cameras':
            pointer = self.cameras_pointer

    # This looks super weird but what we are doing
    # is storing the property as an ID prop, which
    # somewhat dynamic and can adapt to different 
    # property types.

    try:
        self[self.cid] = pointer.path_resolve(PROP_PATHS[self.prop_type])
        self.id_properties_ensure()
        property_manager = self.id_properties_ui(self.cid)
        float_limit = sys.float_info.max 

        match self.prop_type:
            case 'LOCATION':
               property_manager.update(subtype='TRANSLATION', min=-float_limit, max=float_limit)
            case 'ROTATION':
               property_manager.update(subtype='EULER', min=-float_limit, max=float_limit)
            case 'SCALE':
               property_manager.update(subtype='XYZ', min=-float_limit, max=float_limit)
            case 'COLOR':
               property_manager.update(subtype='COLOR')
            case 'POWER':
               property_manager.update(subtype='POWER', min=-float_limit, max=float_limit)
            case 'FOCAL':
               property_manager.update(subtype='DISTANCE_CAMERA')

    except AttributeError:
        self[self.cid] = None


class RP_PG_CustomOverride(PropertyGroup):
    """Custom overrides for a render job."""

    def __repr__(self) -> str:
        return self.__str__()
    
    def __str__(self) -> str:
        return f'Custom Override: "{self.name}"'

    def set_id(self) -> str:
        """Generate ID for this custom override."""

        self.cid = str(uuid4())
        return self.cid


    def to_sample(self) -> None | str:
        """Generate code sample from settings."""
    
        match self.kind:
            case 'CUSTOM':
                sample = self.path
            case 'bpy.data.objects':
                sample = 'bpy.context.scene.objects'
            case _:
                sample = self.kind

        try:
            match self.kind:
                case 'bpy.data.collections':
                    sample += f'["{self.col_pointer.name}"]'
                case 'bpy.data.objects':
                    sample += f'["{self.obj_pointer.name}"]'
                case 'bpy.data.lights':
                    sample += f'["{self.lights_pointer.name}"]'
                case 'bpy.data.cameras':
                    sample += f'["{self.cameras_pointer.name}"]'

            if self.prop_type != 'CUSTOM':
                sample += f'.{PROP_PATHS[self.prop_type]}'
            else:
                sample += f'.{self.path}'

        except (KeyError, AttributeError):
            return None

        match self.prop_type:
            case 'CUSTOM':
                sample += f' = {self.data}'
            case 'LOCATION' | 'SCALE' | 'ROTATION' | 'COLOR':
                data = [i for i in self[self.cid]]
                sample += f' = {data}'
            case 'VISIBLE':
                sample += f' = {not self[self.cid]}'
            case _:
                sample += f' = {self[self.cid]}'

        return sample


    path: StringProperty(
        name="Datapath", description="Datapath to property", default=""
    )

    data: StringProperty(name="Data", description="Data to use", default="")

    cid: StringProperty(name="ID", default="")

    name: StringProperty(
        name="Name", description="Override Name", default="New Custom Override"
    )

    enabled: BoolProperty(
        name="Enabled", description="Enable this override", default=True
    )

    kind: EnumProperty(
        name="Type",
        description="Datablock selection",
        items=(
            ("bpy.data.objects", "Objects", "", 'OBJECT_DATAMODE', 0), 
            ("bpy.data.cameras", "Cameras", "", 'OUTLINER_OB_CAMERA', 1), 
            ("bpy.data.lights", "Lights", "", 'OUTLINER_OB_LIGHT', 2), 
            ("bpy.data.collections", "Collections", "", 'OUTLINER_COLLECTION', 3), 
            None,
            ("CUSTOM", "Custom", "", 'SCRIPT', 4)),
        update=store_id,
    )

    obj_pointer: PointerProperty(
        name="Datablock Pointer",
        type=bpy.types.Object,
        update=store_id,
        poll=lambda s, o: o.type == 'MESH'
    )

    col_pointer: PointerProperty(
        name="Datablock Pointer",
        type=bpy.types.Collection,
        update=store_id,
    )

    lights_pointer: PointerProperty(
        name="Datablock Pointer",
        type=bpy.types.Light,
        update=store_id,
    )

    cameras_pointer: PointerProperty(
        name="Datablock Pointer",
        type=bpy.types.Camera,
        update=store_id,
    )

    prop_type: EnumProperty(
        name="Property",
        description="Datablock selection",
        items=prop_item,
        update=store_id,
    )

    custom_prop: StringProperty(name="Custom Prop", default="")

# ------------------------------------------------------------------------------
# Helper functions for Render job
# ------------------------------------------------------------------------------


def passes_items(self, context) -> list[tuple]:
    """List of items for the passes enum."""

    batch_list = context.scene.renderplus.batch.jobs
    index = context.scene.renderplus.batch.index
    engine = batch_list[index].scene.render.engine

    items = [
        ("NONE", "No changes", ""),
        ("use_pass_z", "Z", ""),
        ("use_pass_mist", "Mist", ""),
    ]

    match engine:
        case "CYCLES":
            items += [
                None,
                ("use_pass_position", "Position", ""),
                ("use_pass_normal", "Normal", ""),
                ("use_pass_vector", "Vector", ""),
                ("use_pass_uv", "UV", ""),
                ("use_pass_denoising_store_passes", "Denoising Data", ""),
                ("use_pass_object_index", "Object Index", ""),
                ("use_pass_material_index", "Material Index", ""),
                ("use_pass_debug_sample_count", "Sample Count (Debug)", ""),
                ("use_pass_diffuse_direct", "Diffuse Direct", ""),
                ("use_pass_diffuse_indirect", "Diffuse Indirect", ""),
                ("use_pass_diffuse_color", "Diffuse Color", ""),
                ("use_pass_glossy_direct", "Glossy Direct", ""),
                ("use_pass_glossy_indirect", "Glossy Indirect", ""),
                ("use_pass_glossy_color", "Glossy Color", ""),
                ("use_pass_transmission_direct", "Transmission Direct", ""),
                ("use_pass_transmission_indirect", "Transmission Indirect", ""),
                ("use_pass_transmission_color", "Transmission Color", ""),
                ("use_pass_volume_direct", "Volume Direct", ""),
                ("use_pass_volume_indirect", "Volume Indirect", ""),
                ("use_pass_emit", "Emission", ""),
                ("use_pass_enviroment", "Enviroment", ""),
                ("use_pass_shadow", "Shadow", ""),
                ("use_pass_ambient_occlusion", "Ambient Occlusion", ""),
                ("use_pass_cryptomatte_object", "Cryptomatte Object", ""),
                ("use_pass_cryptomatte_material", "Cryptomatte Material", ""),
                ("use_pass_cryptomatte_asset", "Cryptomatte Asset", ""),
            ]

        case "BLENDER_EEVEE" | "BLENDER_EEVEE_NEXT" :
            items += [
                None,
                ("use_pass_normal", "Normal", ""),
                ("use_pass_diffuse_direct", "Diffuse Light", ""),
                ("use_pass_diffuse_color", "Diffuse Color", ""),
                ("use_pass_glossy_direct", "Specular Light", ""),
                ("use_pass_glossy_color", "Specular Color", ""),
                ("use_pass_volume_direct", "Volume Light", ""),
                ("use_pass_emit", "Emission", ""),
                ("use_pass_enviroment", "Enviroment", ""),
                ("use_pass_shadow", "Shadow", ""),
                ("use_pass_ambient_occlusion", "Ambient Occlusion", ""),
                ("use_pass_cryptomatte_object", "Cryptomatte Object", ""),
                ("use_pass_cryptomatte_material", "Cryptomatte Material", ""),
                ("use_pass_cryptomatte_asset", "Cryptomatte Asset", ""),
            ]

    return items


def is_format_optional(file_format: str) -> bool:
    """Check if a file format is optional."""

    return file_format in (
        "HDR",
        "TIFF",
        "EXR",
        "MULTILAYER",
        "MPEG",
        "AVICODEC",
        "QUICKTIME",
        "CINEON",
        "DPX",
        "DDS",
    )


def fill_from_scene(self, context: Context) -> None:
    """Populate all fields for render job from scene data."""

    batch_list = context.scene.renderplus.batch.jobs
    index = context.scene.renderplus.batch.index

    if batch_list[index].use_external:
        return

    scene = batch_list[index].scene

    try:
        batch_list[index].camera = scene.camera
    except AttributeError:
        pass

    try:
        batch_list[index].world = scene.world
    except AttributeError:
        pass


def check_job_name(name: str) -> str:
    """Make sure the job's name is unique."""

    def check_duplicate(i: int, name_to_check: str) -> str:
        """Check name for index i."""

        if name_to_check not in seen:
            return name_to_check
        else:
            i += 1
            return check_duplicate(i, f"{name}.{i:0>3}")

    batch = bpy.context.scene.renderplus.batch.jobs
    seen = set()
    i = 0

    [seen.add(job.name) for job in batch if job.name not in seen]
    return check_duplicate(i, name)


def set_job_name(self, new_value, curr_value, is_set) -> str:
    """Wrapper to call check_job_name."""

    if new_value == curr_value:
        return new_value

    return check_job_name(new_value)


def default_job_name() -> str:
    """Return the default name for a job."""

    return check_job_name("New Render Job")


def get_gpus(self, context) -> list:
    """Get list of available GPUs."""

    addons = bpy.context.preferences.addons
    prefs = addons["cycles"].preferences
    dev_type = prefs.get_compute_device_type()
    devices = prefs.get_devices_for_type(dev_type)
    items = []
    default = [("0", "NO_GPU", "No GPU")]

    for device in devices:

        # Skip CPUs
        if device.type == "CPU":
            continue

        items.append((device.id, device.name, ""))

    return items or default


# ------------------------------------------------------------------------------
# Render job
# ------------------------------------------------------------------------------


class RP_PG_RenderJob(PropertyGroup):
    """Render job."""

    def device_items(self, context) -> list:
        local = (utils.prefs().batch_server_location == 'LOCAL')

        items = [
            ("DEFAULT", "Don't Change", ""),
            ("USE_ALL", "Use all devices", ""),
            ("CPU_ONLY", "CPU Only", ""),
            ("ALL_GPU", "All GPUs", ""),
        ]

        if local:
            items += ("SINGLE_GPU", "Single GPU", ""),

        return items


    # --------------------------------------------------------------------------
    # Basic properties

    name: StringProperty(
        name="Name",
        description="A name to identify this job in the queue",
        default="Untitled Render Job",
        set_transform=set_job_name,
    )

    scene: PointerProperty(
        name="Scene",
        description="Scene to render",
        type=bpy.types.Scene,
        update=fill_from_scene,
    )

    camera: PointerProperty(
        name="Camera",
        description="Camera to use in this render",
        poll=lambda _, o: o.type == "CAMERA",
        type=bpy.types.Object,
    )

    world: PointerProperty(
        name="World", description="World to use in this render", type=bpy.types.World
    )

    layer: StringProperty(
        name="Layer",
        description="Specific view layer to render. Leave blank to use all",
        default="",
    )

    enabled: BoolProperty(
        name="Enable this render job",
        description="Process this render job",
        default=True,
    )

    hooks: CollectionProperty(type=RP_PG_Hook)

    passes: CollectionProperty(type=RP_PG_RenderPass)
    passes_index: IntProperty(name="Index of current render pass", default=0)

    # --------------------------------------------------------------------------
    # External blend

    use_external: BoolProperty(
        name="Use external blendfile",
        description="Use a external blend file for this job",
        default=False,
    )

    blend_file: StringProperty(
        name="Blend File",
        description="Path to external blendfile",
        default="",
        update=external.fill_props,
    )

    ex_scene: StringProperty(name="Scene", description="Scene to render", default="")

    ex_camera: StringProperty(
        name="Camera", description="Camera to use in this render", default=""
    )

    ex_world: StringProperty(
        name="World", description="World to use in this render", default=""
    )

    ex_layer: StringProperty(
        name="View Layer", description="View Layer to use in this render", default=""
    )

    ex_pre_job_script: StringProperty(
        name="Pre-render script",
        description="Script to run before rendering",
        default="",
    )

    # --------------------------------------------------------------------------
    # Frames and animation

    animation: BoolProperty(
        name="Animation",
        description="Render an animation instead of a still image",
        default=False,
    )

    frame_custom: BoolProperty(
        name="Custom Frame",
        description="Use a custom frame or frame range for this render",
        default=False,
    )

    frames: StringProperty(name="Frame", description="Frame(s) to render", default="0")

    frame_start: IntProperty(
        name="Start Frame", description="First frame of the animation range", default=0
    )

    frame_end: IntProperty(
        name="End Frame", description="Final frame of the animation range", default=250
    )

    frame_jump: IntProperty(
        name="Frame Jump",
        description="Number of frames to jump forward after each rendered frame",
        default=1,
    )

    # --------------------------------------------------------------------------
    # Output

    output: StringProperty(
        name="Output",
        description="Filename to output to",
        subtype="FILE_PATH",
        options={'PATH_SUPPORTS_BLEND_RELATIVE'},
        default="",
    )

    use_custom_format: BoolProperty(
        name="Custom Format",
        description="Use a specific file format for this render job",
        default=False,
    )

    format: EnumProperty(
        name="Format",
        description="Format to use in the render job",
        items=(
            ("TGA", "Targa", ""),
            ("IRIS", "Iris", ""),
            ("JPEG", "Jpeg", ""),
            ("MOVIE", "Movie", ""),
            ("RAWTGA", "Raw Targa", ""),
            ("AVIRAW", "Raw AVI", ""),
            ("AVIJPEG", "Jpeg AVI", ""),
            ("PNG", "PNG", ""),
            ("BMP", "BMP", ""),
            ("HDR", "Radiance HDR", ""),
            ("TIFF", "TIFF", ""),
            ("EXR", "OpenEXR", ""),
            ("MULTILAYER", "OpenEXR Multilayer", ""),
            ("MPEG", "MPEG", ""),
            ("QUICKTIME", "Quicktime", ""),
            ("CINEON", "Cineon", ""),
            ("DPX", "DPX", ""),
            ("DDS", "DDS", ""),
        ),
        default="PNG",
    )

    use_passes: EnumProperty(
        name="Render Passes",
        description="Render Passes to enable for this job",
        items=passes_items,
        default=0,
    )

    cycles_samples: IntProperty(
        name="Samples",
        description=(
            "Samples to render. Set to 0 to use" " the value set in the scene"
        ),
        default=0,
        min=0,
        max=10000,
    )

    threads: IntProperty(
        name="Threads",
        description="Threads to use while rendering",
        default=0,
        min=0,
        max=64,
    )

    use_turbotools: BoolProperty(
        name="Render with TurboTools",
        description="Render using the TurboTools addon",
        default=False,
    )

    # --------------------------------------------------------------------------
    # Render size

    size_custom: BoolProperty(
        name="Custom Size",
        description="Use a custom render size for this job",
        default=False,
    )

    size_x: IntProperty(
        name="Width",
        description="Custom render width for this job",
        default=1920,
        min=4,
    )

    size_y: IntProperty(
        name="Height",
        description="Custom render height for this job",
        default=1080,
        min=4,
    )

    use_section: BoolProperty(
        name="Render section",
        description="Render only a section of the image",
        default=False,
    )

    section_x: FloatProperty(
        name="X",
        description="Starting X coordinate for section render",
        default=0,
        min=0,
        max=0.99,
    )

    section_y: FloatProperty(
        name="Y",
        description="Starting Y coordinate for section render",
        default=0,
        min=0,
        max=0.99,
    )

    section_width: FloatProperty(
        name="Width", description="Width for section render", default=1, min=0.01, max=1
    )

    section_height: FloatProperty(
        name="Height",
        description="Height for section render",
        default=1,
        min=0.01,
        max=1,
    )

    device: EnumProperty(
        name="Compute Device",
        description="Compute device to render with",
        items=device_items,
    )

    gpu: IntProperty(
        name="GPU #", description="GPU to use (by number)", min=1, default=0
    )

    gpu_local: EnumProperty(
        name="GPU",
        description="GPU to use",
        items=get_gpus,
    )

    # --------------------------------------------------------------------------
    # Custom overides

    custom_overrides: CollectionProperty(type=RP_PG_CustomOverride)

    custom_overrides_index: IntProperty(
        name="Index of current custom override", default=0
    )

    show_override_sample: BoolProperty(
        name="Show Generated Python code",
        description="Show the generated Python code for this custom override",
        default=False,
    )

    use_pre_job_script: BoolProperty(
        name="Run script before rendering",
        description="Run a Python script in the blend file before rendering",
        default=False,
    )

    pre_job_script: PointerProperty(
        name="Run before job",
        description="Python script to run before the render job",
        type=bpy.types.Text,
    )

    # --------------------------------------------------------------------------
    # Running state

    progress: FloatProperty(
        name="Progress",
        description="Progress of the current render job",
        default=0,
        min=0,
        max=100,
        subtype="PERCENTAGE",
    )


# ------------------------------------------------------------------------------
# Batch Settings
# ------------------------------------------------------------------------------


class RP_PG_BatchSettings(PropertyGroup):
    """Hold all Batch data."""

    jobs: CollectionProperty(type=RP_PG_RenderJob)

    pre_batch_hook: PointerProperty(type=RP_PG_Hook)
    post_batch_hook: PointerProperty(type=RP_PG_Hook)
    pre_job_hook: PointerProperty(type=RP_PG_Hook)
    post_job_hook: PointerProperty(type=RP_PG_Hook)

    index: IntProperty(name="Index of current render job in list", default=0)

    # --------------------------------------------------------------------------
    # Batch Renders Settings

    use_rss: BoolProperty(
        name="Use RSS",
        description="Generate a RSS feed to monitor batch process",
        default=False,
    )

    write_logs: BoolProperty(
        name="Write log files",
        description="Write log files for each render job",
        default=False,
    )

    use_global_size: BoolProperty(
        name="Global size",
        description="Override size for all render jobs",
        default=False,
    )

    global_size_x: IntProperty(
        name="Width",
        description="Custom render width for all jobs",
        default=1920,
        min=4,
    )

    global_size_y: IntProperty(
        name="Height",
        description="Custom render height for all jobs",
        default=1080,
        min=4,
    )

    use_global_percentage: BoolProperty(
        name="Global Percentage",
        description="Override size percentage for all jobs",
        default=False,
    )

    global_percentage: IntProperty(
        name="Percentage",
        description="Custom size percentage for all jobs",
        subtype="PERCENTAGE",
        min=1,
        soft_max=100,
        max=10000,
        default=100,
    )

    ignore_border: BoolProperty(
        name="Ignore render border",
        description="Ignore render border for batch",
        default=False,
    )

    use_term: BoolProperty(
        name="Use terminal",
        description=(
            "Run the batch inside a terminal\nNot available"
            " when rendering over a network"
        ),
        default=False,
    )

    poweroff: EnumProperty(
        name="Power Off",
        description="Power off when batch is finished succesfully.",
        items=(
            ("DISABLED", "Disabled", "Let the computer on"),
            ("SLEEP", "Sleep", "Set computer to sleep"),
            ("SHUTDOWN", "Shut down", "Turn off computer"),
        ),
        default="DISABLED",
    )

    notify_desktop: BoolProperty(
        name="Desktop Notifications",
        description="Notify me using the Desktop",
        default=False,
    )

    notify_sound: BoolProperty(
        name="Sound", description="Notify me using Sound", default=False
    )

    notify_mail: BoolProperty(
        name="Mail", description="Notify me using Email", default=False
    )

    overwrite: BoolProperty(
        name="Overwrite",
        description="Overwrite files when rendering. Otherwise rename them.",
        default=True,
    )

    skip_existing: BoolProperty(
        name="Skip Existing",
        description="Skip existing files and don't render them",
        default=False,
    )

    parallel: IntProperty(
        name="Parallel Renders",
        description="Number of render jobs to run in parallel",
        default=1,
        min=1,
        max=multiprocessing.cpu_count(),
    )

    disable_addons: BoolProperty(
        name="Disable addons",
        description="Disable all enabled addons while rendering",
        default=False,
    )

    use_rename: BoolProperty(
        name="Remove frame number in filename",
        description="Remove frame number in rendered file filename",
        default=False,
    )

    fix_layer_nodes: BoolProperty(
        name="Change layer nodes to job layer",
        description="Change the active view layer in layer nodes to the one in set in the job",
        default=True,
    )

    # -------------------------------------------------------------------------
    # Batch Renders UI

    has_external: BoolProperty(
        name="Batch has external jobs",
        description="True if the batch has external render jobs",
        default=False,
    )

    ui_job_tab: EnumProperty(
        name="Tab for render job settings",
        description="Current tab for render job settings",
        items=(
            ("SCENE", "Scene", "Scene related overrides"),
            ("RENDER", "Render", "Rendering related overrides"),
            ("CUSTOM", "Custom", "Custom Overrides"),
        ),
        default="SCENE",
    )

    ui_settings_tab: EnumProperty(
        name="Tab for batch settings",
        description="Current tab for settings",
        items=(
            ("GENERAL", "General", "General settings"),
            ("ACTIONS", "Actions", "Callbacks to run in the batch"),
        ),
        default="GENERAL",
    )

    ui_log_tab: EnumProperty(
        name="Tab for batch log",
        description="Current tab for log",
        items=(
            ("JOB", "Job", "Stats for the selected job"),
            ("BATCH", "Batch", "Stats for the batch"),
        ),
        default="JOB",
    )
