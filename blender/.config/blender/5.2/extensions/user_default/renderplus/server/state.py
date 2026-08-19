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

"""Module to hold the state of the batch."""

from enum import Enum


class BatchStatus(Enum):
    """Status for a batch."""

    WAITING = 0
    RUNNING = 1
    FINISHED = 2
    CANCELLED = 3


# Function to cancel the current job
cancel = None

# Flag to stop processing new jobs
cancelling_batch = False

# List of status for each render job
jobs = []

# Times for the currently running batch
times = {
    "started": None,
    "finished": None,
    "rendertime": None,
}

# Statistics for the batch
stats = {
    "slowest_index": None,
    "slowest_time": None,
    "fastest_index": None,
    "fastest_time": None,
    "average_time": None,
}

# Status of the current batch
status = BatchStatus.WAITING

# Name of the currently running batch
batch_name = None

# Index of job currently rendering
current_job = None

# Batch data
recipe = None
