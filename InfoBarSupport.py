#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 by betonme
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

import os

from Components.config import *
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from enigma import eTimer, iPlayableService, iServiceInformation, eServiceReference, iServiceKeys, getDesktop
from Screens.Screen import Screen
from Screens.InfoBarGenerics import *
from Screens.InfoBar import InfoBar
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS

from EnhancedMovieCenter import _
from EMCTasker import emcDebugOut
from DelayedFunction import DelayedFunction

SeekbarPlg = "%s%s"%(resolveFilename(SCOPE_PLUGINS), "Extensions/Seekbar/plugin.py")


# Overwrite Seekbar
def EMCkeyOK(self):
	sel = self["config"].getCurrent()[1]
	if sel == self.positionEntry:
		if self.length:
			# seekTo() doesn't work for DVD Player
			oldPosition = self.seek.getPlayPosition()[1]
			newPosition = int(float(self.length[1]) / 100.0 * self.percent)
			if newPosition > oldPosition:
				pts = newPosition - oldPosition
			else:
				pts = -1*(oldPosition - newPosition)
			from EMCMediaCenter import EMCMediaCenter
			EMCMediaCenter.doSeekRelative(self.infobarInstance, pts)
			self.exit()
	elif sel == self.minuteInput:
		pts = self.minuteInput.value * 60 * 90000
		if self.fwd == False:
			pts = -1*pts
		from EMCMediaCenter import EMCMediaCenter
		EMCMediaCenter.doSeekRelative(self.infobarInstance, pts)
		self.exit()


class InfoBarSupport(	InfoBarBase, \
											InfoBarNotifications, \
											InfoBarSeek, \
											InfoBarShowHide, \
											InfoBarMenu, \
											InfoBarShowMovies, \
											InfoBarAudioSelection, \
											InfoBarSimpleEventView, \
											InfoBarServiceNotifications, \
											InfoBarPVRState, \
											InfoBarCueSheetSupport, \
											InfoBarMoviePlayerSummarySupport, \
											InfoBarSubtitleSupport, \
											InfoBarTeletextPlugin, \
											InfoBarServiceErrorPopupSupport, \
											InfoBarExtensions, \
											InfoBarPlugins, \
											InfoBarNumberZap ):
											#InfoBarPiP

	def __init__(self):

		for x in	InfoBarBase, \
							InfoBarNotifications, \
							InfoBarSeek, \
							InfoBarShowHide, \
							InfoBarMenu, \
							InfoBarShowMovies, \
							InfoBarAudioSelection, \
							InfoBarSimpleEventView, \
							InfoBarServiceNotifications, \
							InfoBarPVRState, \
							InfoBarMoviePlayerSummarySupport, \
							InfoBarSubtitleSupport, \
							InfoBarTeletextPlugin, \
							InfoBarServiceErrorPopupSupport, \
							InfoBarExtensions, \
							InfoBarPlugins, \
							InfoBarNumberZap:
							#InfoBarCueSheetSupport
			x.__init__(self)
			
		# Initialize InfoBarCueSheetSupport because we cannot override __serviceStarted
		#def __init__(self, actionmap = "InfobarCueSheetActions"):
		actionmap = "InfobarCueSheetActions"
		self["CueSheetActions"] = HelpableActionMap(self, actionmap,
			{
				"jumpPreviousMark": (self.jumpPreviousMark, _("jump to previous marked position")),
				"jumpNextMark": (self.jumpNextMark, _("jump to next marked position")),
				"toggleMark": (self.toggleMark, _("toggle a cut mark at the current position"))
			}, prio=1)
		self.cut_list = [ ]
		self.is_closing = False
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.__serviceStarted,
			})

	##############################################################################
	## Override from InfoBarGenerics.py
	
	# InfoBarCueSheetSupport
	def __serviceStarted(self):
		if self.is_closing:
			return
		print "new service started! trying to download cuts!"
		self.downloadCuesheet()
		
		# From Merlin2 InfoBarCueSheetSupport __serviceStarted
		if config.usage.on_movie_start.value == "beginning" and config.EMC.movie_jump_first_mark.value == True:
			self.jumpToFirstMark()
			return
		
		if self.ENABLE_RESUME_SUPPORT:
			last = None
			
			for (pts, what) in self.cut_list:
				if what == self.CUT_TYPE_LAST:
					last = pts
					
			if last is not None:
				self.resume_point = last
				l = last / 90000
				if config.usage.on_movie_start.value == "ask":
					Notifications.AddNotificationWithCallback(self.playLastCB, MessageBox, _("Do you want to resume this playback?") + "\n" + (_("Resume position at %s") % ("%d:%02d:%02d" % (l/3600, l%3600/60, l%60))), timeout=10)
				elif config.usage.on_movie_start.value == "resume":
					Notifications.AddNotificationWithCallback(self.playLastCB, MessageBox, _("Resuming playback"), timeout=2, type=MessageBox.TYPE_INFO)
			elif config.EMC.movie_jump_first_mark.value == True:
				self.jumpToFirstMark()
		elif config.EMC.movie_jump_first_mark.value == True:
			self.jumpToFirstMark()

	# From Merlin2
	def jumpToFirstMark(self):
		firstMark = None
		current_pos = self.cueGetCurrentPosition() or 0
		#increase current_pos by 2 seconds to make sure we get the correct mark
		current_pos = current_pos+180000
		# EMC enhancement: increase recording margin to make sure we get the correct mark
		margin = config.recording.margin_before.value*60*90000 *2 or 20*60*90000
		middle = self.getSeekLength() or 90*60*90000
		middle /=2 
		
		for (pts, what) in self.cut_list:
			if what == self.CUT_TYPE_MARK:
				if pts != None and ( current_pos < pts and pts < margin and pts < middle ):
					if firstMark == None or pts < firstMark: 
						firstMark = pts
		if firstMark is not None:
			self.start_point = firstMark
			self.doSeek(self.start_point)

	def jumpNextMark(self):
		if not self.jumpPreviousNextMark(lambda x: x-90000):
			# There is no further mark
			self.doSeekEOF()
		else:
			if config.usage.show_infobar_on_skip.value:
				# InfoBarSeek
				self.showAfterSeek()

	# InfoBarSeek
	# Seekbar workaround
	def seekFwdManual(self):
		if fileExists(SeekbarPlg) or fileExists("%sc"%SeekbarPlg):
			from Plugins.Extensions.Seekbar.plugin import Seekbar, seekbar
			Seekbar.keyOK = EMCkeyOK
			seekbar(self)
			Seekbar.keyOK = Seekbar.keyOK
		else:
			# InfoBarSeek
			InfoBarSeek.seekFwdManual(self)

	# Seekbar workaround
	def seekBackManual(self):
		if fileExists(SeekbarPlg) or fileExists("%sc"%SeekbarPlg):
			from Plugins.Extensions.Seekbar.plugin import Seekbar, seekbarBack
			Seekbar.keyOK = EMCkeyOK
			seekbarBack(self)
			Seekbar.keyOK = Seekbar.keyOK
		else:
			# InfoBarSeek
			InfoBarSeek.seekBackManual(self)

	def doSeekRelative(self, pts):
		if self.getSeekLength() < self.getSeekPlayPosition() + pts:
			# Relative jump is behind the movie length
			self.doSeekEOF()
		else:
			# Call baseclass function
			InfoBarSeek.doSeekRelative(self, pts)

	def doSeek(self, pts):
		len = self.getSeekLength()
		if len and len < pts:
			# PTS is behind the movie length
			self.doSeekEOF()
		else:
			# Call baseclass function
			InfoBarSeek.doSeek(self, pts)
			if pts and config.usage.show_infobar_on_skip.value:
				# InfoBarSeek
				self.showAfterSeek()

	def getSeekPlayPosition(self):
		try:
			# InfoBarCueSheetSupport
			return self.cueGetCurrentPosition() or 0
		except Exception, e:
			emcDebugOut("[EMCMC] getSeekPlayPosition exception:" + str(e))
			return 0

	def getSeekLength(self):
		try:
			# Call private InfoBarCueSheetSupport function
			seek = InfoBarCueSheetSupport._InfoBarCueSheetSupport__getSeekable(self)
		except Exception, e:
			emcDebugOut("[EMCMC] getSeekLength exception:" + str(e))
		if seek is None:
			return None
		len = seek.getLength()
		return long(len[1])

	# Handle EOF
	def doSeekEOF(self):
		try:
			# Stop one second before eof : 1 * 90 * 1000
			play = self.getSeekPlayPosition()
			end = self.getSeekLength() - 90000
			if play < end and 0 < end:
				# InfoBarSeek
				InfoBarSeek.doSeek(self, end)
			# Wait one second before signaling eof
			# Call private InfoBarSeek function
			DelayedFunction(1000, InfoBarSeek._InfoBarSeek__evEOF, self)
		except Exception, e:
			emcDebugOut("[EMCMC] doSeekEOF exception:" + str(e))
	
