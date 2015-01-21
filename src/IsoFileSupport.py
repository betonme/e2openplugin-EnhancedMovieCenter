#!/usr/bin/python
# encoding: utf-8
#
# IsoSupport
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

from EMCTasker import emcDebugOut

class IsoSupport():

	def __init__(self, path=None):
		self.iso_file = None
		self.iso_mtime = 0
		self.iso_name = ""

		self.__newPath(path)
		#TODO Temporary deactivated because of massive performance issues
		#self.__readISOFile()

	def __newPath(self, path):
		if path:
			if path.endswith(".iso"):
				if self.iso_file == path:
					# Same file
					pass
				else:
					# New file
					self.iso_file = path
					self.iso_mtime = 0
					self.iso_name = ""
			else:
				# No iso file
				self.iso_file = None
				self.iso_mtime = 0
				self.iso_name = ""

	##############################################################################
	## Get Function
	def getIsoName(self):
		return self.iso_name

	##############################################################################
	## File IO Functions
	def __readISOFile(self):
		try:
			# Attention: Read can be very slow !!!
			name = ""
			path = self.iso_file
			if path and os.path.exists(path) and path.endswith(".iso"):
				mtime = os.path.getmtime(path)
				if self.iso_mtime == mtime:
					# File has not changed
					pass

				else:
					#print "EMC TEST count Eit " + str(path)

					# New path or file has changed
					self.iso_mtime = mtime

					# Read data from file
					f = None
					try:
						f = open(path, 'rb')
						# This is very slow
						# Any ideas do speed up
						f.seek(0x10019)
						name = f.readline()
					except Exception, e:
						emcDebugOut("[ISO] Exception in __readISOFile: " + str(e))
					finally:
						if f is not None:
							f.close()

					# Parse the name
					self.iso_name = name.split('\0')[0]

			else:
				# No path or no file clear all
				self.iso_name = ""

		except Exception, e:
			emcDebugOut("[META] Exception in readMetaFile: " + str(e))