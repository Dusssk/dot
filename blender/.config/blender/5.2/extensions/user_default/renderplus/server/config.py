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

import tomllib
from dataclasses import dataclass, field
import itertools
import requests
from typing import Iterator


@dataclass
class WorkerConfig:
    """Configuration for a specific worker"""

    name: str = "Worker"
    port: int = 7777
    address: str = "localhost"
    poll_interval: int = 1 * 60


    @classmethod
    def from_dict(cls, section: dict):
        """Load from .ini file section."""

        instance = cls()

        instance.port = section["port"]
        instance.address = section["address"]
        instance.poll_interval = section["poll_interval"]

        return instance


    def check(self) -> dict[str, str]:
        """Ping a worker to see if it's ready."""

        r = requests.get(f'http://{self.address}:{self.port}/batch/ready')

        match r.status_code:
            case 401:
                return {'status': 'RUNNING_BATCH'}
            case 200:
                return r.json()
            case _:
                return {'status': f'Unknown error: {r.status_code}'}


@dataclass
class Config:
    """Represents server configuration."""

    port: int = 7777
    mode: str = "master"
    cleanup: bool = True
    log_path: str = "./renderplus.log"
    blender_bin: str = ""
    list_gpus: bool = False
    workers: list[WorkerConfig] = field(default_factory=lambda: [])
    disable_workers: bool = False


    @classmethod
    def from_ags(cls, args):
        """Load from command line arguments."""

        if config := args.config:
            return cls.from_file(config)

        instance = cls()
        instance.port = args.port
        instance.list_gpus = args.list_gpus
        instance.log_path = args.write_log
        instance.cleanup = not args.no_cleanup

        return instance


    @classmethod
    def from_file(cls, path: str):
        """Load from .ini file."""

        with open(path, "rb") as f:
            config = tomllib.load(f)

        instance = cls()

        instance.port = config["main"]["port"]
        instance.log_path = config["main"]["log_path"]
        instance.cleanup = config["main"]["cleanup"]
        instance.disable_workers = config["main"]["disable_workers"]
        instance.blender_bin = config["main"]["blender"]

        for name, section in config.get('workers', {}).items():
            worker = WorkerConfig.from_dict(section)
            worker.name = name
            instance.workers.append(worker)

        return instance


    def iter_workers(self) -> Iterator[WorkerConfig]:
        """Return worker configs while wrapping around."""

        return itertools.cycle(self.workers)
