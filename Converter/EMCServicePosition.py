#!/usr/bin/python
# encoding: utf-8
#
# EMCServicePosition
# Copyright (C) 2011 betonme
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
import NavigationInstance

from Components.config import *

from Components.Converter.Converter import Converter
from Components.Converter.ServicePosition import ServicePosition
from Components.Element import cached, ElementError
from Components.Converter.Poll import Poll
from enigma import eServiceReference

from Plugins.Extensions.EnhancedMovieCenter.CutListSupport import CutList


class EMCServicePosition(ServicePosition):
	def __init__(self, type):
		ServicePosition.__init__(self, type)
		self.cuts = None

	@cached
	def getCutlist(self):
		try:
			cutlist = []
			service = self.source.service
			cue = service and service.cueSheet()
		
			if cue:
				# Native cuesheet support
				cutlist = cue.getCutList()
				#print "EMC cue getCutlist"
			else:
				#print "EMC cue getCutlist else"
				# No native cuesheet support
				if service and not isinstance(service, eServiceReference):
					if NavigationInstance and NavigationInstance.instance:
						service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if service:
					self.cuts = CutList(service, borg=True)
					cutlist = self.cuts and self.cuts.getCutList()
			return cutlist or []
			
		except Exception, e:
			print "[EMCSP] getCutlist exception:" + str(e)

	cutlist = property(getCutlist)
