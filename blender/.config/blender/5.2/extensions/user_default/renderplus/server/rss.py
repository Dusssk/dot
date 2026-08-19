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

"""RSS feed writer for Render+ Batch Server."""

import datetime
import logging
from typing import Dict, List
from email.utils import formatdate

import utils


update = None
log = logging.getLogger("batch.rss")


def build(data: Dict) -> str:

    template = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<?xml-stylesheet type="text/xsl" href="feed.xslt"?>',
        '<rss version="2.0">',
        "<channel>",
        "<title>{title}</title>",
        "<link>#</link>",
        "<description>{description}{finished}</description>",
        "<lastBuildDate>{last_update}</lastBuildDate>",
        "<generator>Render+ 2.0</generator>",
        "{jobs}",
        "</channel>",
        "</rss>",
    ]

    data["last_update"] = formatdate(localtime=True)
    return "\n".join(template).format(**data)


def build_job(job: Dict, index: int) -> str:
    """Format render jobs into rss items."""

    template = [
        "<item>",
        "<title>{title}</title>",
        "<description>{description}</description>",
        "<guid>{guid}</guid>",
        "</item>",
    ]

    messages = {
        "QUEUED": "Waiting...",
        "RUNNING": "Rendering...",
        "FINISHED": f"Finished on {now()}",
        "DISABLED": "Disabled",
        "FAILED": f"Failed on {now()}",
    }

    description = f'{messages[job["status"]]} - {job["progress"]:.2f}%'

    data = {
        "title": f'[{job["status"]}] {job["name"]}',
        "description": description,
        "guid": index,
    }

    return "\n".join(template).format(**data)


def build_all_jobs(jobs: List) -> str:
    """Build RSS items for all render jobs."""

    job_strings = [build_job(job, index) for index, job in enumerate(jobs)]
    return "\n".join(job_strings)


def format_status_extra(rendertime: int) -> str:
    """Format status info."""

    return f"\nRendertime: {utils.format_time(rendertime)}"


def now() -> str:
    """Return the current time formatted according to locale."""

    return datetime.datetime.now().strftime("%x - %X")


def generate(jobs: List, name: str) -> str:
    """Generate RSS file."""

    data = {
        "title": f"Batch Render: {name}",
        "description": f"Batch started on: {now()}.",
        "finished": "",
    }

    jobs_state = [
        {
            "name": job["name"],
            "status": job["status"],
            "info": format_status_extra(job["times"]["rendertime"]),
            "progress": job["progress"],
        }
        for job in jobs
    ]

    if not any([j["status"] in ("RUNNING", "QUEUED") for j in jobs_state]):
        data["finished"] = f"\nFinished on: {now()}."

    data["jobs"] = build_all_jobs(jobs_state)
    return build(data)
