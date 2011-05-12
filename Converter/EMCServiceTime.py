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
				self.cuts = CutList(service, borg=True)
				begin = self.cuts and self.cuts.getCutListMTime()
		return begin or 0

	def getLength(self, info, service):
		len = info and service and info.getLength(service)
		if not len or len < 0:
			if service:
				info = self.serviceHandler.info(service)
				len = info and info.getLength(service)
			if len <= 0:
				if service and not isinstance(service, eServiceReference):
					if NavigationInstance and NavigationInstance.instance:
						service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if service:
					self.meta = MetaList(service, borg=True)
					len = self.meta and self.meta.getMetaLength()
					if len <= 0:
						self.cuts = CutList(service, borg=True)
						len = self.cuts and self.cuts.getCutListLength()
		return len or 0

	@cached
	def getTime(self):
		try:
			service = self.source.service
			info = self.source.info
					
			if self.type == self.STARTTIME:
				return self.getStart(info, service)
				
			elif self.type == self.ENDTIME:
				begin = self.getStart(info, service)
				len = self.getLength(info, service)
				return begin + len
				
			elif self.type == self.DURATION:
				return self.getLength(info, service)
		
		except Exception, e:
			print "[EMCST] getTime exception:" + str(e)

	time = property(getTime)
