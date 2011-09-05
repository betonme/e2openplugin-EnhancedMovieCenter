#!/usr/bin/python
# encoding: utf-8
#
# DirectoryStack
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

from collections import deque

from EMCTasker import emcDebugOut


# DirectoryStack class
class DirectoryStack():
	
	def __init__(self):
		self.stackForward = deque()
		self.stackBackward = deque( maxlen = 10 )

	def isStackForwardAvailable(self):
		return len(self.stackForward) > 0

	def isStackBackwardAvailable(self):
		return len(self.stackBackward) > 0

	def setStackNextDirectory(self, curdir, curservice):
		# Clear forward stack
		self.stackForward.clear()
		if curdir and curservice:
			# Set backward
			self.stackBackward.append( (curdir, curservice) )

	def popStackForward(self, curdir, curservice):
		if self.stackForward:
			# Go forwards
			if curdir and curservice:
				# Set backward
				self.stackBackward.append( (curdir, curservice) )
			return self.stackForward.pop()
		else:
			# Forward isn't possible
			return (None, None)

	def popStackBackward(self, curdir, curservice):
		if self.stackBackward:
			# Go backwards
			if curdir and curservice:
				# Set forward stack
				self.stackForward.append( (curdir, curservice) )
			return self.stackBackward.pop()
		else:
			# Backward isn't possible
			return (None, None)
