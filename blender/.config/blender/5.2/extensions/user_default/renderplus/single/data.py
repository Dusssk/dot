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


"""Data structures for main functionality."""

import logging

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    PointerProperty,
)

from ..batch import data


log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# STATS
# -----------------------------------------------------------------------------
class RP_PG_StatsData(PropertyGroup):
    """Stats data."""

    average: FloatProperty(
        name="Average frame rendertime",
        description="Averaged rendertime for all frames",
        default=0,
    )

    slowest: FloatVectorProperty(
        name="Slowest frame rendertime",
        description="Highest rendertime for all frames",
        size=2,
        default=(0, 0),
    )

    fastest: FloatVectorProperty(
        name="Fastest frame rendertime",
        description="Smallest rendertime of all frames",
        size=2,
        default=(0, 0),
    )

    remaining: FloatProperty(
        name="Time remaining to complete animation",
        description="Estimation of how long rendering will take",
        default=0,
    )

    total: FloatProperty(
        name="Total rendertime",
        description="Time it took to render the last animation",
        default=-1,
    )

    ui_toggle: BoolProperty(
        name="Show time stats",
        description="Show more stats about render time",
        default=False,
    )

    save_file: BoolProperty(
        name="Save stats to a file",
        description="Save the stats to a CSV file",
        default=False,
    )


# -----------------------------------------------------------------------------
# ACTION
# -----------------------------------------------------------------------------


class RP_PG_ActionSettings(bpy.types.PropertyGroup):
    """Settings for pre/post actions."""

    option: EnumProperty(
        name="Option",
        description="Options to run this action",
        items=(
            ("command", "Command", "Run a command"),
            ("script", "Script", "Run a Python script"),
        ),
        default="command",
    )

    command: StringProperty(
        name="Command", description="Command to execute", default=""
    )

    script: PointerProperty(
        name="Script", description="Script to run", type=bpy.types.Text
    )


# -----------------------------------------------------------------------------
# SETTINGS
# -----------------------------------------------------------------------------


class RP_PG_Settings(PropertyGroup):
    """Settings and UI States for R+."""

    off_options: EnumProperty(
        name="Power Off",
        description="Power off when rendering is finished",
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
        name="Email", description="Send an email to notify me", default=False
    )

    opengl_transparent: BoolProperty(
        name="Transparent", description="Make background transparent", default=False
    )

    opengl_use_viewport: BoolProperty(
        name="Render Viewport",
        description="Render the entire viewport (including invisible objects)",
        default=False,
    )

    opengl_percentage: FloatProperty(
        name="Size Percentage",
        description="Custom size percentage OpenGL renders",
        subtype="PERCENTAGE",
        precision=0,
        min=1,
        max=100,
        default=100,
    )

    autosave: BoolProperty(
        name="Autosave image renders",
        description=(
            "Save image renders automatically to the folder in the" "output panel"
        ),
        default=False,
    )

    autohide: BoolProperty(
        name="Autohide objects",
        description=(
            "Hide objects for rendering when they are hidden in the "
            "viewport and vice versa."
        ),
        default=False,
    )

    stats: PointerProperty(type=RP_PG_StatsData)
    batch: PointerProperty(type=data.RP_PG_BatchSettings)
    batch_ops: PointerProperty(type=data.RP_PG_BatchOps)

    # Post-render settings
    # -------------------------------------------------------------------------
    post_enabled: BoolProperty(
        name="Post Render Toggle",
        description="Enable/Disable post render actions",
        default=False,
    )

    post_settings: PointerProperty(type=RP_PG_ActionSettings)

    # Pre-render settings
    # -------------------------------------------------------------------------
    pre_enabled: BoolProperty(
        name="Pre Render Toggle",
        description="Enable/Disable Pre render actions",
        default=False,
    )

    pre_settings: PointerProperty(type=RP_PG_ActionSettings)
