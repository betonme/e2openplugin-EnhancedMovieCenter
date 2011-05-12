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
							InfoBarCueSheetSupport, \
							InfoBarMoviePlayerSummarySupport, \
							InfoBarSubtitleSupport, \
							InfoBarTeletextPlugin, \
							InfoBarServiceErrorPopupSupport, \
							InfoBarExtensions, \
							InfoBarPlugins, \
							InfoBarNumberZap:
			x.__init__(self)

	##############################################################################
	## Override from InfoBarGenerics.py
	
	# InfoBarCueSheetSupport
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
			return self.cueGetCurrentPosition()
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
	
