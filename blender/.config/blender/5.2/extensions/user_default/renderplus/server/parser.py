# ## BEGIN GPL LICENSE BLOCK ##
#
#   Copyright (C) Diego Gangl
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

from dataclasses import dataclass
from typing import Self
from re import Match
import re

if "." in __name__:
    from .status import Step
else:
    from status import Step


FRAME: str = r'Fra:\s*(?P<frame>\d+)\s*'
MEM: str = r'Mem:\s*(?P<mem>[\d\.]+[KMG]?(?:\s*\([^)]+\))?(?:,\s*Peak:\s*[\d\.]+[KMG]?)?)\s*\|?\s*'
TIME: str = r'Time:(?P<time>([0-9a-zA-Z_:.]+))\W\|\W'
REMAINING: str = r'Remaining:\s*(?P<remaining>[0-9:.]+)\s*\|\s*'
COMPOSITING: str = r'Compositing\s\|\sTile\s(?P<done>\d+)-(?P<todo>\d+)'
EEVEE_RENDER: str = r'Rendering\s(?P<done>\d+)\s/\s(?P<todo>\d+)\ssamples'
CYCLES_MEM: str = r'Mem:(\w+.\w+),\sPeak:(\w+.\w+)\s\|\s'
SCENE_LAYER: str = r'(.+)\s\|\s'
CYCLES_SAMPLES: str = r'Sample\s(?P<done>\d+)/(?P<todo>\d+)'

RE_CYCLES = re.compile(
    FRAME +
    r'.*?' +                # permitir texto intermedio (timestamps, prefijos, etc.)
    REMAINING +
    r'.*?' +
    MEM +
    r'.*?' +
    CYCLES_SAMPLES
)


#RE_EEVEE = re.compile(FRAME + MEM + TIME + EEVEE_RENDER)
RE_EEVEE = re.compile(FRAME + r'.*?' + EEVEE_RENDER)
RE_COMPO = re.compile(MEM + TIME + COMPOSITING)
RE_COMPO_INIT = re.compile(MEM + TIME + r"Compositing.*")

Frames = tuple[int, int] | None


@dataclass(slots=True)
class ParsedData:
    """Structured data from a line of stdout."""

    step: Step = Step.RENDERING
    frame: int = 0
    mem: str = ''
    progress: float = 0
    elapsed: str = ''
    remaining: str = ''
    todo: str = ''
    done: str = ''

    @staticmethod
    def safe_get(match: Match, key: str) -> str:
        """Get key avoiding exceptions."""

        try:
            return match[key]
        except (KeyError, IndexError):
            return ''


    @classmethod
    def from_match(cls, match: Match, step: Step, anim: Frames = None) -> Self:
        """Create instance from a regex match."""

        frame = int(cls.safe_get(match, 'frame'))
        todo = cls.safe_get(match, 'todo') or -1
        done = cls.safe_get(match, 'done') or 1
        mem = cls.safe_get(match, 'mem')
        elapsed = cls.safe_get(match, 'time')

        try:
            remaining = match['remaining']
        except IndexError:
            remaining = ''

        if anim is None:
            progress = (int(done) / int(todo)) * 100

            if step == Step.COMPO and progress < 0:
                progress = 100
        else:
            anim_step = 100 / (anim[1] - anim[0])
            progress = abs((frame - anim[0]) * anim_step)

        return cls(
            step=step,
            frame=int(frame),
            mem=mem,
            progress=progress,
            todo=todo,
            done=done,
            elapsed=elapsed,
            remaining=remaining,
        )


    def to_dict(self) -> dict:
        """Get this class fields as a dict"""

        return {
            "step": self.step.value,
            "frame": self.frame,
            "mem": self.mem,
            "progress" : self.progress,
            "elapsed" : self.elapsed,
            "remaining" : self.remaining,
            "todo": self.todo,
            "done": self.done,
        }


class Parser:
    """Parser for rendering stats output."""

    def __init__(self, engine: str) -> None:
        self.anim = None
        self.last_parsed = None

        match engine:
            case 'CYCLES':
                self.regex = RE_CYCLES
            case 'EEVEE' | 'BLENDER_EEVEE' | 'BLENDER_EEVEE_NEXT':
                self.regex = RE_EEVEE
            case _:
                raise ValueError('Invalid Engine for Parser')


    def set_animation(self, start: int, end: int) -> None:
        """Set as animation, and the start/end frames."""

        self.anim = (start, end)


    def update(self, data: str) -> ParsedData:
        """Parse a single line of data."""

        # use search so pattern can appear anywhere in the log line (handles timestamps/prefixes)
        if engine := self.regex.search(data):
            result = ParsedData.from_match(engine, Step.RENDERING, self.anim)

        elif compo := RE_COMPO.search(data):
            result = ParsedData.from_match(compo, Step.COMPO, self.anim)

        elif compo_init := RE_COMPO_INIT.search(data):
            result = ParsedData.from_match(compo_init, Step.COMPO_INIT, self.anim)

        else:
            # Couldn't match it against anything, return the defaults
            result = ParsedData(step=Step.RENDERING)

        if data == 'RENDERPLUS: job completed.':
            result.progress = 100

        elif self.last_parsed and self.last_parsed.step != result.step:
            # We are at the step change between
            # Rendering -> Compositing INIT -> Compositing.
            # Let's reset the progress.
            result.progress = 0

        self.last_parsed = result
        return result
