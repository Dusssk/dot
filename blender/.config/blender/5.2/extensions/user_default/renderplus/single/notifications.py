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

"""Functions and operators to notify when renders are complete."""

import os
import logging

import smtplib
from email.mime.text import MIMEText

import bpy
import aud

from . import utils


# -----------------------------------------------------------------------------
# HANDLERS
# -----------------------------------------------------------------------------

# Sound notifications
sound_handle = None


# Logging
log = logging.getLogger(__name__)

# Errors
error = None


# -----------------------------------------------------------------------------
#  FUNCTIONS
# -----------------------------------------------------------------------------


def sound() -> None:
    """Play a sound to notify."""

    global sound_handle
    prefs = utils.prefs()

    if prefs.sound_file == "":
        sound_file = utils.path("assets", "notification.ogg")
    else:
        sound_file = utils.sane_path(prefs.sound_file)

    device = aud.Device()
    sound = aud.Sound(sound_file)

    try:
        sound_handle = device.play(sound)
        sound_handle.volume = prefs.sound_volume / 100

    except aud.error as e:
        msg = "Couldn't play sound file: " + prefs.sound_file
        msg += "\n Error: " + str(e)
        log.error(msg)


def log_error(msg):
    """Log and show an error"""

    global error

    if msg:
        error = msg
        log.error(msg)


def mail(message=None, subject=None):
    """Send a notification via email"""

    prefs = utils.prefs()

    # Fail early if there's no email setup
    if "mail_to" not in prefs:
        log.error(("Email hasn't been configured " "yet! Check your preferences"))
        return

    # GENERATE MESSAGE
    server = None
    file = os.path.basename(bpy.data.filepath) or "Untitled"
    stats = bpy.context.scene.renderplus.stats

    if not message:
        message = file + " has finished rendering \n\n"

    message += "Total render time: {0} seconds \n".format(
        utils.time_format(stats.total)
    )

    if stats.average > 0:
        message += (
            "Average frame time: "
            + str(utils.time_format(stats.average))
            + " seconds\n"
        )
        message += "Slowest frame: #{0} ({1} seconds)\n".format(
            int(stats.slowest[0]), utils.time_format(stats.slowest[1])
        )

        message += "Fastest frame: #{0} ({1} seconds)\n".format(
            int(stats.fastest[0]), utils.time_format(stats.slowest[1])
        )

    # SETUP MAIL
    mail = MIMEText(message)

    if subject:
        mail["Subject"] = subject
    else:
        mail["Subject"] = file + " has finished rendering"

    mail["From"] = prefs.mail_user
    mail["To"] = prefs.mail_to

    # CONNECT AND SEND MAIL
    if prefs.mail_ssl:
        server = smtplib.SMTP_SSL(prefs.mail_server)
    else:
        server = smtplib.SMTP(prefs.mail_server)

    try:
        server.login(prefs.mail_user, prefs.mail_password)
    except smtplib.SMTPAuthenticationError:
        msg = (
            "Username and/or password for email server are wrong. "
            "Please check your settings."
        )
        log.error(msg)
    except smtplib.SMTPException:
        msg = "There was an error while trying to send the nofitication email."
        log.error(msg)

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
        log_error(msg)
