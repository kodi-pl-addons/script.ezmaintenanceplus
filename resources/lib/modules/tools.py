"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs, os, sys
import urllib
import re
import time
import zipfile
from math import trunc
from resources.lib.modules import control
from datetime import datetime
from resources.lib.modules.backtothefuture import unicode, PY2

if PY2:
    FancyURLopener = urllib.FancyURLopener
else:
    FancyURLopener = urllib.request.FancyURLopener

dp = xbmcgui.DialogProgress()
dialog = xbmcgui.Dialog()
addonInfo = xbmcaddon.Addon().getAddonInfo

AddonTitle = "EZ Maintenance+"
AddonID = 'script.ezmaintenanceplus'

# Code to map the old translatePath
try:
    translatePath = xbmcvfs.translatePath
except AttributeError:
    translatePath = xbmc.translatePath


def open_Settings():
    open_Settings = xbmcaddon.Addon(id=AddonID).openSettings()


def _get_keyboard( default="", heading="", hidden=False, cancel="" ):
    """ shows a keyboard and returns a value """
    if cancel == "":
        cancel = default
    keyboard = xbmc.Keyboard( default, heading, hidden )
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        return unicode(keyboard.getText())
    return cancel

##############################    END    #########################################
