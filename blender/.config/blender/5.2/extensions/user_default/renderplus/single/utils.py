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


"""Useful functions and variables used throughout the addon."""


import os
import platform
import textwrap

import datetime
from typing import Tuple
from dataclasses import dataclass

import bpy
import addon_utils
from bpy.types import AddonPreferences, Operator, UILayout, PropertyGroup, Scene
from .. import __package__ as base_package


# OS name
sys = platform.system()


def prefs() -> AddonPreferences:
    """Return addon preferences."""

    return bpy.context.preferences.addons[base_package].preferences


@dataclass
class popup:
    """Popup to show a short message with an optional link button."""

    title: str
    message: str
    icon: str = "ERROR"
    width: int = 80
    link_url: str = None
    link_text: str = None


    def show(self) -> None:
        """Show messages in a popup.

            Modified from original code by Jon Denning
        """

        text = textwrap.wrap(self.message, 80)

        match self.icon:
            case "ERROR":
                icon = "ERROR"
            case "OK":
                icon = "CHECKMARK"
            case _:
                icon = "HELP"

        def draw(this, context):
            [this.layout.label(text=line) for line in text]

            if self.link_url:
                this.layout.separator()
                op = this.layout.operator('wm.url_open', 
                                          text=self.link_text,
                                          icon='WORLD_DATA')
                op.url = self.link_url

        bpy.context.window_manager.popup_menu(draw, title=self.title, icon=icon)


def buttons(layout: UILayout, op: str, text: str) -> Operator:
    """Confirmation/Cancel buttons for Batch modes."""

    row = layout.row()
    split = row.split(factor=0.85, align=True)
    col = split.column(align=True)
    col.scale_y = 1.2
    op = col.operator(op, text=text)

    col = split.column(align=True)
    col.scale_y = 1.2
    col.operator("renderplus.batch_toggle_mode", text="", icon="CANCEL")

    layout.separator()
    return op


def title(layout: UILayout, title: str, icon: str) -> None:
    """Title layout for Batch modes."""

    layout.separator()
    row = layout.row()
    box = row.box()
    box.label(text=title, icon=icon)
    layout.separator()


def notification_text(settings: PropertyGroup) -> str:
    """Generate text for notifications menu."""

    text = "Desktop" if settings.notify_desktop else ""

    if settings.notify_sound:
        text += "Sound" if not text else " + Sound"

    if settings.notify_mail:
        text += "Mail" if not text else " + Mail"

    return text or "Disabled"


def force_redraw() -> None:
    """
    Forces the UI to redraw

    This makes me cry at night but looks like
    it's the only way to do it.

    Modified from a snippet by CoDEManX in the
    bf-python list to work in a limited context.
    """

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "PROPERTIES":
                for region in area.regions:
                    try:
                        scene = bpy.context.scene
                        scene.frame_end = scene.frame_end
                        region.tag_redraw()
                    except AttributeError:
                        pass
                    return


def path(*args) -> str:
    """Return the path relative to the script. Don't include leading slash."""

    return os.path.join(os.path.dirname(__file__), "..", *args)


def sane_path(path: str) -> str:
    """Return a normalized path."""

    return os.path.normpath(os.path.abspath(bpy.path.abspath(path)))


def base_filename(filepath: str) -> str:
    """Return the file name for filepath without the extension."""

    return os.path.splitext(bpy.path.basename(filepath))[0]


def time_format(timestamp: float) -> str:
    """Formats a timestamp to be HH:MM:SS.UU."""

    return str(datetime.timedelta(seconds=timestamp))[:10]


def date_format(timestamp: float) -> str:
    """Formats a date from a timestamp."""

    try:
        date = datetime.datetime.fromtimestamp(timestamp)
        return date.strftime("%H:%M:%S - %d/%m/%Y")

    except OSError:
        # This works around a bug in Python 3.6 for
        # Windows where small timestamps cause an
        # invalid argument error **sigh**

        return str(datetime.timedelta(seconds=timestamp))[:-4]


def time_format(timestamp: float) -> str:
    """Formats time from a timestamp."""

    hours, remainder = divmod(timestamp, 3600)
    mins, secs = divmod(remainder, 60)

    return f"{int(hours):02}:{int(mins):02}:{int(secs):02}"


def default_terminal() -> str:
    """Return a default terminal for this OS."""

    term = {
        "Linux": "xterm -hold -e ",
        "Windows": 'start ""',
        "Darwin": ("osascript -e 'tell application" ' "Terminal" to do script "'),
    }

    return term[sys]


def image_files_ok() -> bool:
    """Check if image textures files are missing."""

    imgs = bpy.data.images
    real_path = lambda p: os.path.isfile(bpy.path.abspath(p))
    loaded = [img.has_data or real_path(img.filepath) for img in imgs]

    return all(loaded)


def get_server_address() -> Tuple[str, int]:
    """Get adress (IP/Host) and port for the server."""

    if prefs().batch_server_location == "NETWORK":
        address = prefs().batch_server
    else:
        address = "localhost"

    port = prefs().batch_port

    return address, port


def check_turbotools() -> bool:
    """Check if turbotools is installed for the scene."""

    return addon_utils.check("Turbo Tools")[1]
