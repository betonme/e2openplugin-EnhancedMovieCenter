#!/usr/bin/python
# encoding: utf-8
#
# EMCEventName
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
from Components.Converter.EventName import EventName
from Components.Element import cached, ElementError
from enigma import iServiceInformation, eServiceReference

from Plugins.Extensions.EnhancedMovieCenter.MetaSupport import MetaList
from Plugins.Extensions.EnhancedMovieCenter.EitSupport import EitList


class EMCEventName(EventName):
	def __init__(self, type):
		EventName.__init__(self, type)
		self.meta = None
		self.eit = None

	@cached
	def getText(self):
		try:
			service = self.source.service
			event = self.source.event
			
			if service and not isinstance(service, eServiceReference):
				if NavigationInstance and NavigationInstance.instance:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					
			if self.type == self.NAME:
				name = event and event.getEventName()
				return name or ""
			
			elif self.type == self.SHORT_DESCRIPTION:
				shortdesc = event and event.getShortDescription()
				if not shortdesc:
					#print "EMC shortdesc Eit"
					self.eit = EitList(service)
					shortdesc = self.eit and self.eit.getEitDescription()
				if not shortdesc:
					#print "EMC shortdesc Meta"
					self.meta = MetaList(service, borg=True)
					shortdesc = self.meta and self.meta.getMetaDescription()
				return shortdesc or ""
			
			elif self.type == self.EXTENDED_DESCRIPTION:
				extdesc = event and event.getExtendedDescription()
				if not extdesc:
					#print "EMC EIT extdesc Meta"
					self.meta = MetaList(service, borg=True)
					extdesc = self.meta and self.meta.getMetaDescription()
				if not extdesc:
					#print "EMC EIT extdesc Eit"
					self.eit = EitList(service)
					extdesc = self.eit and self.eit.getEitDescription()
				return extdesc or ""
			
			elif self.type == self.ID:
				id = str(event and event.getEventId())
				return id or ""
				
		except Exception, e:
			print "[EMCEN] getText exception:" + str(e)

	text = property(getText)
