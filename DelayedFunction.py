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

from enigma import eTimer
from EMCTasker import emcDebugOut

instanceTab = []	# just seems to be required to keep the instances alive long enough

class DelayedFunction:
	def __init__(self, delay, function, *params):
		try:
			global instanceTab
			instanceTab.append(self)
			self.function = function
			self.params = params
			self.timer = None
			self.timer = eTimer()
			self.timer.timeout.get().append(self.timerLaunch)
			self.timer.start(delay, False)
		except Exception, e:
			emcDebugOut("[spDF] __init__ exception:\n%s:%s" %(str(self.function),str(e)))

	def cancel(self):
		try:
			global instanceTab
			instanceTab.remove(self)
			self.timer.stop()
			self.timer.timeout.get().remove(self.timerLaunch)
			self.timer = None
		except Exception, e:
			emcDebugOut("[spDF] timer cancel exception:\n%s:%s" %(str(self.function),str(e)))

	def timerLaunch(self):
		try:
			global instanceTab
			instanceTab.remove(self)
			self.timer.stop()
			self.timer.timeout.get().remove(self.timerLaunch)
			self.timer = None
			self.function(*self.params)
		except Exception, e:
			emcDebugOut("[spDF] timerLaunch exception:\n%s:%s" %(str(self.function),str(e)))
