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

from datetime import datetime

from EMCTasker import emcDebugOut
from IsoFileSupport import IsoSupport


# Meta File support class
# Description
# http://git.opendreambox.org/?p=enigma2.git;a=blob;f=doc/FILEFORMAT
class MetaList():

	SERVICE = 0
	NAME = 1
	DESC = 2
	RECTIME = 3
	TAGS = 4
	LENGTH = 5
	FILESIZE = 6
	
	def __init__(self, path=None):
		self.meta_file = None
		self.meta_mtime = 0
		self.meta = ["","","","","","",""]
		self.iso = None

		self.__newPath(path)
		self.__readMetaFile()

	def __newPath(self, path):
		name = None
		if path:
			#TODO Too slow
			#if path.endswith(".iso"):
			#	if not self.iso:
			#		self.iso = IsoSupport(path)
			#	name = self.iso and self.iso.getIsoName()
			#	if name and len(name):
			#		path = "/home/root/dvd-" + name
			#el
			if os.path.isdir(path):
				path += "/dvd"
			if not os.path.exists(path + ".meta"):
				path, ext = os.path.splitext(path)
				# Strip existing cut number
				if path[-4:-3] == "_" and path[-3:].isdigit():
					path = path[:-4] + ext
			path += ".meta"
			if self.meta_file != path:
				self.meta_file = path
				self.meta_mtime = 0
	
	def __ptsToSeconds(self, pts):
		# Meta files are using the presentation time stamp time format
		# pts has a resolution of 90kHz
		return pts / 90 / 1000

	def __mk_int(self, s):
		return int(s) if s else 0

	def __secondsToDate(self, s):
		return s and datetime.fromtimestamp(s) or None

	##############################################################################
	## Get Functions
	def getMetaList(self):
		return self.meta
		
	def getMetaMTime(self):
		return self.meta_mtime
		
	def getMetaServiceReference(self):
		return self.meta[self.SERVICE]

	def getMetaName(self):
		return self.meta[self.NAME]

	def getMetaDescription(self):
		#TODO transform during read on init
		try:
			self.meta[self.DESC].decode('utf-8')
		except UnicodeDecodeError:
			try:
				self.meta[self.DESC] = self.meta[self.DESC].decode("cp1252").encode("utf-8")
			except UnicodeDecodeError:
				self.meta[self.DESC] = self.meta[self.DESC].decode("iso-8859-1").encode("utf-8")
		return self.meta[self.DESC]

	def getMetaRecordingTime(self):
		# Time in seconds since 1970
		return self.__mk_int( self.meta[self.RECTIME] )
	
	def getMetaTags(self):
		return self.meta[self.TAGS]

	def	getMetaLength(self):
		#TODO calculate during read on init
		return self.__ptsToSeconds( self.__mk_int( self.meta[self.LENGTH] ) )
		
	def	getMetaFileSize(self):
		return self.__mk_int( self.meta[self.FILESIZE] )

	# Wrapper
	def getMetaDate(self):
		#TODO transform during read on init
		return self.__secondsToDate( self.getMetaRecordingTime() )

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
				#print "EMC TEST count Meta " + str(path)
				
				# New path or file has changed
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
					# Strip lines and extract information
					lines = [l.strip() for l in lines]
					le = len(lines)
					self.meta = ["","","","","","",""]
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

