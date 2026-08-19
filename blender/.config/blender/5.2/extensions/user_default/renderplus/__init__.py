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

# ------------------------------------------------------------------------------
# DEFAULT NOTIFICATION SOUND:
# "Notification Chime" (freesound.org/people/hykenfreak/sounds/202029)
# - By Hykenfreak (freesound.org/people/hykenfreak)
# - CC-BY (creativecommons.org/licenses/by/3.0)
# ------------------------------------------------------------------------------

import bpy
import logging
import importlib
import subprocess

from bpy.props import CollectionProperty, PointerProperty

import os
import shutil


# ------------------------------------------------------------------------------
#  Render+ Classes
# ------------------------------------------------------------------------------

try:
    importlib.reload(batch_data)
    importlib.reload(data)
    importlib.reload(ui)
    importlib.reload(notifications)
    importlib.reload(callbacks)
    importlib.reload(preferences)
    importlib.reload(batch_ui)
    importlib.reload(batch_external)
    importlib.reload(batch_ops)
    importlib.reload(batch_list_ops)
    importlib.reload(batch_quick)
    importlib.reload(color_log)
    importlib.reload(panel_override)
    importlib.reload(panel_buttons)
    importlib.reload(panel_basic)
    importlib.reload(panel_render)

    print("Render+ Modules Reloaded")

except NameError:
    from .single import data
    from .single import ui
    from .single import notifications
    from .single import utils
    from .single import callbacks
    from . import preferences
    from .batch import ui as batch_ui
    from .batch import external as batch_external
    from .batch import data as batch_data
    from .batch import ops as batch_ops
    from .batch import list_ops as batch_list_ops
    from .batch import quick as batch_quick
    from .batch import panel_override
    from .batch import panel_buttons
    from .batch import panel_basic
    from .batch import panel_render
    from .vendor import color_log


classes = (
    preferences.RP_MT_MailQuickSetup,
    preferences.RP_AP_Preferences,
    preferences.RP_OT_MailTest,
    preferences.RP_OT_MailQuickSetup,
    preferences.RP_OT_BatchServerTest,
    batch_external.RP_PG_ExternalBlendProperty,
    batch_external.RP_PG_ExternalBlendData,
    batch_external.RP_OT_SetExternalBlendFile,
    batch_external.RP_OT_AddExternalRenderJobs,
    batch_external.RP_OT_ReloadExternalBlendData,
    batch_data.RP_PG_BatchOps_OutputChange,
    batch_data.RP_PG_BatchOps_QuickScenes,
    batch_data.RP_PG_BatchOps_QuickWorlds,
    batch_data.RP_PG_BatchOps_QuickCameras,
    batch_data.RP_PG_BatchOps_QuickBatch,
    batch_data.RP_PG_BatchOps,
    batch_data.RP_PG_CustomOverride,
    batch_data.RP_PG_Hook,
    batch_data.RP_PG_RenderPass,
    batch_data.RP_PG_RenderJob,
    batch_data.RP_PG_BatchSettings,
    batch_ui.RP_UL_Batch,
    batch_ui.RP_UL_BatchLogs,
    batch_ui.RP_UL_BatchOverrides,
    batch_ui.RP_MT_BatchNotifications,
    batch_ui.RP_MT_BatchOps,
    batch_ui.RP_MT_CustomOverridePresets,
    batch_ui.RP_PT_Batch,
    panel_basic.RP_PT_BasicSettings,
    panel_basic.RP_PT_CustomFrame,
    panel_render.RP_PT_Output,
    panel_render.RP_PT_RenderEngine,
    panel_render.RP_UL_RenderPasses,
    panel_render.RP_PT_RenderPasses,
    panel_override.RP_PT_CustomOverrides,
    panel_basic.RP_PT_Actions,
    panel_buttons.RP_PT_BatchButtons,
    ui.RP_OT_ShowHelp,
    ui.RP_MT_Notifications,
    ui.RP_PT_Main,
    ui.RP_PT_MainStats,
    ui.RP_PT_PreRender,
    ui.RP_PT_PostRender,
    batch_ops.RP_OT_OpenRenderFolder,
    batch_ops.RP_OT_CustomFramePopup,
    batch_ops.RP_OT_ClearBatchTemp,
    batch_ops.RP_OT_GetBorderRenderFromViewport,
    batch_ops.RP_OT_ChangeOutputs,
    batch_ops.RP_OT_ToggleBatchMode,
    batch_ops.RP_OT_AddCustomOverride,
    batch_ops.RP_OT_RemoveCustomOverride,
    batch_ops.RP_OT_CloneOverride,
    batch_ops.RP_OT_AddCustomOverridePreset,
    batch_ops.RP_OT_GenerateScript,
    batch_list_ops.RP_OT_NewRenderJob,
    batch_list_ops.RP_OT_ToggleJobs,
    batch_list_ops.RP_OT_DeleteRenderJob,
    batch_list_ops.RP_ToggleJobType,
    batch_list_ops.RP_OT_MoveRenderJob,
    batch_list_ops.RP_OT_CopyJobSettings,
    batch_ops.RP_OT_CancelJob,
    batch_ops.RP_OT_CancelBatch,
    batch_ops.RP_OT_CancelUpload,
    batch_ops.RP_OT_StartBatch,
    batch_ops.RP_OT_ApplyRenderJob,
    batch_quick.RP_OT_Quick_SceneProps,
    batch_quick.RP_OT_QuickOutputHelp,
    batch_quick.RP_OT_Quick_AddConfig,
    batch_quick.RP_OT_Quick_RemoveConfig,
    data.RP_PG_StatsData,
    data.RP_PG_ActionSettings,
    data.RP_PG_Settings,
)


# ------------------------------------------------------------------------------
#  LIBRARIES
# ------------------------------------------------------------------------------
def install_lib(name: str) -> None:
    """Install required libraries."""

    pybin = bpy.app.binary_path_python
    subprocess.check_call([pybin, "-m", "pip", "install", name])


try:
    import requests
except ImportError:
    print("Requests not found. Trying to install.")
    install_lib("requests")


# ------------------------------------------------------------------------------
#  LOGGING
# ------------------------------------------------------------------------------
def setup_logging(debug: bool) -> logging.Logger:
    """Setup and return logger."""

    log = logging.getLogger(__name__)
    prefs = utils.prefs()

    CONSOLE_FORMAT = "[Render+] [%(levelname)s] -> %(message)s"
    console_formatter = logging.Formatter(CONSOLE_FORMAT)

    console_handler = color_log.ColorStreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)

    log.addHandler(console_handler)
    log.propagate = False

    if debug:
        FILE_FORMAT = (
            "- %(asctime)s :: %(name)-26s :: %(levelname)-8s" " :: %(message)s"
        )
        file_formatter = logging.Formatter(FILE_FORMAT)

        try:
            file_handler = logging.FileHandler(prefs.debug_file)
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)

            log.addHandler(file_handler)

        except (FileNotFoundError, PermissionError):
            print("[RENDER+ LOGGING ERROR]")
            print("- Can't write log to {0}".format(prefs.debug_file))
            print("- Support log has been disabled")

    if bpy.app.background:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.DEBUG if debug or prefs.use_debug_prints else logging.INFO)

    return log


# ------------------------------------------------------------------------------
#  REGISTER / UNREGISTER
# ------------------------------------------------------------------------------


def register():

    # --------------------------------------------------------------------------
    # CLASS AND DATA REGISTER

    for c in classes:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            pass

    wm = bpy.types.WindowManager
    scene = bpy.types.Scene
    external_blenddata = batch_external.RP_PG_ExternalBlendData

    scene.renderplus = PointerProperty(type=data.RP_PG_Settings)
    wm.renderplus = CollectionProperty(type=external_blenddata)

    prefs = utils.prefs()

    # --------------------------------------------------------------------------
    # CALLBACKS REGISTER

    if not bpy.app.background:
        handlers = bpy.app.handlers
        handlers.load_post.append(callbacks.on_file_open)
        handlers.render_init.append(callbacks.on_init)
        handlers.render_complete.append(callbacks.on_complete)
        handlers.render_cancel.append(callbacks.on_cancel)
        handlers.render_post.append(callbacks.on_post_render)

    # --------------------------------------------------------------------------
    # LOGGING SETUP

    try:
        log = setup_logging(prefs.use_debug_file)

        log.debug(" ")
        log.debug("-" * 80)

        background = "[BACKGROUND]" if bpy.app.background else ""
        log.debug(f"LOG START {background}")

        log.debug("-" * 80)
        log.debug(f"System: {utils.sys}")
        log.debug(f"Blender: {bpy.app.version_string}")
        log.debug(f"Branch: {bpy.app.build_branch}")
        log.debug(f"Build Options: {bpy.app.build_options}")
        log.debug(f"Registered Handlers: {bpy.app.handlers}")

    except ValueError as e:
        print(repr(e))
        print("\n")
        print("-[RENDERPLUS]" + ("-" * 66))
        print(
            (
                '\nCan\'t write support log in path "{0}"'
                "! Please check preferences.\n".format(prefs.debug_file)
            )
        )
        print("-" * 80)
        print("\n")

    # --------------------------------------------------------------------------
    # CUSTOM OVERRIDES PRESETS

    if bpy.app.version[0] == 2:
        resources = bpy.utils.user_resource("SCRIPTS", "presets")
        presets = os.path.join(resources, "renderplus", "overrides")

    else:
        resources = bpy.utils.user_resource("SCRIPTS")
        presets = os.path.join(resources, "presets", "renderplus", "overrides")

    bundled = utils.path("assets", "presets")

    if not os.path.isdir(presets):
        os.makedirs(presets)

        # Get a list of all the files in your bundled presets folder
        files = os.listdir(bundled)

        # Copy them
        [shutil.copy2(os.path.join(bundled, f), presets) for f in files]


def unregister():

    del bpy.types.Scene.renderplus

    if not bpy.app.background:
        handlers = bpy.app.handlers
        handlers.load_post.remove(callbacks.on_file_open)
        handlers.render_init.remove(callbacks.on_init)
        handlers.render_complete.remove(callbacks.on_complete)
        handlers.render_cancel.remove(callbacks.on_cancel)
        handlers.render_post.remove(callbacks.on_post_render)

    for c in classes:
        try:
            bpy.utils.unregister_class(c)
        except ValueError:
            pass


if __name__ == "__main__":
    register()
