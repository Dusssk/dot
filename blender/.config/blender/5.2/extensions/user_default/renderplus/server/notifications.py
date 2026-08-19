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

"""Functions to notify when renders are complete."""


import os
import logging
import smtplib
import subprocess
import platform
from email.mime.text import MIMEText

from typing import Dict


log = logging.getLogger("batch.notify")


def desktop(message: str) -> None:
    """Send a desktop notification."""

    title = "Blender (Render+)"
    cmd = {
        "Linux": f'notify-send -i "blender" "{title}" "{message}"',
        "Darwin": (
            f'osascript -e \'display notification "{message}"' f'with title "{title}"\''
        ),
    }

    subprocess.run(cmd[platform.system()], shell=True)


def sound(blender: str, sound_data: Dict) -> None:
    """Play a sound (using Blender's aud system)."""

    cmd = [
        blender,
        "-b",
        "-P",
        os.path.join(os.path.dirname(__file__), "sound.py"),
        "--",
        sound_data["file"],
        str(sound_data["volume"]),
    ]

    subprocess.run(cmd)


def mail(mail_data: Dict, message: str) -> None:
    """Send a notification via email."""

    mail = MIMEText(message)
    mail["Subject"] = "Batch Rendering Finished"
    mail["From"] = mail_data["user"]
    mail["To"] = mail_data["to"]

    try:
        if mail_data["ssl"]:
            server = smtplib.SMTP_SSL(mail_data["server"])
        else:
            server = smtplib.SMTP(mail_data["server"])
    except Exception as e:
        log.error(msg)

    try:
        server.login(mail_data["user"], mail_data["pass"])
    except smtplib.SMTPAuthenticationError:
        msg = (
            "Username and/or password for email server are wrong. "
            "Please check your settings."
        )
        log.error(msg)
        return

    except smtplib.SMTPException:
        msg = (
            "There was an error while trying to send the nofitication "
            "email. Please check the mail notification settings."
        )
        log.error(msg)
        return

    try:
        msg = ""
        server.send_message(mail)
        server.quit()
    except smtplib.SMTPServerDisconnected:
        msg = "Connection to email server was lost. Please try again."
    except smtplib.SMTPRecipientsRefused:
        msg = (
            "The mail recipient was refused. Please check your settings and"
            " try again."
        )
    except (smtplib.SMTPDataError, smtplib.SMTPHeloError):
        msg = "There was an error while trying to send the nofitication email."
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPSenderRefused):
        msg = (
            "Username and/or password for email server are wrong. "
            "Please check your settings."
        )
    finally:
        log.error(msg)
