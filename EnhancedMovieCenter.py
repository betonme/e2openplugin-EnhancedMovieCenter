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
from Components.Button import Button
from Components.ConfigList import ConfigListScreen
from Components.Language import *
from Screens.MessageBox import MessageBox
from Screens.ServiceScan import *
import Screens.Standby
from Tools import Notifications
from enigma import eServiceEvent
import os, struct
import NavigationInstance

from DelayedFunction import DelayedFunction
from EMCTasker import emcTasker, emcDebugOut


EMCVersion = "V2.0.2"
EMCAbout = "\n   Enhanced Movie Center " +EMCVersion+ ".\n\n   Plugin's usage is free.\n\n   and the source is licensed under GPL.\n\n   by .\n\n   Coolman & Swiss-MAD"


def setEPGLanguage(dummy=None):
	if config.EMC.epglang.value:
		emcDebugOut("Setting EPG language: " + str(config.EMC.epglang.value))
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
language.addCallback(setEPGLanguage)
DelayedFunction(5000, setEPGLanguage)

def setupKeyResponseValues(dummy=None):
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

trashCleanCall = None

def trashCleanSetup(dummyparam=None):
	try:
		from MovieSelection import gMS
		global trashCleanCall
		if trashCleanCall is not None:
			trashCleanCall.cancel()
		if config.EMC.movie_trashcan_clean.value is True or config.EMC.movie_finished_clean.value is True:
			from time import time
			recordings = NavigationInstance.instance.getRecordings()
			rec_time = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			cltime = config.EMC.movie_trashcan_ctime.value
			lotime = localtime()
			ltime = lotime[3]*60 + lotime[4]
			ctime = cltime[0]*60 + cltime[1]
			seconds = 60 * (ctime - ltime)
			
			if recordings or rec_time > 0 and (rec_time - time()) < 600: # no more recordings exist
				DelayedFunction(1800000, trashCleanSetup)
				emcDebugOut("recordings exist... so next trashcan cleanup in " + str(seconds/60) + " minutes")
			else:
				if seconds < 0:
					seconds += 86400	# 24*60*60
				trashCleanCall = DelayedFunction(1000*seconds, gMS.purgeExpired)
				DelayedFunction(1000*seconds, trashCleanSetup) #recall Funktion
				DelayedFunction(2000, gMS.purgeExpired)
				emcDebugOut("Next trashcan cleanup in " + str(seconds/60) + " minutes")
	except Exception, e:
		emcDebugOut("[sp] trashCleanSetup exception:\n" + str(e))

def EMCStartup(session):
	if not os.path.exists(config.EMC.folder.value):
		emcTasker.shellExecute("mkdir " + config.EMC.folder.value)
	emcDebugOut("+++ EMC "+EMCVersion+" startup")

	if config.EMC.epglang.value:
		eServiceEvent.setEPGLanguage(config.EMC.epglang.value)
	setupKeyResponseValues()
	DelayedFunction(5000, trashCleanSetup)

	# Go into standby if the reason for restart was EMC auto-restart
	if os.path.exists(config.EMC.folder.value + "/EMC_standby_flag.tmp"):
		emcDebugOut("+++ Going into Standby mode after auto-restart")
		Notifications.AddNotification(Screens.Standby.Standby)
		emcTasker.shellExecute("rm -f " + config.EMC.folder.value + "/EMC_standby_flag.tmp")

class EnhancedMovieCenterMenu(ConfigListScreen, Screen):
	skin = """
		<screen name="EnhancedMovieCenterMenu" position="center,center" size="620,470" title="EnhancedMovieCenterMenu">
		<widget name="config" position="10,10" size="605,400" enableWrapAround="1" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="66,425" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green.png" position="412,425" zPosition="0" size="140,40" transparent="1" alphatest="on" />
		<widget name="key_red" position="66,425" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
		<widget name="key_green" position="412,425" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" shadowColor="#000000" shadowOffset="-1,-1" />
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
		}, -2)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
#		self["key_yellow"] = Button(" ")
#		self["key_blue"] = Button(" ")

		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self.onShown.append(self.onDialogShow)

		self.list.append(getConfigListEntry(_("About"), config.EMC.about, None, self.showInfo))
		self.list.append(getConfigListEntry(_("Start EMC with"), config.EMC.movie_launch, self.launchListSet, None))
		self.list.append(getConfigListEntry(_("Show plugin config in extensions menu"), config.EMC.extmenu_plugin, self.needsRestart, None))
		self.list.append(getConfigListEntry(_("Show EMC in extensions menu"), config.EMC.extmenu_list, self.needsRestart, None))
		self.list.append(getConfigListEntry(_("Disable EMC"), config.EMC.ml_disable, self.needsRestart, None))
		self.list.append(getConfigListEntry(_("Movie home at start"), config.EMC.CoolStartHome, None, None))
		self.list.append(getConfigListEntry(_("Movie home home path"), config.EMC.movie_homepath, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("EMC path access limit"), config.EMC.movie_pathlimit, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("Enable daily trashcan cleanup"), config.EMC.movie_trashcan_clean, trashCleanSetup))
		self.list.append(getConfigListEntry(_("How many days files may remain in trashcan"), config.EMC.movie_trashcan_limit, None, None))
		self.list.append(getConfigListEntry(_("Enable daily movie folder cleanup"), config.EMC.movie_finished_clean, trashCleanSetup))
		self.list.append(getConfigListEntry(_("Days before cleaning finished movies"), config.EMC.movie_finished_limit, None, None))
		self.list.append(getConfigListEntry(_("Daily cleanup time"), config.EMC.movie_trashcan_ctime, trashCleanSetup))
		self.list.append(getConfigListEntry(_("Trashcan path"), config.EMC.movie_trashpath, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("Delete validation"), config.EMC.movie_trashcan_validation, None, None))
		self.list.append(getConfigListEntry(_("Hide trashcan directory"), config.EMC.movie_trashcan_hide, None, None))
		self.list.append(getConfigListEntry(_("Sort file A to Z at startup"), config.EMC.CoolStartAZ, None, None))
		self.list.append(getConfigListEntry(_("File order reverse"), config.EMC.moviecenter_reversed, None, None))

		self.list.append(getConfigListEntry(_("EMC open with cursor on newest (TV mode)"), config.EMC.moviecenter_gotonewest, None, None))
		self.list.append(getConfigListEntry(_("EMC open with cursor on newest (player)"), config.EMC.moviecenter_gotonewestp, None, None))
		self.list.append(getConfigListEntry(_("Cursor predictive move after selection"), config.EMC.moviecenter_selmove, None, None))
		self.list.append(getConfigListEntry(_("Listbox is skin able"), config.EMC.skin_able, None, None))
		self.list.append(getConfigListEntry(_("Show movie icons"), config.EMC.movie_icons, None, None))
		self.list.append(getConfigListEntry(_("Show movie progress"), config.EMC.movie_progress, None, None))
		self.list.append(getConfigListEntry(_("Short watching percent"), config.EMC.movie_watching_percent, None, None))
		self.list.append(getConfigListEntry(_("Finished watching percent"), config.EMC.movie_finished_percent, None, None))
		self.list.append(getConfigListEntry(_("Show date"), config.EMC.movie_date, None, None))
		self.list.append(getConfigListEntry(_("Show icon indication for non-watched"), config.EMC.movie_mark, None, None))
		self.list.append(getConfigListEntry(_("No resume below 10 seconds"), config.EMC.movie_ignore_firstcuts, None, None))
		self.list.append(getConfigListEntry(_("Rewind finished movies before playing"), config.EMC.movie_rewind_finished, None, None))
		self.list.append(getConfigListEntry(_("Always save last played progress as marker"), config.EMC.movie_save_lastplayed, None, None))
		self.list.append(getConfigListEntry(_("Try to load titles from .meta files"), config.EMC.movie_metaload, None, None))
		self.list.append(getConfigListEntry(_("EMC always reload after open"), config.EMC.movie_reload, None, None))
		self.list.append(getConfigListEntry(_("Leave Movie with Exit"), config.EMC.movie_exit, None, None))
		self.list.append(getConfigListEntry(_("EMC re-open list after STOP-press"), config.EMC.movie_reopen, None, None))
		self.list.append(getConfigListEntry(_("EMC re-open list after Movie end"), config.EMC.movie_reopenEOF, None, None))
		self.list.append(getConfigListEntry(_("Display directory reading text"), config.EMC.moviecenter_loadtext, None, None))

		self.list.append(getConfigListEntry(_("Blue button function"), config.EMC.movie_bluefunc, None, None))
		self.list.append(getConfigListEntry(_("Show Movie Format"), config.EMC.CoolFormat, None, None))
		self.list.append(getConfigListEntry(_("Show Cut-Nr if exist"), config.EMC.CoolMovieNr, None, None))
		self.list.append(getConfigListEntry(_("Hide movies being moved"), config.EMC.movie_hide_mov, None, None))
		self.list.append(getConfigListEntry(_("Hide movies being deleted"), config.EMC.movie_hide_del, None, None))
		self.list.append(getConfigListEntry(_("Hide VLC directory"), config.EMC.movie_vlc_hide, None, None))
		self.list.append(getConfigListEntry(_("Automatic timers list cleaning"), config.EMC.timer_autocln, None, None))
		self.list.append(getConfigListEntry(_("Enigma daily auto-restart"), config.EMC.enigmarestart, self.autoRestartInfo, self.autoRestartInfo))
		self.list.append(getConfigListEntry(_("Enigma auto-restart window begin"), config.EMC.enigmarestart_begin, self.autoRestartInfo, self.autoRestartInfo))
		self.list.append(getConfigListEntry(_("Enigma auto-restart window end"), config.EMC.enigmarestart_end, self.autoRestartInfo, self.autoRestartInfo))
		self.list.append(getConfigListEntry(_("Force standby after auto-restart"), config.EMC.enigmarestart_stby, None, None))
		self.list.append(getConfigListEntry(_("Preferred EPG language"), config.EMC.epglang, setEPGLanguage, None))
		self.list.append(getConfigListEntry(_("Primary playback subtitle language"), config.EMC.sublang1, None, None))
		self.list.append(getConfigListEntry(_("Secondary playback subtitle language"), config.EMC.sublang2, None, None))
		self.list.append(getConfigListEntry(_("Tertiary playback subtitle language"), config.EMC.sublang3, None, None))
		self.list.append(getConfigListEntry(_("Enable playback auto-subtitling"), config.EMC.autosubs, None, None))

		self.list.append(getConfigListEntry(_("Primary playback audio language"), config.EMC.audlang1, None, None))
		self.list.append(getConfigListEntry(_("Secondary playback audio language"), config.EMC.audlang2, None, None))
		self.list.append(getConfigListEntry(_("Tertiary playback audio language"), config.EMC.audlang3, None, None))
		self.list.append(getConfigListEntry(_("Enable playback auto-language selection"), config.EMC.autoaudio, None, None))
		self.list.append(getConfigListEntry(_("EMC output directory"), config.EMC.folder, self.validatePath, self.openLocationBox))
		self.list.append(getConfigListEntry(_("Enable EMC debug output"), config.EMC.debug, self.dbgChange, None))
		self.list.append(getConfigListEntry(_("Debug output file name"), config.EMC.debugfile, None, None))
		self.list.append(getConfigListEntry(_("Description field update delay"), config.EMC.movie_descdelay, None, None))
		self.list.append(getConfigListEntry(_("Key period value (50-900)"), config.EMC.key_period, setupKeyResponseValues, None))
		self.list.append(getConfigListEntry(_("Key repeat value (250-900)"), config.EMC.key_repeat, setupKeyResponseValues, None))
		try:
			self.list.append(getConfigListEntry(_("Enable component video in A/V Settings"), config.av.yuvenabled, self.needsRestart, None))
		except: pass

		self.needsRestartFlag = False

	def autoRestartInfo(self, dummy=None):
		emcTasker.ShowAutoRestartInfo()

	def bouquetPlus(self):
		#self["config"].setCurrentIndex( max(self["config"].getCurrentIndex()-16, 0) )
		self["config"].instance.moveSelection(self["config"].instance.pageUp)

	def bouquetMinus(self):
		#self["config"].setCurrentIndex( min(self["config"].getCurrentIndex()+16, len(self.list)-1) )
		self["config"].instance.moveSelection(self["config"].instance.pageDown)

	def dbgChange(self, value):
		if value == True:
			pass
		else:
			emcTasker.shellExecute("rm -f " + config.EMC.folder.value + config.EMC.debugfile.value)

	def dirSelected(self, res):
		if res is not None:
			if res[-1:] == "/":
				res = res[:-1]
			self.list[self["config"].getCurrentIndex()][1].value = res

	def keyOK(self):
		try:
			self.list[self["config"].getCurrentIndex()][3]()
		except:
			pass

	def keyCancel(self):
		for entry in self.list:
			if entry[1].isChanged():
				entry[1].cancel()
		self.close()

	def keySaveNew(self):
		config.EMC.needsreload.value = True
		for entry in self.list:
			if entry[1].isChanged():
				entry[1].save()
				if entry[2] is not None:
					entry[2](entry[1].value)	# execute value changed -function
		if self.needsRestartFlag:
			self.session.open(MessageBox, _("Some settings changes require GUI restart to take effect."), MessageBox.TYPE_INFO, 10)
		self.keySave()
		self.close()

	def launchListSet(self, value):
		if value is not None:
			self.needsRestart()

	def needsRestart(self, dummy=None):
		self.needsRestartFlag = True

	def openLocationBox(self):
		try:
			path = self.list[ self["config"].getCurrentIndex() ][1].value + "/"
			from Screens.LocationBox import LocationBox
			self.session.openWithCallback(self.dirSelected, LocationBox, text = _("Choose directory"), filename = "", currDir = path, minFree = 100)
		except:
			pass

	def showRestart(self):
		emcTasker.ShowAutoRestartInfo()

	def showInfo(self):
		self.session.open(MessageBox, EMCAbout, MessageBox.TYPE_INFO)

	def validatePath(self, value):
		if not os.path.exists(str(value)):
			self.session.open(MessageBox, _("Given path %s does not exist. Please change." % str(value)), MessageBox.TYPE_ERROR)

	def onDialogShow(self):
		self.setTitle("Enhanced Movie Center "+ EMCVersion+ " (Setup)")
	

