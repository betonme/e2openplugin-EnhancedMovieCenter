#!/usr/bin/python
# encoding: utf-8
#
# MetaSupport
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

from enigma import eServiceReference

from EMCTasker import emcDebugOut
from IsoFileSupport import IsoSupport


# Meta File support class
# Description
# http://git.opendreambox.org/?p=enigma2.git;a=blob;f=doc/FILEFORMAT
class MetaList():
	#__shared_state = {}
	SERVICE = 0
	NAME = 1
	DESC = 2
	RECTIME = 3
	TAGS = 4
	LENGTH = 5
	FILESIZE = 6
	
	def __init__(self, service=None, borg=False):
		#if borg:
		#	self.__dict__ = self.__shared_state
		if not '_ready' in dir(self):
			# Very first one time initialization
			self._ready = True
			self.meta_file = None
			self.meta_mtime = 0
			self.meta = ["","","","","","",""]
			self.iso = None

		self.__newService(service)
		self.__readMetaFile()

	def __newService(self, service):
		path = None
		name = None
		if service and isinstance(service, eServiceReference):
			path = service.getPath()
			#if path.endswith(".iso"):
			#	if not self.iso:
			#		self.iso = IsoSupport(service, borg=True)
			#	name = self.iso and self.iso.getIsoName()
			#	if name and len(name):
			#		path = "/home/root/dvd-" + name
			#el
			if os.path.isdir(path):
				path += "/dvd"
			path += ".meta"
			if self.meta_file != path:
				self.meta_file = path
				self.meta_mtime = 0
		else:
			# No service or no eServiceReference
			self.meta_file = None
			self.meta_mtime = 0
			self.meta = [""]*len(METAID)
			self.iso = None

	def __ptsToSeconds(self, pts):
		# Meta files are using the presentation time stamp time format
		# pts has a resolution of 90kHz
		return pts / 90 / 1000

	def __mk_int(self, s):
		return int(s) if s else 0

	##############################################################################
	## Get Functions
	def getMetaList(self):
		return self.meta
		
	def getMetaMTime(self):
		return self.meta_mtime
		
	def	getMetaServiceReference(self):
		return self.meta[self.SERVICE]

	def	getMetaName(self):
		return self.meta[self.NAME]

	def	getMetaDescription(self):
		return self.meta[self.DESC]

	def	getMetaRecordingTime(self):
		return self.meta[self.RECTIME]

	def	getMetaTags(self):
		return self.meta[self.TAGS]

	def	getMetaLength(self):
		return self.__ptsToSeconds( self.__getMetaLength() )
		
	def	getMetaFileSize(self):
		return self.__mk_int( self.meta[self.FILESIZE] )

	# Intenal from metalist in pts
	def	__getMetaLength(self):
		return self.__mk_int( self.meta[self.LENGTH] )

	##############################################################################
	## File IO Functions
	def __readMetaFile(self):
		lines = []
		path = self.meta_file
		if path and os.path.exists(path):
			mtime = os.path.getmtime(path)
			if self.meta_mtime == mtime:
				# File has not changed
				pass
				
			else:
				# New Service or file has changed
				self.meta_mtime = mtime
				
				# Read data from file
				# OE1.6 with Pyton 2.6
				#with open(self.meta_file, 'r') as file: lines = file.readlines()	
				f = None
				try:
					f = open(path, 'r')
					lines = f.readlines()
				except Exception, e:
					emcDebugOut("[META] Exception in readMetaFile: " + str(e))
				finally:
					if f is not None:
						f.close()
					
				# Parse the lines
				if lines:
					# Strip lines
					#lines = map(lambda l: l.rstrip("\r\n"), lines)
					# Extract information
					#self.meta[0:len(lines)] = lines[0:len(lines)]
					lines = [l.strip() for l in lines]
					le = len(lines)
					self.meta[0:le] = lines[0:le]
				else:
					# No date clear all
					self.meta = ["","","","","","",""]
					
		else:
			# No path or no file clear all
			self.meta = ["","","","","","",""]

#MAYBE
#	def __writeMetaFile(self):
#		# Generate and pack data
#		data = ""
#		if self.meta_file:
#TODO
#			pass
#		# Write data to file
#		if os.path.exists(self.meta_file):
#TODO w or wb
#			with open(self.meta_file, 'wb') as file:
#				file.write(data)
