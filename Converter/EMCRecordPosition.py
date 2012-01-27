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

#import os
import NavigationInstance

from Components.config import *

from Components.Converter.Converter import Converter
from Components.Converter.ServicePosition import ServicePosition
from Components.Element import cached
#from enigma import eServiceReference

from time import time


class EMCRecordPosition(ServicePosition):
	def __init__(self, type):
		ServicePosition.__init__(self, type)

	@cached
	def getCutlist(self):
		return []

	cutlist = property(getCutlist)

	@cached
	def getPosition(self):
		print "EMCRecordPosition getPosition"
		if config.EMC.record_eof_zap.value:
			from Plugins.Extensions.EnhancedMovieCenter.MovieSelection import gMS
			service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			path = service and service.getPath()
			print path
			record = path and gMS.getRecording(path)
			if record:
				print record
				begin, end, s = record
				print int((time() - begin) * 90000)
				return int((time() - begin) * 90000)
		return 0

	position = property(getPosition)

	@cached
	def getLength(self):
		print "EMCRecordPosition getLength"
		if config.EMC.record_eof_zap.value:
			from Plugins.Extensions.EnhancedMovieCenter.MovieSelection import gMS
			service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			path = service and service.getPath()
			record = path and gMS.getRecording(path)
			if record:
				begin, end, s = record
				print int((end - begin) * 90000)
				return int((end - begin) * 90000)
		return 0

	length = property(getLength)

	@cached
	def getValue(self):
		return None
	
	value = property(getValue)
