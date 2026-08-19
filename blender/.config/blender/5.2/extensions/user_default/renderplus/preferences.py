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

"""Addon preferences."""


import os
from pydoc import text
import smtplib
import socket
import logging
import urllib.request

from bpy.types import Menu, AddonPreferences, UILayout, Operator
from bpy.props import (
    IntProperty,
    StringProperty,
    BoolProperty,
    EnumProperty,
    FloatProperty,
)

from .single import utils


log = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
#  Helper Functions
# ------------------------------------------------------------------------------


def default_path_debug() -> str:
    """Create a useful default for support log."""

    return os.path.expanduser(f"~{os.sep}renderplus_support.log")


def make_path_sane(key: str) -> None:
    """Prevent Blender's relative paths of doom."""

    if utils.prefs()[key] and utils.prefs()[key].startswith("//"):
        utils.prefs()[key] = utils.sane_path(utils.prefs()[key])
    elif key == "debug_file" and utils.prefs().debug_file == "":
        utils.prefs()["debug_file"] = default_path_debug()


def docs_url() -> str:
    """Get URL for local documentation."""

    local_path = os.path.dirname(os.path.realpath(__file__))
    return "file://" + os.path.join(local_path, "docs", "index.html")


# ------------------------------------------------------------------------------
#  Mail Operators
# ------------------------------------------------------------------------------


class RP_OT_MailTest(Operator):
    bl_idname = "renderplus.mail_test"
    bl_label = "Mail Test"
    bl_description = "Test email connection"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        prefs = utils.prefs()
        return prefs.mail_user != "" and prefs.mail_password != ""

    def execute(self, context):
        msg = None
        prefs = utils.prefs()

        try:
            if prefs.mail_ssl:
                server = smtplib.SMTP_SSL(prefs.mail_server)
            else:
                server = smtplib.SMTP(prefs.mail_server)

            server.login(prefs.mail_user, prefs.mail_password)

        except smtplib.SMTPAuthenticationError:
            msg = "Username and/or password were rejected"
        except smtplib.SMTPHeloError:
            msg = "Connection failed. Try enabling SSL"
        except smtplib.SMTPConnectError:
            msg = "There was a connection error"
        except socket.error:
            msg = "Can't find mail server"
        except smtplib.SMTPException:
            msg = "There was an unkown error"

        finally:
            if msg is not None:
                self.report({"ERROR"}, msg)
                log.error(msg)
                return {"CANCELLED"}

        self.report({"INFO"}, "Connected Successfully!")
        return {"FINISHED"}


class RP_OT_MailQuickSetup(Operator):
    bl_idname = "renderplus.mail_quick_setup"
    bl_label = "Mail quick setup"
    bl_description = "Setup email automatically"
    bl_options = {"REGISTER"}

    provider: EnumProperty(
        items=(
            ("GMAIL", "Gmail", ""),
            ("YAHOO", "Yahoo", ""),
            ("LIVE", "Outlook Live", ""),
        ),
        default="GMAIL",
    )

    def execute(self, context):
        prefs = utils.prefs()

        providers = {
            "GMAIL": {
                "ssl": True,
                "server": "smtp.gmail.com",
                "user": "-YOU-@gmail.com",
            },
            "YAHOO": {
                "ssl": True,
                "server": "smtp.mail.yahoo.com",
                "user": "-YOU-@yahoo.com",
            },
            "LIVE": {
                "ssl": True,
                "server": "smtp.office365.com",
                "user": "-YOU-@live.com",
            },
        }

        prefs.mail_ssl = providers[self.provider]["ssl"]
        prefs.mail_server = providers[self.provider]["server"]
        prefs.mail_user = providers[self.provider]["user"]
        prefs.mail_password = "-YOUR-PASSWORD"

        return {"FINISHED"}


class RP_OT_BatchServerTest(Operator):
    bl_idname = "renderplus.batch_server_test"
    bl_label = "Test server connection"
    bl_description = "Check if we can talk to the batch server"
    bl_options = {"REGISTER"}

    def execute(self, context):

        prefs = utils.prefs()
        address = prefs.batch_server
        port = prefs.batch_port

        url = f"http://{address}:{port}/test"
        req = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()

            pop = utils.popup("Server responded", "Everything ready to go!")
            pop.icon = "OK"
            pop.show()

            return {"FINISHED"}

        except urllib.error.URLError:
            self.report({"ERROR"}, "Server could not be reached")
            return {"CANCELLED"}

        except ConnectionResetError:
            self.report({"ERROR"}, "Connection reset. Network error?")
            return {"CANCELLED"}


# ------------------------------------------------------------------------------
#  Menu
# ------------------------------------------------------------------------------


class RP_MT_MailQuickSetup(Menu):
    bl_label = "Quick Setup"

    def draw(self, context):
        layout = self.layout

        layout.operator("renderplus.mail_quick_setup", text="Gmail").provider = "GMAIL"
        layout.operator("renderplus.mail_quick_setup", text="Yahoo").provider = "YAHOO"
        layout.operator(
            "renderplus.mail_quick_setup", text="MSN/Hotmail/Live/Outlook Live"
        ).provider = "LIVE"


# ------------------------------------------------------------------------------
#  UI
# ------------------------------------------------------------------------------


def notifications_tab(prefs: AddonPreferences, layout: UILayout) -> None:
    """Layout for notifications preferences."""

    utils.title(layout, "Sound Notifications Setup", "SOUND")
    split = layout.split(factor=0.335, align=True)

    col = split.column()
    col.label(text="Sound File")
    col.label(text="Volume")

    col = split.column()
    col.prop(prefs, "sound_file", icon="SOUND", text="")
    col.prop(prefs, "sound_volume", text="", slider=True)

    utils.title(layout, "Email Setup", "FILE_FONT")
    split = layout.split(factor=0.335, align=True)
    col = split.column()
    col.label(text="Send to")
    col.label(text="Username")
    col.label(text="Password")
    col.label(text="Server SMTP Address")
    col.label(text="")
    col.separator()

    col = split.column()
    col.prop(prefs, "mail_to", text="")
    col.prop(prefs, "mail_user", text="")
    col.prop(prefs, "mail_password", text="")
    col.prop(prefs, "mail_server", text="")
    col.prop(prefs, "mail_ssl")

    split = layout.split(factor=0.335, align=True)
    col.separator()
    col.operator("renderplus.mail_test")


    layout.row().label(
        text=(
            "Email credentials aren't stored or sent"
            " safely. Please don't use your personal email "
            "account"
        ),
        icon="INFO",
    )
    row = layout.row()
    msg = 'Cloud email services might not be compatible with "Render+"'
    row.label(text=msg, icon="ERROR")
    op = row.operator("wm.url_open", text='Why')
    op.url = "file://" + utils.path("docs/preferences.html") + "#gmail"


def batch_tab(prefs: AddonPreferences, layout: UILayout) -> None:
    """Layout for batch preferences."""

    utils.title(layout, "General Settings", "PRESET")

    split = layout.split(factor=0.335, align=True)
    split.enabled = prefs.show_batch

    col = split.column()
    col.label(text="Batch Server Location")

    if prefs.batch_server_location == "NETWORK":
        col.label(text="Batch Server Address")

    col.label(text="Batch Server Port")
    col.label(text="Refresh Frequency (seconds)")

    col = split.column()
    col.row().prop(prefs, "batch_server_location", expand=True)

    if prefs.batch_server_location == "NETWORK":
        col.prop(prefs, "batch_server", text="")

    col.prop(prefs, "batch_port", text="")
    col.prop(prefs, "batch_refresh_interval", text="")

    if prefs.batch_server_location == "NETWORK":
        split_small = layout.split(factor=0.5, align=True)
        col = split_small.column()
        col = split_small.column()
        col.scale_y = 1.2
        col.operator("renderplus.batch_server_test")

    col.separator(factor=3)
    col = layout.column(align=True)
    col.prop(prefs, "show_batch")
    col.prop(prefs, "batch_new_dirs")
    col.prop(prefs, "keep_alive")
    col.prop(prefs, "check_images")
    col.prop(prefs, "batch_always_turbo")

    utils.title(layout, "Custom Commands", "PREFERENCES")
    split = layout.split(factor=0.335, align=True)

    col = split.column()
    col.label(text="Blender", icon="BLENDER")
    col.label(text="Terminal", icon="CONSOLE")

    col = split.column()
    row = col.row()

    if prefs.batch_server_location == "NETWORK":
        row.alert = prefs.blender_path == ""

    row.prop(prefs, "blender_path", text="")
    col.prop(prefs, "term_path", text="")

    if prefs.batch_server_location == "NETWORK" and prefs.blender_path == "":
        layout.label(text="Please set a path for Blender in the server", icon="ERROR")
    else:
        layout.label(
            text=(
                "Fill this if you want to use a different"
                " Blender or Terminal binary for batches."
                " Leave emtpy to use defaults."
            ),
            icon="INFO",
        )

    layout.separator()

    utils.title(layout, "Default Output Path", "FILE_FOLDER")

    split = layout.split(factor=0.335, align=True)
    col = split.column()
    col.label(text="Base Filepath")
    col.label(text="Suffixes")

    col = split.column(align=True)
    col.prop(prefs, "batch_output_base", text="")

    row = col.row(align=True)
    row.prop(prefs, "batch_output_blend", toggle=True)
    row.prop(prefs, "batch_output_scene", toggle=True)
    row.prop(prefs, "batch_output_camera", toggle=True)

    split = layout.split(factor=0.335, align=True)
    col.separator()

    sample = prefs.batch_output_base
    sample += "_file" if prefs.batch_output_blend else ""
    sample += "_scene" if prefs.batch_output_scene else ""
    sample += "_camera" if prefs.batch_output_camera else ""

    col.label(text=sample)


def help_tab(prefs: AddonPreferences, layout: UILayout) -> None:
    """Layout for help tab."""

    layout.separator()
    row = layout.row()
    row.scale_y = 1.5

    row.label(text="")
    op = row.operator("wm.url_open", text="Documentation", icon="HELP")
    op.url = docs_url()
    row.label(text="")

    utils.title(layout, "Single Renders", "PREFERENCES")

    layout.prop(prefs, "use_debug_prints")
    layout.prop(prefs, "use_debug_file")

    if prefs.use_debug_file:
        privacy = (
            "The debug file will contain the following information "
            "about your system: Operating system, "
            "Blender version and branch."
        )

        layout.separator()
        layout.prop(prefs, "debug_file")
        layout.label(text=privacy, icon="INFO")

    utils.title(layout, "Local Batch Renders", "PREFERENCES")

    layout.prop(prefs, "use_log_server")

    if prefs.use_log_server:
        layout.prop(prefs, "server_log_path", text="Path to write log file")
        layout.separator()

    layout.prop(prefs, "use_clear_temp")
    layout.separator()

    row = layout.row()
    row.scale_y = 1.2
    row.label(text="")
    row.operator(
        "renderplus.batch_clear_tmp", text=" Clear temp folder now ", icon="TRASH"
    )
    row.label(text="")


# ------------------------------------------------------------------------------
#  Preferences
# ------------------------------------------------------------------------------


class RP_AP_Preferences(AddonPreferences):
    """Preferences for Render+."""

    bl_idname = __package__

    # --------------------------------------------------------------------------
    # Notifications tab

    sound_file: StringProperty(
        name="Sound File",
        description="Custom sound file for notifications",
        subtype="FILE_PATH",
        update=lambda a, b: make_path_sane("sound_file"),
        default=utils.path("assets", "notification.ogg"),
    )

    sound_volume: FloatProperty(
        name="Volume",
        description="Volume for sound notifications",
        default=90.0,
        min=0,
        max=100.0,
        subtype="PERCENTAGE",
    )

    mail_user: StringProperty(
        name="Username", description="User to login into the mail server", default=""
    )

    mail_password: StringProperty(
        name="Password",
        description="Password to login into the mail server",
        subtype="PASSWORD",
        default="",
    )

    mail_ssl: BoolProperty(
        name="Use SSL",
        description="Connect to mail server using Secure Sockets",
        default=False,
    )

    mail_server: StringProperty(
        name="Mail server (SMTP)",
        description="Server to send use when sending mails",
        default="",
    )

    mail_to: StringProperty(
        name="Send to",
        description="Address to send mail to",
    )

    # --------------------------------------------------------------------------
    # Batch tab

    show_batch: BoolProperty(
        name="Show Batch render panel",
        description="Show Batch rendering panel in render properties",
        default=True,
    )

    batch_server_location: EnumProperty(
        name="Batch Server Location",
        description="Tab in the preferences editor",
        items=(
            ("LOCAL", "This PC", ""),
            ("NETWORK", "Network", ""),
        ),
        default="LOCAL",
    )

    batch_refresh_interval: FloatProperty(
        name="Refresh interval for batch panel",
        description=(
            "Time between refreshes in the UI panel while a batch is"
            " running (in seconds)"
        ),
        default=0.05,
        min=0.01,
        max=60.0,
    )

    batch_new_dirs: BoolProperty(
        name="Automatically create directories when rendering",
        description=(
            "Try to create directories set in output paths"
            " if they don't exist when rendering."
        ),
        default=True,
    )

    batch_server: StringProperty(
        name="Server Adress",
        description=(
            "IP adress of the batch server " "(leave blank or as localhost if unsure)"
        ),
        default="localhost",
    )

    batch_port: IntProperty(
        name="Port for the batch server",
        description="Port to use for the batch server",
        min=1025,
        max=65500,
        default=7777,
    )

    batch_stuck_time: IntProperty(
        name="Server wait time",
        description=(
            "If the server is replying with the same data, wait "
            "this many minutes before killing it"
        ),
        min=5,
        max=600,
        default=600,
    )

    batch_output_base: StringProperty(
        name="Base Filepath",
        description="Default output filepath for new batch render jobs",
        default="//render",
    )

    batch_output_camera: BoolProperty(
        name="Camera",
        description="Add camera name after the default output filepath",
        default=False,
    )

    batch_output_scene: BoolProperty(
        name="Scene",
        description="Add camera name after the default output filepath",
        default=True,
    )

    batch_output_blend: BoolProperty(
        name="Filename",
        description="Add blend filename after the default output filepath",
        default=True,
    )

    batch_always_turbo: BoolProperty(
        name="Always use Turbo Tools (if present)",
        description=("Enable Turbo Tools by default on all " "new render jobs"),
        default=False,
    )

    blender_path: StringProperty(
        name="Custom Blender Command",
        description=(
            "Blender to use for batches. Type a"
            "command or point this to the Blender executable."
        ),
        update=lambda a, b: make_path_sane("blender_path"),
        subtype="FILE_PATH",
    )

    term_path: StringProperty(
        name="Custom Terminal Command",
        description=(
            "Terminal to use for batches. Type a"
            "command or point this to a terminal executable."
        ),
        update=lambda a, b: make_path_sane("term_path"),
        subtype="FILE_PATH",
    )

    keep_alive: BoolProperty(
        name="Never shutdown batch server",
        description="Don't shutdown server after completing the batch",
        default=False,
    )

    check_images: BoolProperty(
        name="Check missing texture files",
        description="Check for missing textures files before starting a batch",
        default=False,
    )

    # --------------------------------------------------------------------------
    # Help tab

    use_debug_prints: BoolProperty(
        name="Enable debug messages",
        description="Enable debug messages in the console",
        default=False,
    )

    use_debug_file: BoolProperty(
        name="Write support log",
        description=(
            "Enable debugging output. This is used to get information"
            "when reporting a bug, or requesting support."
        ),
        default=False,
    )

    debug_file: StringProperty(
        name="Support log file",
        description="Where to save the support log output",
        update=lambda a, b: make_path_sane("debug_file"),
        subtype="FILE_PATH",
        default=default_path_debug(),
    )

    use_log_server: BoolProperty(
        name="Write log for the batch server",
        description="Enable log writing for the batch server",
        default=False,
    )

    server_log_path: StringProperty(
        name="Batch server log file",
        description=(
            "Where to write the batch server log file. " "\nLeave empty for temp folder"
        ),
        subtype="FILE_PATH",
    )

    use_clear_temp: BoolProperty(
        name="Clear temp folder after running a batch",
        description="Always clear the temp folder after finishing a batch",
        default=True,
    )

    ui_tab: EnumProperty(
        name="Tab",
        description="Tab in the preferences editor",
        items=(
            ("NOTIFICATIONS", "Notifications", ""),
            ("BATCH", "Batch", ""),
            ("HELP", "Help", ""),
        ),
        default="NOTIFICATIONS",
    )

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, "ui_tab", expand=True)

        if self.ui_tab == "NOTIFICATIONS":
            notifications_tab(self, layout)
        elif self.ui_tab == "BATCH":
            batch_tab(self, layout)
        elif self.ui_tab == "HELP":
            help_tab(self, layout)

        layout.separator()
