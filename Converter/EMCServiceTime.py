#!/usr/bin/python
# encoding: utf-8
#
# EMCServiceTime
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
from Components.Converter.ServiceTime import ServiceTime
from Components.Element import cached, ElementError
from enigma import iServiceInformation, eServiceCenter, eServiceReference

from Plugins.Extensions.EnhancedMovieCenter.CutListSupport import CutList
from Plugins.Extensions.EnhancedMovieCenter.MetaSupport import MetaList


class EMCServiceTime(ServiceTime):
	def __init__(self, type):
		ServiceTime.__init__(self, type)
		self.serviceHandler = eServiceCenter.getInstance()
		self.meta = None
		self.cuts = None

	def getStart(self, info, service):
		begin = info and service and info.getInfo(service, iServiceInformation.sTimeCreate)
		if not begin:
			if service and not isinstance(service, eServiceReference):
				if NavigationInstance and NavigationInstance.instance:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			if service:
				self.cuts = CutList( service.getPath() )
				begin = self.cuts and self.cuts.getCutListMTime()
		return begin or 0

	def getLength(self, info, service):
		length = info and service and info.getLength(service)
		if not length or length < 0:
			if service:
				info = self.serviceHandler.info(service)
				length = info and info.getLength(service)
		if length <= 0:
			if service and not isinstance(service, eServiceReference):
				if NavigationInstance and NavigationInstance.instance:
					service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			if service:
				path = service.getPath()
				self.meta = MetaList(path)
				length = self.meta and self.meta.getMetaLength()
				if length <= 0:
					self.cuts = CutList(path)
					length = self.cuts and self.cuts.getCutListLength()
		return length or 0

	@cached
	def getTime(self):
		try:
			service = self.source.service
			info = self.source.info
					
			if self.type == self.STARTTIME:
				#TODO con print "EMC STs " +str(self.getStart(info, service))
				return self.getStart(info, service) #or None
				
			elif self.type == self.ENDTIME:
				begin = self.getStart(info, service)
				length = self.getLength(info, service)
				#TODO con print "EMC STe " +str(begin) + " " + str(length)
				return begin + length #or None
				
			elif self.type == self.DURATION:
				#TODO con print "EMC STl " +str(self.getLength(info, service))
				return self.getLength(info, service) #or None
		
		except Exception, e:
			print "[EMCST] getTime exception:" + str(e)

	time = property(getTime)
