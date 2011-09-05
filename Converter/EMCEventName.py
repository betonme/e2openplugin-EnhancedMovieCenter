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
				#TODO con print "EMC en shortdesc1 " + str(shortdesc)
				if not shortdesc:
					if service:
						path = service.getPath()
						self.eit = EitList(path)
						shortdesc = self.eit and self.eit.getEitDescription()
						#TODO con print "EMC en shortdesc2 " + str(shortdesc)
						if not shortdesc:
							self.meta = MetaList(path)
							shortdesc = self.meta and self.meta.getMetaDescription()
							#TODO con print "EMC en shortdesc3 " + str(shortdesc)
						if not shortdesc:
							#1
							#	rec_ref_str = info and info.getInfoString(service, iServiceInformation.sServiceref)
							#	shortdesc = rec_ref_str and ServiceReference(rec_ref_str).getServiceName()
							#2
							# filename = os.path.basename(service.getPath())
							# shortdesc = getFileTitle(filename, service)[0]
							#3
							shortdesc = service.getName()
							#TODO con print "EMC en shortdesc4 " + str(shortdesc)
							#Fallback basename path
				return shortdesc or ""
			
			elif self.type == self.EXTENDED_DESCRIPTION:
				extdesc = event and event.getExtendedDescription()
				#TODO con print "EMC en extdesc1 " + str(extdesc)
				if not extdesc:
					if service:
						path = service.getPath()
						self.eit = EitList(path)
						extdesc = self.eit and self.eit.getEitDescription()
						#TODO con print "EMC en extdesc3 " + str(extdesc)
						if not extdesc:
							self.meta = MetaList(path)
							extdesc = self.meta and self.meta.getMetaDescription()
							#TODO con print "EMC en extdesc2 " + str(extdesc)
							if not extdesc:
								if not os.path.isfile(path):
									# Resolve symbolic link
									extdesc = os.path.realpath(path)
									#TODO con print "EMC en extdesc4 " + str(extdesc)
#								elif path == "..":
#									# Resolve symbolic link of dirname
#									#TODO where to get the directory
#									extdesc = os.path.realpath( os.path.dirname(path) )
#									#TODO con print "EMC en extdesc3a " + str(extdesc)
#								elif os.path.isdir(path):
#									# Resolve symbolic link
#									extdesc = os.path.realpath(path)
#									#TODO con print "EMC en extdesc4 " + str(extdesc)
				return extdesc or ""
			
			elif self.type == self.ID:
				id = str(event and event.getEventId())
				return id or ""
				
		except Exception, e:
			print "[EMCEN] getText exception:" + str(e)

	text = property(getText)
