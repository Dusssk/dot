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

"""Callbacks for Render+ main functionality."""

import logging
import os
import subprocess
import urllib

import bpy
from bpy.app.handlers import persistent
from bpy.types import Scene

from . import utils
from . import stats
from . import notifications as old_notifications
from ..batch import state
from ..batch import api
from ..batch import ops
from ..server import poweroff
from ..server import notifications
from ..server import sound


log = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
#  Functions
# ------------------------------------------------------------------------------


def autosave() -> None:
    """Auto-save image renders."""

    scene = bpy.context.scene
    use_extension = scene.render.use_file_extension
    use_overwrite = scene.render.use_overwrite

    output_path = bpy.path.abspath(scene.render.filepath)

    # There's a chance the path won't have a filename, so add a default one
    if os.path.basename(output_path) == "":
        output_path = os.path.join(output_path, "render")

    extension = scene.render.file_extension
    base_name = os.path.splitext(output_path)[0]

    result = bpy.data.images["Render Result"]

    if scene.render.is_movie_format:
        # Blender already autosaves animations
        return False

    if not result:
        # Saving error
        log.info("Could not autosave render!")
        return False

    if use_extension:
        # Make sure the file has an extension
        final_path = base_name + extension
    elif os.path.splitext(output_path)[1]:
        final_path = base_name + os.path.splitext(output_path)[1]
    else:
        final_path = base_name

    if not use_overwrite:
        # Add duplicate number to filename
        # so it doesn't get overwritten
        dupe_number = 1

        while os.path.isfile(final_path):
            # Deconstruct again
            base, ext = os.path.splitext(final_path)

            # Removing the old number
            old_dupe = "_#" + str(dupe_number - 1)
            base = base.replace(old_dupe, "")

            final_path = str.format("{0}_#{1}{2}", base, dupe_number, ext)

            dupe_number += 1

    result.save_render(final_path)
    log.debug(f"Autosaved to {final_path}")


def run_hook(when: str) -> None:
    """Run post/pre hooks."""

    if when == "POST":
        settings = bpy.context.scene.renderplus.post_settings
    else:
        settings = bpy.context.scene.renderplus.pre_settings

    if settings.option == "command":
        log.debug(f"Running command: {settings.command} at {when}")
        return subprocess.Popen(settings.command, shell=True)
    else:
        log.debug(f"Running script: {settings.script} at {when}")
        log.debug(settings.script.as_string())

        code = settings.script.as_string()
        return exec(code)


# ------------------------------------------------------------------------------
#  CALLBACKS
# ------------------------------------------------------------------------------


@persistent
def on_file_open(dummy: None) -> None:
    """Make sure pre/post actions are disabled for security."""

    settings = bpy.context.scene.renderplus

    if settings:
        # Don't use R+ for evil!
        settings.pre_enabled = False
        settings.post_enabled = False
        settings.off_options = "DISABLED"
        settings.batch.poweroff = "DISABLED"

    # Check for external blends on batch
    external = any([job.use_external for job in settings.batch.jobs])
    settings.batch.has_external = external

    # Check for running batch
    api.address, api.port = utils.get_server_address()

    if api.socket_busy():
        log.debug(f"Found a server on port {api.port}. Polling...")

        try:
            batch_name = api.poll_name()["name"]
            log.debug(f"Polled batch name: {batch_name}")

            if batch_name == bpy.data.filepath:
                ops.polling_loop(check_if_running)

        except urllib.error.HTTPError as e:
            if e.code == 409:
                log.debug("Poll: No batch has been run.")
            else:
                log.debug(f"Polling Failed with status {e.code}. {e.reason}")

            return

        except KeyError:
            log.debug("Poll: No batch has been run.")


def check_if_running() -> None:
    """Check if batch is running and set the state."""

    if state.reply and state.reply["status"] == "RUNNING":
        log.debug("Found a batch currently running.")
        state.mode = "RUNNING"


@persistent
def on_cancel(dummy: None) -> None:
    """Clean up if render is cancelled."""

    log.debug("Render Cancel Called")
    stats.reset()


@persistent
def on_post_render(scene: Scene) -> None:
    """Change data for animation renders."""

    log.debug(f"Post Render called at frame: {scene.frame_current}")

    try:
        stats.update_frame()
    except AttributeError:
        # on_post is sometimes called after on_complete, which will
        # make this throw an AttributeError. But it could be something else
        # too.
        log.debug("AttributeError in stats. Check for on_complete.")

    utils.force_redraw()


@persistent
def on_complete(scene: Scene) -> None:
    """Call the different functions after rendering."""

    log.debug("Render Complete called")

    settings = scene.renderplus
    prefs = utils.prefs()

    #  Clean up
    stats.stop()
    utils.force_redraw()

    #  Notifications
    if settings.notify_desktop:
        notifications.desktop(f"Render Finished for scene: {scene.name}")

    if settings.notify_sound:
        sound.play(prefs.sound_file, prefs.sound_volume / 100, False)

    if settings.notify_mail:
        old_notifications.mail()

    #  Actions
    if settings.autosave:
        autosave()

    if settings.post_enabled:
        run_hook("POST")

    if settings.off_options != "DISABLED":
        poweroff.off(settings.off_options)


@persistent
def on_init(scene: Scene) -> None:
    """Run when rendering begins."""

    log.debug("Render Init Called")

    settings = scene.renderplus
    old_notifications.error = None

    # Autohide objects
    if settings.autohide:
        for obj in scene.objects:
            visible = obj.visible_get()

            if not visible and not obj.hide_render:
                obj.hide_render = True
            elif visible and obj.hide_render:
                obj.hide_set(True)

    if settings.pre_enabled:
        run_hook("PRE")

    stats.reset()
    stats.start()
