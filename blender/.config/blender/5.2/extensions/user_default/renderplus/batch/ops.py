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

import logging
import os
import json
import subprocess as sp
import urllib.request
import threading
import copy
import http
import requests
import subprocess

import bpy
from bl_operators.presets import AddPresetBase
from bpy_extras.io_utils import ExportHelper

from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from typing import Callable

from ..single import utils

from ..server import poweroff
from ..server import notifications
from ..server import sound
from ..server import custom
from ..server.job import LocalJob
from ..single import notifications as old_notifications

from . import api
from . import state
from . import recipe
from . import files


log = logging.getLogger(__name__)


@classmethod
def ready_to_run(cls, context) -> bool:
    """Poll for when the batch list has jobs and no batch is running."""

    prefs = utils.prefs()

    if prefs.batch_server_location == "NETWORK":
        return (
            context.scene.renderplus.batch.jobs
            and state.mode != "RUNNING"
            and prefs.blender_path != ""
        )
    else:
        return context.scene.renderplus.batch.jobs and state.mode != "RUNNING"


@classmethod
def has_jobs(cls, context) -> bool:
    """Poll for when the batch list has jobs."""

    return context.scene.renderplus.batch.jobs


def current_job():
    """Get currently selected job."""

    index = bpy.context.scene.renderplus.batch.index
    return bpy.context.scene.renderplus.batch.jobs[index]


# ------------------------------------------------------------------------------
#  Open render folder
# ------------------------------------------------------------------------------


class RP_OT_OpenRenderFolder(Operator):
    """Open output folder in file browser."""

    bl_idname = "renderplus.batch_open_render_folder"
    bl_label = "Show output folder"
    poll = has_jobs

    def execute(self, context):

        output = current_job().output or context.scene.render.filepath
        output_folder = utils.sane_path(output)
        output_folder = os.path.dirname(output_folder)

        command = {
            "Linux": f"xdg-open {output_folder}",
            "Windows": f"explorer {output_folder}",
            "Darwin": f'open "{output_folder}"',
        }

        try:
            print(sp.run(command[utils.sys], shell=True, check=True))
        except sp.CalledProcessError:
            # Explorer returns with an error code even when it works fine
            if utils.sys != "Windows":
                self.report(
                    {"ERROR"},
                    ("Couldn't open render folder." " Please check output path"),
                )

        return {"FINISHED"}


# ------------------------------------------------------------------------------
#  Custom Frame explanation
# ------------------------------------------------------------------------------


class RP_OT_CustomFramePopup(Operator):
    """Useful information about custom frames"""

    bl_idname = "renderplus.custom_frame_popup"
    bl_label = "Info about custom frames"

    def execute(self, context):
        msg = (
            "Type a single number to render a single frame. "
            "Type a number with + or - to render a frame "
            "relative to the start and end frames. "
            "You can also render more than one frame separating "
            "them with a comma (eg. 1,2,5,8). "
            "Or render ranges of frames using the .. separator. "
            "(eg. 20..30, 50..120)"
        )

        popup = utils.popup("Custom Frames", msg)
        popup.show()

        return {"FINISHED"}


# ------------------------------------------------------------------------------
#  Clear Batch temp folder
# ------------------------------------------------------------------------------


class RP_OT_ClearBatchTemp(Operator):
    """Clear batch temporary folder."""

    bl_idname = "renderplus.batch_clear_tmp"
    bl_label = "Clear batch temp folder"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        here = os.path.dirname(__file__)
        folder = os.path.join(here, "..", "server", "temp")

        log.debug(f"Cleaning batch folder: {folder}")

        for a_file in os.listdir(folder):
            file_path = os.path.join(folder, a_file)

            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except OSError as e:
                msg = (
                    "There was an error while trying to clear the batch "
                    "temporary folder"
                )

                log.error(msg + str(e))
                self.report({"ERROR"}, msg)

                return {"CANCELLED"}

        self.report({"INFO"}, "Cleared batch temporary folder")
        return {"FINISHED"}


# ------------------------------------------------------------------------------
#  Get section from viewport
# ------------------------------------------------------------------------------


class RP_OT_GetBorderRenderFromViewport(Operator):
    """Get border render coordinates set in viewport."""

    bl_idname = "renderplus.batch_get_from_viewport"
    bl_label = "Set section coordinates from viewport"
    poll = ready_to_run

    def execute(self, context):
        job = current_job()
        settings = context.scene.render

        job.section_x = settings.border_min_x
        job.section_y = settings.border_min_y

        job.section_width = settings.border_max_x - settings.border_min_x
        job.section_height = settings.border_max_y - settings.border_min_y

        return {"FINISHED"}


# ------------------------------------------------------------------------------
#  Change outputs
# ------------------------------------------------------------------------------


class RP_OT_ChangeOutputs(Operator):
    """Change output paths across all render jobs."""

    bl_idname = "renderplus.batch_change_outputs"
    bl_label = "Change outputs in render jobs"
    bl_options = {"UNDO"}
    poll = ready_to_run

    def execute(self, context):

        for job in context.scene.renderplus.batch.jobs:
            job.output = recipe.make_output_path(job)
            state.mode = "NORMAL"

        return {"FINISHED"}


# ------------------------------------------------------------------------------
#  Toggle settings
# ------------------------------------------------------------------------------


class RP_OT_ToggleBatchMode(Operator):
    """Toggle settings in Batch panel."""

    bl_idname = "renderplus.batch_toggle_mode"
    bl_label = "Toggle the Batch panel ui mode"

    mode: EnumProperty(
        items=(
            ("NORMAL", "Normal", ""),
            ("SETTINGS", "Settings", ""),
            ("LOG", "Log", ""),
            ("OUTPUT_CHANGE", "Output Changer", ""),
            ("QUICK_BATCH", "Quick Batch", ""),
        ),
        default="NORMAL",
    )

    def execute(self, context):

        quicks = bpy.context.scene.renderplus.batch_ops.quick_batch

        if state.mode != self.mode:
            state.mode = self.mode
        else:
            state.mode = "NORMAL"

        if self.mode == "QUICK_BATCH" and not quicks.scenes:
            scene_quick = quicks.scenes.add()
            scene_quick.scene = context.scene

        return {"FINISHED"}


# -----------------------------------------------------------------------------
#  Custom overrides
# -----------------------------------------------------------------------------


class RP_OT_AddCustomOverride(Operator):
    """Add a custom override for a render job."""

    bl_idname = "renderplus.batch_add_custom_override"
    bl_label = "Add a Custom Override"
    poll = has_jobs

    def execute(self, context):
        customs = current_job().custom_overrides
        override = customs.add()
        override.set_id()

        return {"FINISHED"}


class RP_OT_RemoveCustomOverride(Operator):
    """Remove a custom override from a render job."""

    bl_idname = "renderplus.batch_remove_custom_override"
    bl_label = "Remove a Custom Override"
    poll = has_jobs

    def execute(self, context):
        customs = current_job().custom_overrides
        index = current_job().custom_overrides_index
        customs.remove(index)

        return {"FINISHED"}


class RP_OT_CloneOverride(Operator):
    """Duplicate override on all render jobs."""

    bl_idname = "renderplus.batch_clone_override"
    bl_label = "Clone custom override for all jobs"
    poll = has_jobs

    def execute(self, context):
        customs = current_job().custom_overrides
        index = current_job().custom_overrides_index
        batch_list = context.scene.renderplus.batch.jobs

        path = customs[index].path
        data = customs[index].data
        name = customs[index].name
        enabled = customs[index].enabled

        for job in batch_list:
            found = False

            # We don't have overrides
            if job.custom_overrides:
                job.custom_overrides.add()
                job.custom_overrides[0]["name"] = name
                job.custom_overrides[0]["enabled"] = enabled
                job.custom_overrides[0]["path"] = path
                job.custom_overrides[0]["data"] = data

                found = True
            else:
                # Loop through overrides to find the one
                for override in job.custom_overrides:
                    if "path" in override:
                        if override["path"] != path:
                            continue
                        else:
                            override["data"] = data
                            found = True

                # We didn't find the key
                if not found:
                    new_index = len(job.custom_overrides)
                    job.custom_overrides.add()
                    job.custom_overrides[new_index]["name"] = name
                    job.custom_overrides[new_index]["enabled"] = enabled
                    job.custom_overrides[new_index]["path"] = path
                    job.custom_overrides[new_index]["data"] = data

        self.report({"INFO"}, "Copied {0} to all render jobs".format(name))
        return {"FINISHED"}


class RP_OT_AddCustomOverridePreset(AddPresetBase, Operator):
    bl_idname = "renderplus.add_override_preset"
    bl_label = "Add a preset"
    preset_menu = "RP_MT_CustomOverridePresets"

    # Common variable used for all preset values
    preset_defines = [
        "batch = bpy.context.scene.renderplus.batch",
        "jobs = batch.jobs",
        "current = jobs[batch.index]",
    ]

    # Properties to store in the preset
    preset_values = ["current.custom_overrides"]

    # Directory to store the presets
    preset_subdir = "renderplus/overrides"


# ------------------------------------------------------------------------------
#  List manipulation
# ------------------------------------------------------------------------------


def default_output(scene, external=None):
    """Generate a default output string according to preferences."""

    prefs = utils.prefs()

    if external:
        filename = utils.base_filename(external.blend_file)
        name = "_" + filename if prefs.batch_output_blend else ""
        sce = "_" + external.ex_scene if prefs.batch_output_scene else ""

        if prefs.batch_output_camera and external.camera:
            cam = "_" + external.camera
        else:
            cam = ""
    else:
        name = utils.base_filename(bpy.data.filepath) or "Untitled"

        name = "_" + name if prefs.batch_output_blend else ""
        sce = "_" + scene.name if prefs.batch_output_scene else ""

        try:
            cam = "_" + scene.camera.name if prefs.batch_output_camera else ""
        except AttributeError:
            cam = ""

    output = prefs.batch_output_base + name + sce + cam
    return "//render" if output == "" else output


# ------------------------------------------------------------------------------
#  Start and Cancel
# ------------------------------------------------------------------------------


def polling_loop(callback: Callable = None) -> None:
    """Keep polling the server and storing the reply."""

    prefs = utils.prefs()
    settings = bpy.context.scene.renderplus

    # Number of times we have to get the same reply from the server
    # before we consider it "stuck"
    stuck_threshold = 10_800

    try:
        response = api.poll()
        state.reply = response
        # log.debug(f"Received from server: {json.dumps(response, indent=4)}\n")

        progress = -1

        for job in response["jobs"]:
            if job["status"] == "RUNNING":
                progress = job["progress"]
                break

        # Check if the server is stuck
        if state.reply == state.last_reply:
            state.same_replies += 1
            pre_render = progress == 0

            if state.same_replies > stuck_threshold and not pre_render:
                log.error(f"Received the same reply {stuck_threshold } times")
                return server_is_stuck()

        else:
            state.last_reply = response

            for i, job in enumerate(state.reply["jobs"]):
                try:
                    settings.batch.jobs[i].progress = job["progress"]
                except AttributeError:
                    pass

    except urllib.error.HTTPError as e:
        if e.code == 409:
            log.debug("Poll: No batch has been run.")
        else:
            log.debug(f"Poll Failed with status {e.code}. {e.reason}")

        return

    except urllib.error.URLError:
        log.debug("Poll Failed. Did the server crash?")
        log.debug("Resetting UI to normal")
        state.mode = "NORMAL"
        utils.force_redraw()

        return

    except ConnectionResetError:
        log.debug("Connection reset. Server was shutting down?")
        return

    except IndexError:
        log.debug("Switched to another Blendfile?")
        return

    finally:
        if callback:
            callback()
            settings.batch.poweroff = "DISABLED"

    if response['status'] == 'FINISHED':
        # Make sure all jobs are marked as done

        for job in settings.batch.jobs:
            if job.enabled:
                job.progress = 100

        for j in state.reply['jobs']:
            if j['status'] in ('QUEUED', 'RUNNING'):
                j['status'] = 'FINISHED'


    if response["status"] in ("FINISHED", "CANCELLED"):
        state.last_batch = copy.deepcopy(state.reply)
        utils.force_redraw()

        if not prefs.keep_alive:
            log.debug("Stopping server.")
            api.stop()

        return

    utils.force_redraw()
    interval = prefs.batch_refresh_interval
    timer = threading.Timer(interval, polling_loop, args=(callback,))
    timer.daemon = True
    timer.start()


def server_is_stuck():
    """Kill server if it got stuck."""

    log.error("Did Blender get stuck? There's been no progress for a long time...")
    log.error(f"Last reply was: {state.reply}")


def start():
    """Reset the state and start the batch."""

    api.start()

    settings = bpy.context.scene.renderplus.batch
    settings.ui_progress = 0
    state.mode = "RUNNING"
    state.last_batch = None
    state.reply = None
    state.last_reply = None
    state.same_replies = 0
    state.server_hanged = False


class RP_OT_CancelUpload(Operator):
    """Cancel file packing and upload for remote batch."""

    bl_idname = "renderplus.batch_cancel_packing"
    bl_label = "Cancel file upload"

    @classmethod
    def poll(self, context):
        return state.mode == "PACKING"

    def execute(self, context):
        state.packing_cancel = True

        self.report({"INFO"}, "File upload cancelled")
        return {"FINISHED"}


class RP_OT_CancelJob(Operator):
    """Cancel the currently running job."""

    bl_idname = "renderplus.batch_cancel_job"
    bl_label = "Cancel current render job"

    @classmethod
    def poll(self, context):
        return state.mode == "RUNNING"

    def execute(self, context):

        try:

            index = context.scene.renderplus.batch.index
            log.debug("Cancelling Batch")
            print(api.request(f"batch/jobs/{index}", "DELETE"))

        except urllib.error.HTTPError as e:
            print(f"Server replied with status: {e.code} {e.reason}")
            return {"CANCELLED"}

        except urllib.error.URLError:
            log.debug("Tried to cancel but no server is running")
            return {"FINISHED"}

        log.info("Cancelled render job\n")
        self.report({"WARNING"}, "Cancelled render job")
        return {"FINISHED"}


class RP_OT_CancelBatch(Operator):
    """Cancel a running batch"""

    bl_idname = "renderplus.cancel_batch"
    bl_label = "Cancel Batch Rendering"

    @classmethod
    def poll(self, context):
        return state.mode == "RUNNING"

    def execute(self, context):

        try:
            print(api.cancel())

        except urllib.error.HTTPError as e:
            print(f"Server replied with status: {e.code} {e.reason}")
            return {"CANCELLED"}

        except urllib.error.URLError:
            log.debug("Tried to cancel but no server is running")
            return {"FINISHED"}

        except http.client.RemoteDisconnected:
            log.debug("Tried to cancel but the server closed the conenction")
            return {"FINISHED"}

        log.info("Batch Rendering was CANCELLED\n")
        self.report({"WARNING"}, "Batch Render Cancelled")
        state.mode = "NORMAL"
        return {"FINISHED"}


def initial_checks() -> None:
    """Check if it's ok to start batch."""

    if not bpy.data.is_saved:
        raise ValueError("Please save this file before starting a batch\n")

    if bpy.data.is_dirty:
        try:
            bpy.ops.wm.save_mainfile()
            log.info("Autosaved blend file before starting batch.")
        except RuntimeError as e:
            log.error("Autosaving threw an error, %s", e)

    if utils.prefs().check_images and not utils.image_files_ok():
        raise ValueError(("Some image files are missing or have not " "been loaded"))


class RP_OT_StartBatch(Operator):
    """Start a batch render."""

    bl_idname = "renderplus.batch_start"
    bl_label = "Start Batch"
    retried = False
    poll = ready_to_run

    timer = None
    pack_filepath = None
    packing_done = False

    def err(self, error: str) -> None:
        """Print error message."""

        self.report({"ERROR"}, error)
        log.error(error)

    def modal(self, context, event):
        """Upload blendfiles to remote server."""

        if event.type == "TIMER":

            # Cancel file upload ----------------------------------------------
            if state.packing_cancel:
                log.debug("Cancelling file upload")
                self.cancel(context)

                return {"CANCELLED"}

            # Upload packed blend ------------------------------------
            elif not self.packing_done:
                path = self.blends.pop()

                if not os.path.isfile(path):
                    msg = f'Failed to find file to upload {path}'

                    log.error(msg)
                    self.report({'ERROR'}, msg)

                    return {"CANCELLED"}


                log.debug(f"Sending {self.pack_filepath}...")
                api.send_file(path)

                if not self.blends:
                    self.packing_done = True

                return {"PASS_THROUGH"}

            # If we are done packing and uploading, start ---------------------
            elif self.packing_done:
                self.cleanup(context)

                start()
                polling_loop()
                context.scene.renderplus.batch.index = 0

                log.info("Batch Rendering has started")
                self.report({"INFO"}, "Batch Render Started")

                return {"FINISHED"}

            else:
                return {"PASS_THROUGH"}

        else:
            return {"PASS_THROUGH"}

    def execute(self, context):

        try:
            initial_checks()
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            log.error(str(e))

            return {"CANCELLED"}

        settings = context.scene.renderplus.batch
        prefs = utils.prefs()

        use_log = prefs.use_log_server
        use_clear = prefs.use_clear_temp
        log_path = prefs.server_log_path

        api.address, api.port = utils.get_server_address()

        try:
            if not bpy.app.online_access:
                self.report({'ERROR'}, 'Please enable network access in system preferences for Render+ to run a batch.')
                return {'CANCELLED'}

        except AttributeError:
            # For older Blender versions
            pass


        if api.is_local() and not api.blender_bin_ok(prefs.blender_path):
                self.report({'ERROR'}, 'Failed to start batch.\nCustom Blender in addon preferences is incorrect.')
                return {'CANCELLED'}


        # Submit recipe to batch server ---------------------------------------
        try:
            encoded_recipe = recipe.build(settings)
            log.debug(f"Recipe for batch is {json.dumps(encoded_recipe)}")
            api.submit(encoded_recipe)

        # Server returns 400 --------------------------------------------------
        except urllib.error.HTTPError as e:
            if e.code == 409:
                name = json.loads(e.read().decode())["debug_message"]
                self.err(f"Already running a batch for file: {name}")
            else:
                log.error(f"Poll Failed with status {e.code}. {e.reason}")

            return {"CANCELLED"}

        # Errors in the server ------------------------------------------------
        except ConnectionRefusedError:
            self.err("Can't start server!")
            return {"CANCELLED"}

        # Server isn't running or responding ----------------------------------
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ConnectTimeout,
        ):
            if self.retried:
                self.err("The batch server could not be started")
                return {"CANCELLED"}

            elif api.socket_busy():
                self.err("Batch server is running but not responding")
                return {"CANCELLED"}

            elif api.is_local():
                log.debug(f"Starting server on port {api.port}")
                api.start_server(settings.use_term, use_log, use_clear, log_path)
                self.retried = True

                return self.execute(context)

            else:
                if api.is_local():
                    self.err("Could not start the server")
                else:
                    self.err(
                        (
                            "Could not find the batch server at "
                            f"{api.address}, port {api.port}"
                        )
                    )

                return {"CANCELLED"}

        # Incorrect output ----------------------------------------------------
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.err(
                (
                    "Can't find folder to render into. Please check "
                    f"this path: {e.args[0][1]}"
                )
            )

            return {"CANCELLED"}

        # Bad Permissions ----------------------------------------------------
        except PermissionError as e:
            self.err(
                (
                    "Not enough permissions to write render folder."
                    f"Please check this path: {e.args[0][1]}"
                )
            )

            return {"CANCELLED"}

        # Start server for local batches --------------------------------------
        if api.is_local():
            start()
            polling_loop()
            context.scene.renderplus.batch.index = 0

            log.info("Batch Rendering has started")
            self.report({"INFO"}, "Batch Render Started")

            return {"FINISHED"}

        # Start uploading for network batches ---------------------------------
        else:
            wm = context.window_manager
            self.timer = wm.event_timer_add(0.1, window=context.window)
            wm.modal_handler_add(self)

            self.blends = files.blends_in_recipe(encoded_recipe['jobs'])
            log.debug(f"Found {len(self.blends)} files")

            state.mode = "PACKING"
            self.report({"INFO"}, "Uploading files...")

            return {"RUNNING_MODAL"}

    def cancel(self, context):
        """Cancel file upload."""

        state.mode = "NORMAL"

        state.packing_proc.wait()
        state.packing_proc.kill()
        state.packing_proc = None

        self.cleanup(context)

    def cleanup(self, context):
        """Cleanup after file upload."""

        wm = context.window_manager
        wm.event_timer_remove(self.timer)

        state.packing_file = ""
        self.packing_done = False
        self.packing_cancel = False


# ------------------------------------------------------------------------------
#  Generate script
# ------------------------------------------------------------------------------


class RP_OT_GenerateScript(Operator, ExportHelper):
    """Generate Script."""

    bl_idname = "renderplus.generate_script"
    bl_label = "Generate script"

    filter_glob: StringProperty(
        default="",
        options={"HIDDEN"},
    )

    directory: StringProperty(subtype="DIR_PATH")

    filename_ext: str = ""

    @classmethod
    def poll(cls, context):
        return context.scene.renderplus.batch.jobs

    def execute(self, context):
        settings = context.scene.renderplus.batch

        # Make sure the folder is there
        os.makedirs(self.directory, exist_ok=True)

        # Get recipe
        data = recipe.build(settings)

        bat_data = ":: Generated by Render+\n\n"

        # For each render job:
        for job in data["jobs"]:
            # Get custom script data
            py_path = custom.filepath(
                bpy.data.filepath, job["name"], job['id'], utils.sys, self.directory
            )
            py_code = custom.build(job, data["settings"])

            # Write custom py script
            with open(py_path, "w") as stream:
                stream.write("\n".join(py_code))

            # Generate Blender command
            temp_job = LocalJob(job, data["settings"])
            temp_job.custom_py = py_path
            cmd = temp_job.generate_command()

            # Quote for windows
            cmd[0] = f'"{cmd[0]}"'
            cmd[2] = f'"{cmd[2]}"'

            if job["use_pre_job_script"]:
                cmd[5] = f'"{cmd[5]}"'
                cmd[7] = f'"{cmd[7]}"'
                cmd[13] = f'"{cmd[13]}"'
            else:
                cmd[4] = f'"{cmd[4]}"'
                cmd[6] = f'"{cmd[6]}"'
                cmd[12] = f'"{cmd[12]}"'

            # Add to bat list
            bat_data += " ".join(cmd)
            bat_data += "\n"

        # Write bat file
        bat_file = os.path.join(self.directory, "batch.bat")

        with open(bat_file, "w") as stream:
            stream.write(bat_data)

        return {"FINISHED"}


class RP_OT_ApplyRenderJob(Operator):
    """Apply render job settings to viewport."""

    bl_idname = "renderplus.apply_render_job"
    bl_label = "Apply Job Settings"

    @classmethod
    def poll(cls, context):
        return context.scene.renderplus.batch.jobs and not current_job().use_external

    def execute(self, context):
        job = current_job()

        # Apply view layer
        if job.layer:
            context.window.view_layer = job.scene.view_layers[job.layer]

        # Apply world
        if job.world:
            context.scene.world = job.world

        # Apply camera
        if job.camera:
            job.scene.camera = job.camera

        # Apply frames
        if job.frame_custom:
            context.scene.frame_start = job.frame_start
            context.scene.frame_end = job.frame_end
            context.scene.frame_step = job.frame_jump

            try:
                context.scene.frame_current = int(job.frames)
            except ValueError:
                context.scene.frame_current = int(job.frames.split(",")[0])

        return {"FINISHED"}