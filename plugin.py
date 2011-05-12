#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 by Coolman & Swiss-MAD
#
# In case of reuse of this source code please do not remove this copyright.
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	For more information on the GNU General Public License see:
#	<http://www.gnu.org/licenses/>.
#

from Components.Converter import EMCClockToText
from Components.Converter import EMCEventName
from Components.Converter import EMCServicePosition
from Components.Converter import EMCServiceTime

from __init__ import *
from Plugins.Plugin import PluginDescriptor
from Components.config import *
from EMCTasker import emcTasker, emcDebugOut
from EnhancedMovieCenter import _, EMCVersion, EMCStartup, EnhancedMovieCenterMenu


def langList():
	newlist = []
	for e in language.getLanguageList():
		newlist.append( (e[0], _(e[1][0])) )
	return newlist

def langListSel():
	newlist = []
	for e in language.getLanguageList():
		newlist.append( _(e[1][0]) )
	return newlist

config.EMC = ConfigSubsection()
config.EMC.needsreload = ConfigYesNo(default = False)
config.EMC.about = ConfigSelection(default = "1", choices = [("1", " ")])
config.EMC.extmenu_plugin = ConfigYesNo()
config.EMC.extmenu_list = ConfigYesNo()
config.EMC.epglang = ConfigSelection(default = language.getActiveLanguage(), choices = langList() )
config.EMC.sublang1 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.EMC.sublang2 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.EMC.sublang3 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.EMC.audlang1 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.EMC.audlang2 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.EMC.audlang3 = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices = langListSel() )
config.EMC.autosubs = ConfigYesNo(default = False)
config.EMC.autoaudio = ConfigYesNo(default = False)
config.EMC.key_period = ConfigSelectionNumber(50, 900, 50, default = 100)
config.EMC.key_repeat = ConfigSelectionNumber(250, 900, 50, default = 500)
config.EMC.enigmarestart = ConfigYesNo(default = False)
config.EMC.enigmarestart_begin = ConfigClock(default = 60*60*2)
config.EMC.enigmarestart_end = ConfigClock(default = 60*60*5)
config.EMC.enigmarestart_stby = ConfigYesNo(default = False)
config.EMC.debug = ConfigYesNo(default = False)
config.EMC.folder = ConfigText(default = "/hdd/EMC", fixed_size = False, visible_width = 22)
config.EMC.debugfile = ConfigText(default = "output.txt", fixed_size = False, visible_width = 22)
config.EMC.ml_disable = ConfigYesNo()
config.EMC.movie_bluefunc = ConfigSelection(default = "Movie home", choices = [("Movie home", _("Movie home")), ("Play last", _("Play last"))])
config.EMC.CoolStartHome = ConfigYesNo(default = False)
config.EMC.movie_descdelay = ConfigSelectionNumber(50, 1000, 50, default = 200)
config.EMC.skin_able = ConfigYesNo(default = False)
config.EMC.movie_icons = ConfigYesNo(default = True)
config.EMC.movie_progress = ConfigSelection(default = "PB", choices = [("PB", _("ProgressBar")), ("P", _("Percent (%)")), ("Off", _("Off"))])
config.EMC.movie_watching_percent = ConfigSelectionNumber(0, 30, 1, default = 5)
config.EMC.movie_finished_percent = ConfigSelectionNumber(50, 100, 1, default = 80)
config.EMC.movie_date = ConfigYesNo(default = True)
config.EMC.movie_mark = ConfigYesNo(default = True)
config.EMC.movie_ignore_firstcuts = ConfigYesNo(default = True)
config.EMC.movie_rewind_finished = ConfigYesNo(default = True)
config.EMC.movie_save_lastplayed = ConfigYesNo(default = False)
config.EMC.movie_metaload = ConfigYesNo(default = True)
config.EMC.movie_exit = ConfigYesNo(default = False)
config.EMC.movie_reopen = ConfigYesNo(default = True)
config.EMC.movie_reopenEOF = ConfigYesNo(default = True)
config.EMC.movie_reload = ConfigYesNo()
config.EMC.CoolMovieNr = ConfigYesNo(default = False)
config.EMC.CoolFormat = ConfigYesNo(default = True)
config.EMC.movie_homepath = ConfigText(default = "/hdd/movie", fixed_size = False, visible_width = 22)
config.EMC.movie_pathlimit = ConfigText(default = "/hdd/movie", fixed_size = False, visible_width = 22)
config.EMC.movie_trashpath = ConfigText(default = "/hdd/movie/trashcan", fixed_size = False, visible_width = 22)
config.EMC.movie_trashcan_hide = ConfigYesNo(default = False)
config.EMC.movie_trashcan_clean = ConfigYesNo(default = True)
config.EMC.movie_trashcan_limit = ConfigSelectionNumber(0, 99, 1, default = 3)
config.EMC.movie_finished_clean = ConfigYesNo(default = False)
config.EMC.movie_finished_limit = ConfigSelectionNumber(0, 99, 1, default = 10)
config.EMC.movie_trashcan_ctime = ConfigClock(default = 0)
config.EMC.movie_trashcan_validation = ConfigYesNo(default = True)
config.EMC.movie_vlc_hide = ConfigYesNo(default = True)
config.EMC.movie_hide_mov = ConfigYesNo(default = False)
config.EMC.movie_hide_del = ConfigYesNo(default = False)
config.EMC.CoolStartAZ = ConfigYesNo(default = False)
config.EMC.moviecenter_reversed = ConfigYesNo(default = False)
config.EMC.moviecenter_gotonewest = ConfigYesNo()
config.EMC.moviecenter_gotonewestp = ConfigYesNo()
config.EMC.moviecenter_selmove = ConfigSelection(default = "d", choices = [("d", _("down")), ("b", _("up/down")), ("o", _("off"))])
config.EMC.moviecenter_loadtext = ConfigYesNo(default = True)
config.EMC.timer_autocln = ConfigYesNo(default = False)

launch_choices = [	("None", _("No override")),
					("showMovies", _("Video-button")),
					("showTv", _("TV-button")),
					("showRadio", _("Radio-button")),
					("openQuickbutton", _("Quick-button")),
					("timeshiftStart", _("Timeshift-button"))]
config.EMC.movie_launch = ConfigSelection(default = "showMovies", choices = launch_choices)

gSession = None
gRecordings = None

def showMoviesNew(dummy_self = None):
	try:
		global gSession, gRecordings
		gSession.execDialog(gRecordings)
	except Exception, e:
		emcDebugOut("[showMoviesNew] exception:\n" + str(e))

def autostart(reason, **kwargs):
	if reason == 0: # start
		if kwargs.has_key("session"):
			global gSession
			gSession = kwargs["session"]
			
			EMCStartup(gSession)
			emcTasker.Initialize(gSession)
			
			if not config.EMC.ml_disable.value:
				try:
					from Screens.InfoBar import InfoBar
					value = config.EMC.movie_launch.value
					if value == "showMovies":			InfoBar.showMovies = showMoviesNew
					elif value == "showTv":				InfoBar.showTv = showMoviesNew
					elif value == "showRadio":			InfoBar.showRadio = showMoviesNew
					elif value == "openQuickbutton":	InfoBar.openQuickbutton = showMoviesNew
					elif value == "timeshiftStart":		InfoBar.startTimeshift = showMoviesNew
				except Exception, e:
					emcDebugOut("[spStartup] MovieCenter launch override exception:\n" + str(e))
				
				try:
					global gRecordings
					from MovieSelection import EMCSelection
					gRecordings = gSession.instantiateDialog(EMCSelection)
				except Exception, e:
					emcDebugOut("[spStartup] instantiateDialog exception:\n" + str(e))

def pluginOpen(session, **kwargs):
	try:
		session.open(EnhancedMovieCenterMenu)
	except Exception, e:
		emcDebugOut("[pluginOpen] exception:\n" + str(e))

def recordingsOpen(session, **kwargs):
	showMoviesNew()

def Plugins(**kwargs):
	localeInit()
	descriptors = []
	
	descriptors.append( PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart) )
	
	show_p = [ PluginDescriptor.WHERE_PLUGINMENU ]
	if config.EMC.extmenu_plugin.value:
		show_p.append( PluginDescriptor.WHERE_EXTENSIONSMENU )
	descriptors.append( PluginDescriptor(name = "Enhanced Movie Center "+EMCVersion+ " (Setup)", description = "Enhanced Movie Center " +_("configuration"), icon = "/EnhancedMovieCenter.png", where = show_p, fnc = pluginOpen) )

	if config.EMC.extmenu_list.value and not config.EMC.ml_disable.value:
		descriptors.append( PluginDescriptor(name = "Enhanced Movie Center", description = "Enhanced Movie Center " + _("movie manipulation list"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = recordingsOpen) )
	return descriptors
