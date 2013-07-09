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

from Components.config import *
from Components.ActionMap import ActionMap
from enigma import eActionMap
from keyids import KEYIDS
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Components.Sources import EMCCurrentService
from Components.Sources import EMCServiceEvent
from Components.Renderer import EMCPositionGauge
from Components.Converter import EMCClockToText
from Components.Converter import EMCEventName
from Components.Converter import EMCServicePosition
from Components.Converter import EMCRecordPosition
from Components.Converter import EMCServiceTime

from __init__ import _, language
from EMCTasker import emcTasker, emcDebugOut
import copy


class ConfigTextWOHelp(ConfigText):
	def __init__(self, default = "", fixed_size = True, visible_width = False):
		ConfigText.__init__(self, default, fixed_size, visible_width)

	def onSelect(self, session):
		ConfigText.onSelect(self, None)

	def onDeselect(self, session):
		ConfigText.onDeselect(self, None)


yes_no_descriptions = {False: _("no"), True: _("yes")}
class ConfigYesNoConfirm(ConfigBoolean):
	def __init__(self, text, key1, key2, default = False):
		self.text = text
		self.key1 = key1
		self.key2 = key2
		ConfigBoolean.__init__(self, default = default, descriptions = yes_no_descriptions)
		self.session = None

	def handleKey(self, key):
		if key in (KEY_LEFT, KEY_RIGHT):
			if self.value:
				self.value = False
			else:
				self.confirm()
		elif key == KEY_HOME:
			self.value = False
		elif key == KEY_END:
			self.confirm()

	def onSelect(self, session):
		self.session = session

	def confirm(self):
		if self.session:
			self.session.openWithCallback(self.confirmed, ConfirmBox, self.text, self.key1, self.key2, MessageBox.TYPE_INFO)

	def confirmed(self, answer):
		if self.value != answer:
			self.value = answer


class ConfirmBox(MessageBox):
	def __init__(self, session, text, key1, key2, type):
		MessageBox.__init__(self, session, text=text, type=type, enable_input=False)
		self.skinName = "MessageBox"
		self["actions"] = ActionMap(["OkCancelActions","ColorActions"], 
			{
				"ok": self.cancel,
				"cancel": self.cancel,
				key1: self.firstAction,
				key2: self.secondAction,
			}, -1)
		self.firstKey = False
		eActionMap.getInstance().bindAction('', 0x7FFFFFFF, self.action) 

	def firstAction(self):
		self.firstKey = True

	def secondAction(self):
		if self.firstKey:
			self.closeConfirmBox(True)

	#this function is called on every keypress!
	def action(self, key=0, flag=0):
		if flag == 0:
			self.firstKey = False

	def cancel(self):
		self.closeConfirmBox(False)

	def closeConfirmBox(self, answer):
		eActionMap.getInstance().unbindAction('', self.action)
		self.close(answer)


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

launch_choices = [	("None",			_("No override")),
					("showMovies",		_("Video-button")),
					("showTv",			_("TV-button")),
					("showRadio",		_("Radio-button")),
					("openQuickbutton",	_("Quick-button")),
					("timeshiftStart",	_("Timeshift-button")) ]

# Date format is implemented using datetime.strftime
date_choices = [	("",					_("Off")),
					("%d.%m.%Y",			_("DD.MM.YYYY")),
					("%d.%m %H:%M",			_("DD.MM HH:MM")),
					("%d.%m. %H:%M",		_("DD.MM. HH:MM")),
					("%Y/%m/%d",			_("YYYY/MM/DD")),
					("%m/%d %H:%M",			_("MM/DD HH:MM")) ]

dirinfo_choices = [	("",	_("Off")),
					("C",	_("( # )")),		# Count
					("CS",	_("( # / GB )")),	# Count / Size
					("S",	_("( GB )")) ]		# Size

progress_choices = [("PB",	_("ProgressBar")),
					("P",	_("Percent (%)")),
					("MC",	_("Movie Color")),
					("",	_("Off")) ]

#blueyellowgreen_choices = 	[("MH",	_("Movie home")),
#							 ("MV", _("Move Movie")),
#							 ("PL",	_("Play last")),
#							 ("CS",	_("Cover Search")),
#							 ("MI",	_("Download Movie Info")),
#							 ("CP", _("Copy File")),
#							 ("E2", _("Open E2 bookmarks"))]

colorbutton_choices = 	[("MH",	_("Movie home")),
							 ("DL",	_("Delete")),
							 ("MV",	_("Move Movie")),
							 ("PL",	_("Play last")),
							 ("CS",	_("Cover Search")),
							 ("MI",	_("Download Movie Info")),
							 ("CP",	_("Copy File")),
							 ("E2",	_("Open E2 bookmarks")),
							 ("TC",	_("Toggle Cover Button")),
							 ("",		_("Button disabled"))]

red_choices = colorbutton_choices
green_choices = copy.copy(colorbutton_choices)
green_choices.extend([("ST", _("Sort Options"))])
yellow_choices = colorbutton_choices
blue_choices = colorbutton_choices

#green_choices = copy.copy(blueyellowgreen_choices)
#longblueyellowgreen_choices = copy.copy(blueyellowgreen_choices)

longcolorbutton_choices = 	[("MH",	_("Movie home")),
							 ("DL",	_("Delete")),
							 ("MV",	_("Move Movie")),
							 ("PL",	_("Play last")),
							 ("CS",	_("Cover Search")),
							 ("MI",	_("Download Movie Info")),
							 ("CP",	_("Copy File")),
							 ("E2",	_("Open E2 bookmarks")),
#							 ("TC",	_("Toggle Cover Button")),
							 ("",		_("Button disabled"))]

#longblueyellowgreen_choices.extend()

longred_choices = longcolorbutton_choices
#longgreen_choices = blueyellowgreen_choices
longyellow_choices = longcolorbutton_choices
longblue_choices = longcolorbutton_choices

move_choices = [("d",	_("down")),
				("b",	_("up/down")),
				("o",	_("off")) ]

bookmark_choices = [("No",		_("No")),
					("E2",		_("E2 Bookmarks")),
					("EMC",		_("EMC Bookmarks")),
					("Both",	_("Both")) ]

restart_choices = [	("",	_("No")),
					("0",	_("Standby")),
					("1",	_("DeepStandby")),
					("2",	_("Reboot")),
					("3",	_("E2 Restart"))]

bqt_choices = [	("",		_("HomeEnd")),
				("Skip",	_("Skip")),
				("Folder",	_("Change Folder"))]

#Think about using AZ or ("A",False) as dict key / permanent sort store value
#TODO use an OrderedDict
sort_modes =	{		("D-")	:	( _("Date sort descending (D-)"),		("D",False),	_("Date sort"),		),
						("AZ")	:	( _("Alpha sort ascending (AZ)"),		("A",False),	_("Alpha sort"),	),
						("P+")	:	( _("Progress sort ascending (P+)"),	("P",False),	_("Progress sort"),	),
						("D+")	:	( _("Date sort ascending (D+)"),		("D",True),		_("Date sort"),		),
						("ZA")	:	( _("Alpha sort descending (ZA)"),		("A",True),		_("Alpha sort"),	),
						("P-")	:	( _("Progress sort descending (P-)"),	("P",True),		_("Progress sort"),	),
				}
									# If you add a new sort order, you have to think about
									#  Order false has to be the preferred state
									#  Both order possibilities should be in the list
									# Following functions are invoved, but they are all implemented dynamically 
									#  MovieCenter.reload -> Add new parameter if necessary
									#   Don't worry about buildMovieCenterEntry(*args):
									#  MovieSelection.initButtons -> Set next button text
									#  Green short will go through all types: D A
									#  Green long will only toggle the sort order: normal reverse

sort_choices = [ (k, v[0]) for k, v in sort_modes.items() ]

config.EMC                           = ConfigSubsection()
config.EMC.needsreload               = ConfigYesNo(default = False)
config.EMC.about                     = ConfigSelection(default = "1", choices = [("1", " ")])
config.EMC.extmenu_plugin            = ConfigYesNo(default = False)
config.EMC.extmenu_list              = ConfigYesNo(default = False)
config.EMC.epglang                   = ConfigSelection(default = language.getActiveLanguage(), choices                    = langList())
config.EMC.sublang1                  = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices  = langList())
config.EMC.sublang2                  = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices  = langList())
config.EMC.sublang3                  = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices  = langList())
config.EMC.audlang1                  = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices  = langList())
config.EMC.audlang2                  = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices  = langList())
config.EMC.audlang3                  = ConfigSelection(default = language.lang[language.getActiveLanguage()][0], choices  = langList())
config.EMC.autosubs                  = ConfigYesNo(default = False)
config.EMC.autoaudio                 = ConfigYesNo(default = False)
config.EMC.key_period                = ConfigSelectionNumber(50, 900, 50, default = 100)
config.EMC.key_repeat                = ConfigSelectionNumber(250, 900, 50, default= 500)
config.EMC.restart                   = ConfigSelection(choices = restart_choices, default = "")
config.EMC.restart_begin             = ConfigClock(default = 60 * 60 * 2)
config.EMC.restart_end               = ConfigClock(default = 60 * 60 * 5)
config.EMC.restart_stby              = ConfigYesNo(default = False)
config.EMC.debug                     = ConfigYesNo(default = False)
config.EMC.folder                    = ConfigTextWOHelp(default = "/hdd/EMC", fixed_size = False, visible_width= 22)
config.EMC.debugfile                 = ConfigTextWOHelp(default = "output.txt", fixed_size = False, visible_width= 22)
config.EMC.ml_disable                = ConfigYesNo(default = False)
config.EMC.files_cache               = ConfigYesNo(default = False)
# Color keys selection list array dict: longdescription, shortdescription, functionpointer
config.EMC.movie_redfunc             = ConfigSelection(default = "DL", choices = red_choices)
config.EMC.movie_greenfunc           = ConfigSelection(default = "ST", choices = green_choices)
config.EMC.movie_yellowfunc          = ConfigSelection(default = "MV", choices = yellow_choices)
config.EMC.movie_bluefunc            = ConfigSelection(default = "MH", choices = blue_choices)
config.EMC.movie_longredfunc         = ConfigSelection(default = "DL", choices = longred_choices)
#config.EMC.movie_longgreenfunc       = ConfigSelection(default = "CS", choices = longgreen_choices)
config.EMC.movie_longyellowfunc      = ConfigSelection(default = "MV", choices = longyellow_choices)
config.EMC.movie_longbluefunc        = ConfigSelection(default = "MH", choices = longblue_choices)
config.EMC.CoolStartHome             = ConfigYesNo(default = False)
config.EMC.movie_descdelay           = ConfigSelectionNumber(50, 60000, 50, default= 200)
config.EMC.movie_cover               = ConfigYesNo(default = False)
config.EMC.movie_cover_delay         = ConfigSelectionNumber(50, 60000, 50, default= 500)
config.EMC.movie_preview             = ConfigYesNo(default = False)
config.EMC.movie_preview_delay       = ConfigSelectionNumber(50, 60000, 50, default= 2000)
config.EMC.movie_preview_offset      = ConfigSelectionNumber(0, 60000, 1, default= 5)
config.EMC.skin_able                 = ConfigYesNo(default = False)
config.EMC.movie_icons               = ConfigYesNo(default = True)
config.EMC.link_icons                = ConfigYesNo(default = True)
config.EMC.movie_progress            = ConfigSelection(default = "PB", choices = progress_choices)
config.EMC.movie_watching_percent    = ConfigSelectionNumber(0, 30, 1, default = 5)
config.EMC.movie_finished_percent    = ConfigSelectionNumber(50, 100, 1, default = 80)
config.EMC.movie_date_format         = ConfigSelection(default = "%d.%m %H:%M", choices = date_choices)
config.EMC.movie_ignore_firstcuts    = ConfigYesNo(default = True)
config.EMC.movie_jump_first_mark     = ConfigYesNo(default = True)
config.EMC.movie_rewind_finished     = ConfigYesNo(default = True)
config.EMC.movie_save_lastplayed     = ConfigYesNo(default = False)
config.EMC.record_eof_zap            = ConfigYesNo(default = True)
config.EMC.record_show_real_length   = ConfigYesNo(default = True)
config.EMC.cutlist_at_download       = ConfigYesNo(default = False)
config.EMC.movie_metaload            = ConfigYesNo(default = True)
config.EMC.movie_eitload             = ConfigYesNo(default = False)
config.EMC.movie_exit                = ConfigYesNo(default = False)
config.EMC.movie_reopen              = ConfigYesNo(default = True)
config.EMC.movie_reopenEOF           = ConfigYesNo(default = True)
config.EMC.movie_reload              = ConfigYesNo(default = False)
config.EMC.movie_show_cutnr          = ConfigYesNo(default = False)
config.EMC.movie_show_format         = ConfigYesNo(default = False)
config.EMC.movie_real_path           = ConfigYesNo(default = True)
config.EMC.movie_homepath            = ConfigTextWOHelp(default = "/hdd/movie", fixed_size  = False, visible_width= 22)
config.EMC.movie_pathlimit           = ConfigTextWOHelp(default = "/hdd/movie", fixed_size = False, visible_width= 22)
config.EMC.movie_trashcan_enable     = ConfigYesNo(default = True)
config.EMC.movie_trashcan_path       = ConfigTextWOHelp(default = "/hdd/movie/trashcan", fixed_size = False, visible_width= 22)
config.EMC.movie_trashcan_show       = ConfigYesNo(default = True)
config.EMC.movie_trashcan_info       = ConfigSelection(default = "C", choices = dirinfo_choices)
config.EMC.movie_trashcan_clean      = ConfigYesNo(default = True)
config.EMC.movie_trashcan_limit      = ConfigSelectionNumber(1, 99, 1, default = 3)
config.EMC.movie_finished_clean      = ConfigYesNoConfirm(default = False, text = _("ATTENTION\n\nThis option will move all finished movies in Movie Home automatically to Your trashcan at the given time.\nAt next trashcan cleanup all movies will be deleted.\n\nConfirm this with the blue key followed by the green key."), key1="blue", key2="green")
config.EMC.movie_finished_limit      = ConfigSelectionNumber(1, 99, 1, default = 10)
config.EMC.movie_trashcan_ctime      = ConfigClock(default = 0)
config.EMC.movie_delete_validation   = ConfigYesNo(default = True)
config.EMC.directories_show          = ConfigYesNo(default = True)
config.EMC.symlinks_show             = ConfigYesNo(default = True)
config.EMC.directories_ontop         = ConfigYesNo(default = False)
config.EMC.cfgtopdir_enable          = ConfigYesNo(default = False)
config.EMC.directories_info          = ConfigSelection(default = "", choices = dirinfo_choices)
#config.EMC.symlinkdir_info           = ConfigYesNo(default = False)
config.EMC.latest_recordings         = ConfigYesNo(default = True)
config.EMC.mark_latest_files         = ConfigYesNo(default = True)
config.EMC.vlc                       = ConfigYesNo(default = False)
config.EMC.bookmarks                 = ConfigSelection(default = "No", choices = bookmark_choices)
config.EMC.check_dvdstruct           = ConfigYesNo(default = True)
config.EMC.check_moviestruct         = ConfigYesNo(default = False)
config.EMC.check_blustruct           = ConfigYesNo(default = True)
#config.EMC.check_movie_cutting      = ConfigYesNo(default = True)
config.EMC.movie_hide_mov            = ConfigYesNo(default = False)
config.EMC.movie_hide_del            = ConfigYesNo(default = False)
config.EMC.moviecenter_sort          = ConfigSelection(default = ("D-"), choices = sort_choices)
config.EMC.moviecenter_selmove       = ConfigSelection(default = "d", choices = move_choices)
config.EMC.moviecenter_loadtext      = ConfigYesNo(default = True)
config.EMC.replace_specialchars      = ConfigYesNo(default = False)
config.EMC.timer_autocln             = ConfigYesNo(default = False)
config.EMC.movie_launch              = ConfigSelection(default = "showMovies", choices = launch_choices)
config.EMC.scan_linked               = ConfigYesNo(default = False)
config.EMC.cfghide_enable            = ConfigYesNo(default = False)
config.EMC.cfgscan_suppress          = ConfigYesNo(default = False)
config.EMC.remote_recordings         = ConfigYesNo(default = False)
config.EMC.bqt_keys                  = ConfigSelection(default = "", choices = bqt_choices)
config.EMC.list_skip_size            = ConfigSelectionNumber(3, 10, 1, default = 5)

config.EMC.InfoLong                  = ConfigSelection(choices = [("IMDbSearch", _("IMDb Search")), ("TMDBInfo", _("TMDB Info")), ('CSFDInfo', _('CSFD Info'))], default = "IMDbSearch")

def checkList(cfg):
	for choices in cfg.choices.choices:
		if cfg.value == choices[0]:
			return
	for choices in cfg.choices.choices:
		if cfg.default == choices[0]:
			cfg.value = cfg.default
			return
	cfg.value = cfg.choices.choices[0][0]

checkList(config.EMC.epglang)
checkList(config.EMC.sublang1)
checkList(config.EMC.sublang2)
checkList(config.EMC.sublang3)
checkList(config.EMC.audlang1)
checkList(config.EMC.audlang2)
checkList(config.EMC.audlang3)

gSession = None

def showMoviesNew(dummy_self = None):
	try:
		global gSession
		from MovieSelection import EMCSelection
		gSession.openWithCallback(showMoviesCallback, EMCSelection)
	except Exception, e:
		emcDebugOut("[showMoviesNew] exception:\n" + str(e))

def showMoviesCallback(*args):
	try:
		if args:
			global gSession
			from EMCMediaCenter import EMCMediaCenter
			gSession.openWithCallback(playerCallback, EMCMediaCenter, *args)
	except Exception, e:
		emcDebugOut("[showMoviesCallback] exception:\n" + str(e))

def playerCallback(reopen, *args):
	if reopen:
		showMoviesNew(*args)

def autostart(reason, **kwargs):
	if reason == 0: # start
		if kwargs.has_key("session"):
			global gSession
			from EnhancedMovieCenter import EMCStartup
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
				
				#try:
				#	from MovieSelection import EMCSelection
				#	gSession.openWithCallback(showMoviesCallback, EMCSelection)
				#except Exception, e:
				#	emcDebugOut("[spStartup] instantiateDialog exception:\n" + str(e))

def pluginOpen(session, *args, **kwargs):
	try:
		from EnhancedMovieCenter import EnhancedMovieCenterMenu
		session.open(EnhancedMovieCenterMenu)
	except Exception, e:
		emcDebugOut("[pluginOpen] exception:\n" + str(e))

def recordingsOpen(session, *args, **kwargs):
	from MovieSelection import EMCSelection
	session.openWithCallback(showMoviesCallback, EMCSelection)

def Plugins(**kwargs):
	from EnhancedMovieCenter import EMCVersion
	descriptors = []
	
	descriptors.append( PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart) )
	
	show_p = [ PluginDescriptor.WHERE_PLUGINMENU ]
	if config.EMC.extmenu_plugin.value:
		show_p.append( PluginDescriptor.WHERE_EXTENSIONSMENU )
	descriptors.append( PluginDescriptor(name = "EMC "+EMCVersion+ " (Setup)", description = "Enhanced Movie Center " +_("configuration"), icon = "EnhancedMovieCenter.png", where = show_p, fnc = pluginOpen) )

	if config.EMC.extmenu_list.value and not config.EMC.ml_disable.value:
		descriptors.append( PluginDescriptor(name = "Enhanced Movie Center", description = "Enhanced Movie Center " + _("movie manipulation list"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = recordingsOpen) )
	return descriptors
