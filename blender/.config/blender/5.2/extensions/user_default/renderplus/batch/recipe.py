# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright Diego Gangl
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

"""Functions to create recipe."""

import bpy
import os
import re

from typing import Dict
from bpy.types import Scene, CollectionProperty, PropertyGroup

from ..single import utils
from . import external
from . import files



def reparse(text: str) -> str:
    """Try to parse UTF-8, otherwise try SHIFT_JIS."""

    try:
        bytes_code = text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # Try to parse as ShiftJIS (since this encoding
        # can creep into Blender).
        return text.encode('shift_jis').decode('shift_jis')


def fix_outputs(jobs: CollectionProperty) -> None:
    """Fix output paths in place (collisions, etc)."""

    def check_collision(path: str, index: int = 1) -> None:
        """Check and fix filepath collision."""

        if path in checked:
            # "extension" in this case refers to ###
            filepath, extension = os.path.splitext(path)

            # Remove "_00x" if it exists
            filepath = re.sub(r"_\d{3}_", "", filepath)

            new_path = f"{filepath}_{index:0>3}_{extension}"

            # Iterate until it collides no more
            index += 1
            check_collision(new_path, index)
        else:
            checked.append(path)

    checked = []
    prefs = utils.prefs()

    for i, job in enumerate(jobs):

        if not job.enabled or not job.output:
            checked.append("")
            continue

        test_path = job.output.replace("#", "")
        test_path = bpy.path.abspath(test_path)
        test_path = os.path.dirname(test_path)

        # Directory checks
        if not os.path.isdir(test_path):
            if not prefs.batch_new_dirs:
                raise FileNotFoundError((i, test_path))

            try:
                os.makedirs(test_path)
            except OSError:
                raise FileNotFoundError((i, test_path))

        if not os.access(test_path, os.W_OK):
            raise PermissionError((i, test_path))

        # Corner Case: Sometimes a path ends with .001 and no
        # file extension. We should not remove that 001 beacuse
        # it will lead to duplicate output paths
        clean_path = re.sub(r"\.\d{3}$", "", job.output)

        if not bpy.context.scene.render.use_overwrite:
            check_collision(clean_path)
        else:
            checked.append(job.output)

    # Set the paths
    for i, job in enumerate(jobs):
        if job.enabled:
            try:
                job.output = checked[i]
            except IndexError:
                pass


def make_output_path(job: PropertyGroup) -> str:
    """Generate default output path."""

    def add_suffix(suffix_type: str, filename: str) -> str:
        """Add sufixes according to job data"""

        separator = "_" if filename else ""

        if suffix_type == "NONE":
            return ""

        elif suffix_type == "FILENAME":
            if job.use_external:
                name = utils.base_filename(job.blend_file)
            else:
                name = utils.base_filename(bpy.data.filepath) or "Untitled"

            return separator + name

        elif suffix_type == "SCENE" and job.scene:
            return separator + job.scene.name

        elif suffix_type == "CAMERA" and job.camera:
            return separator + job.camera.name

        elif suffix_type == "VIEWLAYER" and job.layer:
            return separator + job.layer
        else:
            return ""

    settings = bpy.context.scene.renderplus.batch_ops.output_change
    directory = settings.base_directory

    if settings.subdirs_scene:
        directory = os.path.join(directory, job.scene.name)

    if settings.subdirs_layer:
        directory = os.path.join(directory, job.layer)

    if settings.subdirs_cam:
        try:
            directory = os.path.join(directory, job.camera.name)
        except AttributeError:
            # No cameras in the scene
            pass

    filename = settings.base_filename
    filename += add_suffix(settings.name_suffix_01, filename)
    filename += add_suffix(settings.name_suffix_02, filename)
    filename += add_suffix(settings.name_suffix_03, filename)

    return os.path.join(directory, filename)


def check_camera(camera: str, scene: Scene) -> str:
    """Check a camera exists and return its name."""

    if camera in scene.objects and scene.objects[camera].type == "CAMERA":
        return camera
    elif camera == "":
        return ""
    else:
        return scene.camera.name


def script_name(script) -> None | str:

    try:
        return script.name
    except AttributeError:
        return None


def build_job(index: int, job: PropertyGroup, hooks: Dict, packed: dict) -> Dict:
    """Build a render job dict."""

    prefs = utils.prefs()
    scene = job.scene

    job_data = {
        "enabled": job.enabled,
        "id": index,
        "name": reparse(job.name),
        "external": job.use_external,
        "animated": job.animation,
        "threads": job.threads,
        "hooks": hooks,
        "use_pre_job_script": job.use_pre_job_script,
        "render_passes": [],
        "custom_overrides": [],
    }

    # Custom Size for render job
    if job.size_custom:
        job_data["size"] = (job.size_x, job.size_y)
    elif not job.use_external:
        job_data["size"] = (scene.render.resolution_x, scene.render.resolution_y)
    else:
        job_data["size"] = ""

    # Blend file
    if job.use_external:
        output = reparse(job.output or external.get_default_output(job, job.ex_scene))
        job_data["blend_file"] = ''
        job_data["filename"] = reparse(files.get_name(job.blend_file))
        job_data["scene"] = reparse(job.ex_scene)
        job_data["camera"] = reparse(job.ex_camera)
        job_data["world"] = reparse(job.ex_world)
        job_data["layer"] = reparse(job.ex_layer)
        job_data["engine"] = external.find_engine(job, job.ex_scene)
    else:
        cam = reparse(job.camera.name) if job.camera else ""
        output = reparse(job.output or scene.render.filepath)
        job_data["blend_file"] = ''
        job_data["filename"] = reparse(files.get_name(bpy.data.filepath))
        job_data["scene"] = reparse(job.scene.name)
        job_data["camera"] = reparse(check_camera(cam, scene))
        job_data["world"] = reparse(job.world.name if job.world else "")
        job_data["layer"] = job.layer
        job_data["engine"] = job.scene.render.engine

    if prefs.batch_server_location == "NETWORK":
        blend = job.blend_file or bpy.data.filepath
        destination = packed.get(blend, '')

        if destination:
            files.pack(blend, destination)
            job_data['blend_file'] = destination
    else:
        blend = job.blend_file or bpy.data.filepath
        job_data['blend_file'] = blend

    # Relative paths
    if output.startswith("//"):
        job_data["output"] = bpy.path.abspath(output)
    else:
        job_data["output"] = output

    # Use extension
    job_data["add_extension"] = (
        int(scene.render.use_file_extension) if not job.use_external else 1
    )

    # Animation data
    if job.frame_custom or job.use_external:
        job_data["frames"] = job.frames
        job_data["frame_start"] = job.frame_start
        job_data["frame_end"] = job.frame_end
        job_data["frame_jump"] = job.frame_jump
    else:
        job_data["frames"] = str(scene.frame_current)
        job_data["frame_start"] = scene.frame_start
        job_data["frame_end"] = scene.frame_end
        job_data["frame_jump"] = 1

    # Autodetect animation. If the user passes x..y or x,y
    # frames, we will end up rendering multiple frames.
    if any(x in job.frames for x in {"..", ","}) and not job.animation:
        job_data["animated"] = True
        job_data["split_frames"] = True
    else:
        job_data["split_frames"] = False

    # Custom format
    if job.use_custom_format:
        job_data["format"] = job.format
    elif not job.use_external:
        job_data["format"] = scene.render.image_settings.file_format
    else:
        job_data["format"] = ""

    # Custom section render
    job_data["section"] = {
        "enabled": job.use_section,
        "x": job.section_x,
        "y": job.section_y,
        "width": job.section_width,
        "height": job.section_height,
    }

    job_data["cycles"] = {
        "samples": job.cycles_samples,
        "device": job.device,
    }

    if prefs.batch_server_location == "NETWORK":
        job_data["cycles"]["device_number"] = job.gpu
    elif job.gpu_local:
        job_data["cycles"]["device_number"] = job.gpu_local
    else:
        job_data["cycles"]["device_number"] = ''

    for custom in job.custom_overrides:
        if code := custom.to_sample():
            job_data["custom_overrides"].append({
                "enabled": custom.enabled,
                "code": code,
            })

    if job.use_pre_job_script:
        if job.use_external:
            job_data["pre_job_script"] = job.ex_pre_job_script
        else:
            job_data["pre_job_script"] = script_name(job.pre_job_script)

    job_data["use_turbotools"] = job.use_turbotools

    for rpass in job.passes:
        if rpass.engine not in (job_data["engine"], "ALL") or not rpass.enabled:
            continue

        if not rpass.output:
            rpass.output = f"//passes{os.sep}{rpass.name}"

        folder = os.path.dirname(rpass.output)
        filename = os.path.basename(rpass.output)

        job_data["render_passes"].append(
            {
                "key": rpass.key,
                "folder": folder,
                "filename": filename,
                "socket": rpass.socket,
            }
        )

    return job_data


def build(settings: PropertyGroup) -> Dict:
    """Build recipe for a batch."""

    jobs = settings.jobs
    prefs = utils.prefs()
    packed = {}

    if prefs.batch_server_location != "NETWORK":
        fix_outputs(jobs)
    else:
        packed = files.tmp_map(jobs)

    # Render job hooks
    job_hooks = {
        "PRE_JOB": [
            {
                "enabled": settings.pre_job_hook.enabled,
                "cmd": settings.pre_job_hook.command,
                "type": settings.pre_job_hook.kind,
                "script": script_name(settings.pre_job_hook.script),
            }
        ],
        "POST_JOB": [
            {
                "enabled": settings.post_job_hook.enabled,
                "cmd": settings.post_job_hook.command,
                "type": settings.post_job_hook.kind,
                "script": script_name(settings.post_job_hook.script),
            }
        ],
    }

    blender_bin = prefs.blender_path or bpy.app.binary_path

    rss = {
        "enabled": settings.use_rss,
    }

    global_percentage = {
        "enabled": settings.use_global_percentage,
        "value": settings.global_percentage,
    }

    global_size = {
        "enabled": settings.use_global_size,
        "value": (settings.global_size_x, settings.global_size_y),
    }

    hooks = {
        "PRE_BATCH": [
            {
                "enabled": settings.pre_batch_hook.enabled,
                "cmd": settings.pre_batch_hook.command,
                "type": settings.pre_batch_hook.kind,
                "script": script_name(settings.pre_batch_hook.script),
            }
        ],
        "POST_BATCH": [
            {
                "enabled": settings.post_batch_hook.enabled,
                "cmd": settings.post_batch_hook.command,
                "type": settings.post_batch_hook.kind,
                "script": script_name(settings.post_batch_hook.script),
            }
        ],
    }

    power_off = {
        "enabled": (settings.poweroff != "DISABLED"),
        "action": settings.poweroff,
    }

    notifications = {
        "desktop": settings.notify_desktop,
        "sound": {
            "enabled": settings.notify_sound,
            "file": prefs.sound_file,
            "volume": prefs.sound_volume,
        },
        "mail": {
            "enabled": settings.notify_mail,
            "user": prefs.mail_user,
            "pass": prefs.mail_password,
            "ssl": prefs.mail_ssl,
            "to": prefs.mail_to,
            "server": prefs.mail_server,
        },
    }

    return {
        "name": bpy.data.filepath,
        "version": 3.1,
        "settings": {
            "OS": utils.sys,
            "type": prefs.batch_server_location,
            "blender_version": bpy.app.version[0],
            "rss": rss,
            "global_percentage": global_percentage,
            "global_size": global_size,
            "write_log": settings.write_logs,
            "ignore_border": settings.ignore_border,
            "overwrite": settings.overwrite,
            "skip_existing": settings.skip_existing,
            "blender_bin": blender_bin,
            "parallel_jobs": settings.parallel,
            "disable_addons": settings.disable_addons,
            "use_rename": settings.use_rename,
            "fix_layer_nodes": settings.fix_layer_nodes,
        },
        "hooks": hooks,
        "poweroff": power_off,
        "notifications": notifications,
        "jobs": [build_job(i, job, job_hooks, packed=packed) for i, job in enumerate(jobs)],
    }
