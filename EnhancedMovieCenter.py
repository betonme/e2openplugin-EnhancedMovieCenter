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

from __init__ import _
from Components.config import *
from Components.config import config
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.Language import *
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ServiceScan import *
import Screens.Standby
from Tools import Notifications
from enigma import eServiceEvent, eActionMap
import os, struct
import NavigationInstance

from DelayedFunction import DelayedFunction
from EMCTasker import emcTasker, emcDebugOut

EMCVersion = "V2.1.0"
EMCAbout = "\n  Enhanced Movie Center " +EMCVersion+ "\n\n  (C) 2011 by\n  Coolman, Betonme & Swiss-MAD \n\n  If you like this plugin and you want to support it,\n  or if just want to say ''thanks'',\n  please donate via PayPal. \n\n  Thanks a lot ! \n\n  PayPal: enhancedmoviecenter@gmail.com"

def setEPGLanguage(dummyself=None, dummy=None):
	if config.EMC.epglang.value:
		emcDebugOut("Setting EPG language: " + str(config.EMC.epglang.value))
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
language.addCallback(setEPGLanguage)
DelayedFunction(5000, setEPGLanguage)

def setupKeyResponseValues(dummyself=None, dummy=None):
	# currently not working on DM500/DM600, wrong input dev files?
	e1 = os.open("/dev/input/event0", os.O_RDWR)
	e2 = os.open("/dev/input/event0", os.O_RDWR)
	s1 = struct.pack("LLHHl", 0, 0, 0x14, 0x00, int(config.EMC.key_repeat.value))
	s2 = struct.pack("LLHHl", 0, 0, 0x14, 0x01, int(config.EMC.key_period.value))
	size = struct.calcsize("LLHHl")
	os.write(e1, s1)
	os.write(e2, s1)
	os.write(e1, s2)
	os.write(e2, s2)
	os.close(e1)
	os.close(e2)

# Only one trashclean instance is allowed
trashCleanCall = None

def cleanupSetup(dummy=None):
	try:
		from MovieSelection import gMS
		global trashCleanCall
		if trashCleanCall is not None:
			if trashCleanCall.exists():
				trashCleanCall.cancel()
		if config.EMC.movie_trashcan_enable.value and config.EMC.movie_trashcan_clean.value or config.EMC.movie_finished_clean.value:
			from time import time
			recordings = NavigationInstance.instance.getRecordings()
			rec_time = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			cltime = config.EMC.movie_trashcan_ctime.value
			lotime = localtime()
			ltime = lotime[3]*60 + lotime[4]
			ctime = cltime[0]*60 + cltime[1]
			seconds = 60 * (ctime - ltime)
			if recordings or rec_time > 0 and (rec_time - time()) < 600: # no more recordings exist
				DelayedFunction(1800000, cleanupSetup)
				emcDebugOut("recordings exist... so next trashcan cleanup in " + str(seconds/60) + " minutes")
			else:
				if seconds <= 0:
					seconds += 86400	# 24*60*60
				# Recall setup funktion
				trashCleanCall = DelayedFunction(1000*seconds, cleanupSetup)
				# Execute trash cleaning
				DelayedFunction(2000, gMS.purgeExpired)
				emcDebugOut("Next trashcan cleanup in " + str(seconds/60) + " minutes")
	except Exception, e:
		emcDebugOut("[sp] cleanupSetup exception:\n" + str(e))

def EMCStartup(session):
	emcDebugOut("+++ EMC "+EMCVersion+" startup")
	
	if not os.path.exists(config.EMC.folder.value):
		emcTasker.shellExecute("mkdir " + config.EMC.folder.value)
	
	if config.EMC.epglang.value:
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
	
	setupKeyResponseValues()
	DelayedFunction(5000, cleanupSetup)

	# Go into standby if the reason for restart was EMC auto-restart
	if config.EMC.enigmarestart.value:
		flag = os.path.join(config.EMC.folder.value, "EMC_standby_flag.tmp")
		if os.path.exists(flag):
			emcDebugOut("+++ Going into Standby mode after auto-restart")
			Notifications.AddNotification(Screens.Standby.Standby)
			emcTasker.shellExecute("rm -f " + flag)


class EnhancedMovieCenterMenu(ConfigListScreen, Screen):
	skin = """
		<screen name="EnhancedMovieCenterMenu" position="center,center" size="620,500" title="EnhancedMovieCenterMenu">
		<widget name="config" position="10,10" size="605,353 " enableWrapAround="1" scrollbarMode="showOnDemand" />
		<eLabel position="0,362" size="620,2" backgroundColor="#999999" zPosition="1" />
		<widget source="help" render="Label" position="10,367" size="605,88" font="Regular;20" foregroundColor="#999999" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="66,455" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green.png" position="412,455" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<widget name="key_red" position="66,455" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
		<widget name="key_green" position="412,455" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
	</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "EnhancedMovieCenterMenu"
		self.skin = EnhancedMovieCenterMenu.skin
		
		self["actions"] = ActionMap(["ChannelSelectBaseActions", "OkCancelActions", "ColorActions"],
		{
			"ok":			self.keyOK,
			"cancel":		self.keyCancel,
			"red":			self.keyCancel,
			"green": 		self.keySaveNew,
			"nextBouquet":	self.bouquetPlus,
			"prevBouquet":	self.bouquetMinus,
		}, -2) # higher priority
		
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
#		self["key_yellow"] = Button(" ")
#		self["key_blue"] = Button(" ")
		self["help"] = StaticText()
		
		self.list = []
		self.EMCConfig = []
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)
		self.needsRestartFlag = False
		self.defineConfig()
		self.createConfig()
		
		# Override selectionChanged because our config tuples have a size bigger than 2 
		def selectionChanged():
			current = self["config"].getCurrent()
			if self["config"].current != current:
				if self["config"].current:
					self["config"].current[1].onDeselect(self.session)
				if current:
					current[1].onSelect(self.session)
				self["config"].current = current
			for x in self["config"].onSelectionChanged:
				x()
		self["config"].selectionChanged = selectionChanged
		self["config"].onSelectionChanged.append(self.updateHelp)
		
		#Todo Remove if there is another solution
		config.EMC.movie_finished_clean.addNotifier(self.changedEntry, initial_call = False, immediate_feedback = True)
		
		self.onShow.append(self.onDialogShow)

	def defineConfig(self):
		
		separator = "".ljust(250,"-")
		
#         _config list entry                                
#         _                                                 , config element                     
#         _                                                 ,                                     , function called on save
#         _                                                 ,                                     ,                       , function called if user has pressed OK
#         _                                                 ,                                     ,                       ,                       , usage setup level from E2
#         _                                                 ,                                     ,                       ,                       ,   0: simple+
#         _                                                 ,                                     ,                       ,                       ,   1: intermediate+
#         _                                                 ,                                     ,                       ,                       ,   2: expert+
#         _                                                 ,                                     ,                       ,                       ,       , depends on relative parent entries
#         _                                                 ,                                     ,                       ,                       ,       ,   parent config value must be true
#         _                                                 ,                                     ,                       ,                       ,       ,   a selection value "" is False 
#         _                                                 ,                                     ,                       ,                       ,       ,           , _context sensitive help text
		self.EMCConfig = [	
			(  _("About")                                         , config.EMC.about                    , None                  , self.showInfo         , 0     , []        , _("HELP_About") ),
			
			(  _("Disable EMC")                                   , config.EMC.ml_disable               , self.needsRestart     , None                  , 1     , []        , _("HELP_Disable EMC") ),
			
			(  _("Start EMC with")                                , config.EMC.movie_launch             , self.launchListSet    , None                  , 0     , []        , _("HELP_Start EMC with") ),
			(  _("Show plugin config in extensions menu")         , config.EMC.extmenu_plugin           , self.needsRestart     , None                  , 0     , []        , _("HELP_Show plugin config in extensions menu") ),
			(  _("Show EMC in extensions menu")                   , config.EMC.extmenu_list             , self.needsRestart     , None                  , 0     , []        , _("HELP_Show EMC in extensions menu") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),
			(  _("Movie home at start")                           , config.EMC.CoolStartHome            , None                  , None                  , 0     , []        , _("HELP_Movie home at start") ),
			(  _("Sort file A to Z at startup")                   , config.EMC.CoolStartAZ              , None                  , None                  , 0     , []        , _("HELP_Sort file A to Z at startup") ),
			(  _("File order reverse")                            , config.EMC.moviecenter_reversed     , None                  , None                  , 0     , []        , _("HELP_File order reverse") ),
			
			(  _("Movie home home path")                          , config.EMC.movie_homepath           , self.validatePath     , self.openLocationBox  , 0     , []        , _("HELP_Movie home home path") ),
			(  _("EMC path access limit")                         , config.EMC.movie_pathlimit          , self.validatePath     , self.openLocationBox  , 1     , []        , _("HELP_EMC path access limit") ),
			
			(  _("Cursor predictive move after selection")        , config.EMC.moviecenter_selmove      , None                  , None                  , 0     , []        , _("HELP_Cursor predictive move after selection") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),
			(  _("Show directories")                              , config.EMC.directories_show         , None                  , None                  , 0     , []        , _("HELP_Show directories") ),		
			(  _("Show directories information")                  , config.EMC.directories_info         , None                  , None                  , 0     , [-1]        , _("HELP_Show directories information") ),		
			(  _("Show Latest Recordings directory")              , config.EMC.latest_recordings        , None                  , None                  , 0     , []        , _("HELP_Show Latest Recordings directory") ),
			(  _("Show VLC directory")                            , config.EMC.vlc                      , None                  , None                  , 0     , []        , _("HELP_Show VLC directory") ),
			(  _("Show E2 Bookmarks in movielist")                , config.EMC.bookmarks_e2             , None                  , None                  , 0     , []        , _("HELP_Show E2 Bookmarks in movielist") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 1     , []        , _("HELP_separator_hide&performance") ),
			(  _("Hide selected entries in movielist")            , config.EMC.cfghide_enable           , None                  , None                  , 1     , []        , _("HELP_cfghide_enable") ),
			(  _("Scan for DVD structures")                       , config.EMC.check_dvdstruct          , None                  , None                  , 1     , []        , _("HELP_Scan for DVD structures") ),
			(  _("No structure scan in selected folders")         , config.EMC.cfgnoscan_enable         , None                  , None                  , 1     , []        , _("HELP_cfgnoscan_enable") ),
			(  _("No structure scan in linked folders")           , config.EMC.noscan_linked            , None                  , None                  , 1     , []        , _("HELP_noscan_linked") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),
			(  _("Try to load titles from .meta files")           , config.EMC.movie_metaload           , None                  , None                  , 0     , []        , _("HELP_Try to load titles from .meta files") ),
			(  _("Try to load titles from .eit files")            , config.EMC.movie_eitload            , None                  , None                  , 0     , []        , _("HELP_Try to load titles from .eit files") ),
			(  _("Show Movie Format")                             , config.EMC.movie_show_format        , None                  , None                  , 0     , []        , _("HELP_Show Movie Format") ),
			(  _("Show Cut-Nr if exist")                          , config.EMC.movie_show_cutnr         , None                  , None                  , 0     , []        , _("HELP_Show Cut-Nr if exist") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),
			(  _("Listbox is skin able")                          , config.EMC.skin_able                , None                  , None                  , 0     , []        , _("HELP_Listbox is skin able") ),
			
			(  _("Date format")                                   , config.EMC.movie_date_format        , None                  , None                  , 0     , []        , _("HELP_Date format") ),
			
			(  _("Show movie icons")                              , config.EMC.movie_icons              , None                  , None                  , 0     , []        , _("HELP_Show movie icons") ),
			(  _("Show movie progress")                           , config.EMC.movie_progress           , None                  , None                  , 0     , []        , _("HELP_Show movie progress") ),
			(  _("Short watching percent")                        , config.EMC.movie_watching_percent   , None                  , None                  , 0     , [-1]      , _("HELP_Short watching percent") ),
			(  _("Finished watching percent")                     , config.EMC.movie_finished_percent   , None                  , None                  , 0     , [-2]      , _("HELP_Finished watching percent") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),
			(  _("No resume below 10 seconds")                    , config.EMC.movie_ignore_firstcuts   , None                  , None                  , 1     , []        , _("HELP_No resume below 10 seconds") ),
			(  _("Jump to first mark when playing movie")         , config.EMC.movie_jump_first_mark    , None                  , None                  , 1     , []        , _("HELP_Jump to first mark when playing movie") ),
			(  _("Rewind finished movies before playing")         , config.EMC.movie_rewind_finished    , None                  , None                  , 1     , []        , _("HELP_Rewind finished movies before playing") ),
			(  _("Always save last played progress as marker")    , config.EMC.movie_save_lastplayed    , None                  , None                  , 1     , []        , _("HELP_Always save last played progress as marker") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("HELP_separator_Trashcan settings") ),
			(  _("Trashcan enable")                               , config.EMC.movie_trashcan_enable    , None                  , self.openLocationBox  , 0     , []        , _("HELP_Trashcan enable") ),
			(  _("Trashcan path")                                 , config.EMC.movie_trashcan_path      , self.validatePath     , self.openLocationBox  , 0     , [-1]        , _("HELP_Trashcan path") ),
			(  _("Show trashcan directory")                       , config.EMC.movie_trashcan_show      , None                  , None                  , 0     , [-2]        , _("HELP_Show trashcan directory") ),
			(  _("Show trashcan information")                     , config.EMC.movie_trashcan_info      , None                  , None                  , 0     , [-3,-1]        , _("HELP_Dynamic trashcan") ),
			(  _("Delete validation")                             , config.EMC.movie_delete_validation  , None                  , None                  , 0     , [-4]        , _("HELP_Delete validation") ),
			
			(  _("Enable daily trashcan cleanup")                 , config.EMC.movie_trashcan_clean     , self.trashCleanupSetup, None                  , 0     , [-5]        , _("HELP_Enable daily trashcan cleanup") ),
			(  _("Daily cleanup time")                            , config.EMC.movie_trashcan_ctime     , None                  , None                  , 0     , [-6,-1]      , _("HELP_Daily cleanup time") ),
			(  _("How many days files may remain in trashcan")    , config.EMC.movie_trashcan_limit     , None                  , None                  , 0     , [-7,-2]      , _("HELP_How many days files may remain in trashcan") ),
			(  _("Move finished movies in trashcan")              , config.EMC.movie_finished_clean     , None                  , None                  , 2     , [-8,-3]      , _("HELP_Move finished movies in trashcan") ),
			(  _("Age of finished movies in movie folder (days)") , config.EMC.movie_finished_limit     , None                  , None                  , 2     , [-9,-1]     , _("HELP_Age of finished movies in movie folder (days)") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 0     , []        , _("") ),
			(  _("Display directory reading text")                , config.EMC.moviecenter_loadtext     , None                  , None                  , 1     , []        , _("HELP_Display directory reading text") ),
			(  _("EMC always reload after open")                  , config.EMC.movie_reload             , None                  , None                  , 1     , []        , _("HELP_EMC always reload after open") ),
			(  _("EMC re-open list after STOP-press")             , config.EMC.movie_reopen             , None                  , None                  , 1     , []        , _("HELP_EMC re-open list after STOP-press") ),
			(  _("EMC re-open list after Movie end")              , config.EMC.movie_reopenEOF          , None                  , None                  , 1     , []        , _("HELP_EMC re-open list after Movie end") ),
			
			(  _("Leave Movie with Exit")                         , config.EMC.movie_exit               , None                  , None                  , 0     , []        , _("HELP_Leave Movie with Exit") ),
			(  _("Blue button function")                          , config.EMC.movie_bluefunc           , None                  , None                  , 0     , []        , _("HELP_Blue button function") ),
			
			(  _("Hide movies being moved")                       , config.EMC.movie_hide_mov           , None                  , None                  , 1     , []        , _("HELP_Hide movies being moved") ),
			(  _("Hide movies being deleted")                     , config.EMC.movie_hide_del           , None                  , None                  , 1     , []        , _("HELP_Hide movies being deleted") ),
			
			(  _("Enable remote recordings")                      , config.EMC.remote_recordings        , None                  , None                  , 1     , []        , _("HELP_Enable remote recordings") ),
			(  _("Automatic timers list cleaning")                , config.EMC.timer_autocln            , None                  , None                  , 1     , []        , _("HELP_Automatic timers list cleaning") ),
			
			(  _("Enigma daily auto-restart")                     , config.EMC.enigmarestart            , self.autoRestartInfo  , self.autoRestartInfo  , 1     , []        , _("HELP_Enigma daily auto-restart") ),
			(  _("Enigma auto-restart window begin")              , config.EMC.enigmarestart_begin      , None                  , None                  , 1     , [-1]      , _("HELP_Enigma auto-restart window begin") ),
			(  _("Enigma auto-restart window end")                , config.EMC.enigmarestart_end        , None                  , None                  , 1     , [-2]      , _("HELP_Enigma auto-restart window end") ),
			(  _("Force standby after auto-restart")              , config.EMC.enigmarestart_stby       , None                  , None                  , 1     , [-3]      , _("HELP_Force standby after auto-restart") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 1     , []        , _("HELP_Language Separator") ),
			(  _("Preferred EPG language")                        , config.EMC.epglang                  , setEPGLanguage        , None                  , 1     , []        , _("HELP_Preferred EPG language") ),
			(  _("Enable playback auto-subtitling")               , config.EMC.autosubs                 , None                  , None                  , 1     , []        , _("HELP_Enable playback auto-subtitling") ),
			(  _("Primary playback subtitle language")            , config.EMC.sublang1                 , None                  , None                  , 1     , [-1]      , _("HELP_Primary playback subtitle language") ),
			(  _("Secondary playback subtitle language")          , config.EMC.sublang2                 , None                  , None                  , 1     , [-2]      , _("HELP_Secondary playback subtitle language") ),
			(  _("Tertiary playback subtitle language")           , config.EMC.sublang3                 , None                  , None                  , 1     , [-3]      , _("HELP_Tertiary playback subtitle language") ),
			(  _("Enable playback auto-language selection")       , config.EMC.autoaudio                , None                  , None                  , 1     , []        , _("HELP_Enable playback auto-language selection") ),
			(  _("Primary playback audio language")               , config.EMC.audlang1                 , None                  , None                  , 1     , [-1]      , _("HELP_Primary playback audio language") ),
			(  _("Secondary playback audio language")             , config.EMC.audlang2                 , None                  , None                  , 1     , [-2]      , _("HELP_Secondary playback audio language") ),
			(  _("Tertiary playback audio language")              , config.EMC.audlang3                 , None                  , None                  , 1     , [-3]      , _("HELP_Tertiary playback audio language") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 2     , []        , _("HELP_Advanced options separator") ),
			(  _("Description field update delay")                , config.EMC.movie_descdelay          , None                  , None                  , 2     , []        , _("HELP_Description field update delay") ),
			(  _("Key period value (50-900)")                     , config.EMC.key_period               , setupKeyResponseValues, None                  , 2     , []        , _("HELP_Key period value (50-900)") ),
			(  _("Key repeat value (250-900)")                    , config.EMC.key_repeat               , setupKeyResponseValues, None                  , 2     , []        , _("HELP_Key repeat value (250-900)") ),
			
			(  separator                                          , config.EMC.about                    , None                  , None                  , 2     , []        , _("HELP_Advanced options separator") ),
			(  _("Enable EMC debug output")                       , config.EMC.debug                    , self.dbgChange        , None                  , 2     , []        , _("HELP_Enable EMC debug output") ),
			(  _("EMC output directory")                          , config.EMC.folder                   , self.validatePath     , self.openLocationBox  , 2     , [-1]      , _("HELP_EMC output directory") ),
			(  _("Debug output file name")                        , config.EMC.debugfile                , self.validatePath     , None                  , 2     , [-2]      , _("HELP_Debug output file name") ),
		]

	def createConfig(self):
		list = []
		for i, conf in enumerate( self.EMCConfig ):
			# 0 entry text
			# 1 variable
			# 2 validation
			# 3 pressed ok
			# 4 setup level
			# 5 parent entries
			# 6 help text
			# Config item must be valid for current usage setup level
			if config.usage.setup_level.index >= conf[4]:
				# Parent entries must be true
				for parent in conf[5]:
					if not self.EMCConfig[i+parent][1].value:
						break
				else:
					# loop fell through without a break
					list.append( getConfigListEntry( conf[0], conf[1], conf[2], conf[3], conf[4], conf[5], conf[6] ) )
#			try:
#				list.append( getConfigListEntry( _("Enable component video in A/V Settings"), config.av.yuvenabled, self.needsRestart, None, 2, [], _("") ) )
#			except: pass
		self.list = list
		self["config"].setList(self.list)

	def onDialogShow(self):
		self.setTitle("Enhanced Movie Center "+ EMCVersion + " (Setup)")

	# Overwrite Screen close function
	def close(self):
		#self.hide()
		self.session.openWithCallback(self.closeConfirm, MessageBox, EMCAbout, MessageBox.TYPE_INFO)

	def closeConfirm(self, dummy=None):
		# Call baseclass function
		Screen.close(self)

	def changedEntry(self, addNotifierDummy=None):
		self.createConfig()

	def updateHelp(self):
		cur = self["config"].getCurrent()
		self["help"].text = cur and cur[6] or ""

	def autoRestartInfo(self, dummy=None):
		emcTasker.ShowAutoRestartInfo()

	def bouquetPlus(self):
		self["config"].instance.moveSelection(self["config"].instance.pageUp)

	def bouquetMinus(self):
		self["config"].instance.moveSelection(self["config"].instance.pageDown)

	def dbgChange(self, element):
		if element.value == True:
			pass
		else:
			emcTasker.shellExecute("rm -f " + os.path.join(config.EMC.folder.value, config.EMC.debugfile.value))

	def dirSelected(self, res):
		if res is not None:
			res = os.path.normpath( res )
			self["config"].getCurrent()[1].value = res

	def keyOK(self):
		try:
			current = self["config"].getCurrent()
			current and current[3]( current[1] )
		except: pass

	def keySaveNew(self):
		config.EMC.needsreload.value = True
		for i, entry in enumerate( self.list ):
			if entry[1].isChanged():
				if entry[2] is not None:
					# execute value changed -function
					if entry[2](entry[1]) is not None:
						# Stop exiting, user has to correct the config
						return
				# Check parent entries
				for parent in entry[5]:
					if self.list[i+parent][2] is not None:
						# execute parent value changed -function
						if self.list[i+parent][2](self.EMCConfig[i+parent][1]) is not None:	
							# Stop exiting, user has to correct the config
							return
				entry[1].save()
		if self.needsRestartFlag:
			self.session.open(MessageBox, _("Some settings changes require GUI restart to take effect."), MessageBox.TYPE_INFO, 10)
		self.close()

	def launchListSet(self, element):
		if element is not None:
			self.needsRestart()

	def needsRestart(self, dummy=None):
		self.needsRestartFlag = True

	def openLocationBox(self, element):
		try:
			if element:
				path = os.path.normpath( element.value )
				from Screens.LocationBox import MovieLocationBox
				self.session.openWithCallback(self.dirSelected, MovieLocationBox, text = _("Choose directory"), dir = str(path)+"/", minFree = 100)
		except: pass

	def showRestart(self):
		emcTasker.ShowAutoRestartInfo()

	def showInfo(self, dummy=None):
		self.session.open(MessageBox, EMCAbout, MessageBox.TYPE_INFO)

	def validatePath(self, element):
		element.value = os.path.normpath( element.value )
		if not os.path.exists(element.value):
			self.session.open(MessageBox, _("Given path %s does not exist. Please change." % str(element.value)), MessageBox.TYPE_ERROR)
			return False

	def trashCleanupSetup(self, dummy=None):
		if not os.path.exists(config.EMC.movie_trashcan_path.value):
			try:
				os.makedirs(config.EMC.movie_trashcan_path.value)
			except Exception, e:
				self.session.open(MessageBox, _("Trashcan create failed. Check mounts and permissions."), MessageBox.TYPE_ERROR)
				emcDebugOut("[EMCMS] trashcanCreate exception:\n" + str(e))
		cleanupSetup()
	