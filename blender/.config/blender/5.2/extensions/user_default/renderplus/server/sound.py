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

"""Blender-based module to play a sound."""

import sys
import time

try:
    import aud
except ImportError:
    print('Could not import aud module from Blender')
    aud = None


def play(sound_file: str, volume: float, wait: bool) -> None:
    """Play a sound to notify."""

    if not aud:
        return

    device = aud.Device()
    sound = aud.Sound(sound_file)

    try:
        sound_handle = device.play(sound)
        sound_handle.volume = volume

        if wait:
            while sound_handle.status == aud.STATUS_PLAYING:
                time.sleep(1 / 40)

    except aud.error as e:
        print(f"Couldn't play sound file: {sound_file}")
        print(f"Error {e}")


if __name__ == "__main__":

    # Get all args after "--"
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :]

    sound_file = argv[0]
    volume = float(argv[1]) / 100

    play(sound_file, volume, True)
