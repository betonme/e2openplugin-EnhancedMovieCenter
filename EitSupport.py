#!/usr/bin/python
# encoding: utf-8
#
# EitSupport
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
import struct
import time

from enigma import eServiceReference

from EMCTasker import emcDebugOut
from IsoFileSupport import IsoSupport

#def crc32(data):
#	poly = 0x4c11db7
#	crc = 0xffffffffL
#	for byte in data:
#		byte = ord(byte)
#		for bit in range(7,-1,-1):  # MSB to LSB
#			z32 = crc>>31    # top bit
#			crc = crc << 1
#			if ((byte>>bit)&1) ^ z32:
#				crc = crc ^ poly
#			crc = crc & 0xffffffffL
#	return crc

def parseMJD(MJD):
	# Parse 16 bit unsigned int containing Modified Julian Date, 
	# as per DVB-SI spec
	# returning year,month,day
	YY = int( (MJD - 15078.2) / 365.25 )
	MM = int( (MJD - 14956.1 - int(YY*365.25) ) / 30.6001 )
	D  = MJD - 14956 - int(YY*365.25) - int(MM * 30.6001)
	K=0
	if MM == 14 or MM == 15: K=1
	
	return (1900 + YY+K), (MM-1-K*12), D

def unBCD(byte):
	return (byte>>4)*10 + (byte & 0xf)


# Eit File support class
# Description
# http://de.wikipedia.org/wiki/Event_Information_Table
class EitList():
	
	EIT_SHORT_EVENT_DESCRIPTOR 		= 0x4d
	EIT_EXTENDED_EVENT_DESCRIPOR 	=	0x4e
	
	def __init__(self, service=None):
		#self.serviceReference = service
		#if service:
			#self.eit_file = service.getPath() + ".eit"
			#self.readEitFile()
		#if borg:
		#	self.__dict__ = self.__shared_state
		if not '_ready' in dir(self):
			# Very first one time initialization
			self._ready = True
			self.eit_file = None
			self.eit_mtime = 0
			#self.eit = [""]*len(METAID)
			self.eit = {}
			self.iso = None

		self.__newService(service)
		self.__readEitFile()

	def __newService(self, service):
		path = None
		name = None
		if service and isinstance(service, eServiceReference):
			path = service.getPath()
			if path.endswith(".iso"):
				if not self.iso:
					self.iso = IsoSupport(service, borg=True)
				name = self.iso and self.iso.getIsoName()
				if name and len(name):
					path = "/home/root/dvd-" + name
			elif os.path.isdir(path):
				path += "/dvd"
			else:
				path = os.path.splitext(path)[0]
			path += ".eit"
			if self.eit_file != path:
				self.eit_file = path
				self.eit_mtime = 0
		else:
			# No service or no eServiceReference
			self.eit_file = None
			self.eit_mtime = 0
			#self.eit = [""]*len(METAID)
			self.iso = None

	##############################################################################
	## Get Functions
	def getEitServiceId(self):
		return self.eit.get('service', "")

	def getEitTsId(self):
		return self.eit.get('transportstream', "")

	def getEitWhen(self):
		return self.eit.get('when', "")

	def getEitStartDate(self):
		return self.eit.get('startdate', "")

	def getEitStartTime(self):
		return self.eit.get('starttime', "")

	def getEitDuration(self):
		return self.eit.get('duration', "")

	def getEitName(self):
		return self.eit.get('name', "")

	def getEitDescription(self):
		return self.eit.get('description', "")

	# Wrapper
	def getEitShortDescription(self):
		return self.getEitName()

	def getEitExtendedDescription(self):
		return self.getEitDescription()

	##############################################################################
	## File IO Functions
	def __readEitFile(self):
		try:
			data = ""
			path = self.eit_file
			if path and os.path.exists(path):
				mtime = os.path.getmtime(path)
				if self.eit_mtime == mtime:
					# File has not changed
					pass
					
				else:
					# New Service or file has changed
					self.eit_mtime = mtime
					
					# Read data from file
					# OE1.6 with Pyton 2.6
					#with open(self.eit_file, 'r') as file: lines = file.readlines()	
					f = None
					try:
						f = open(path, 'rb')
						#lines = f.readlines()
						data = f.read()
					except Exception, e:
						emcDebugOut("[META] Exception in readEitFile: " + str(e))
					finally:
						if f is not None:
							f.close()
						
					# Parse the data
					if data and 12 <= len(data):
						# go through events
						pos = 0
						e = struct.unpack(">HHBBBBBBH", data[pos:pos+12])
						event_id = e[0]
						date     = parseMJD(e[1])                         # Y, M, D
						time     = unBCD(e[2]), unBCD(e[3]), unBCD(e[4])  # HH, MM, SS
						duration = unBCD(e[5]), unBCD(e[6]), unBCD(e[7])  # HH, MM, SS
						running_status  = (e[8] & 0xe000) >> 13
						free_CA_mode    = e[8] & 0x1000
						descriptors_len = e[8] & 0x0fff
						
						if running_status in [1,2]:
							self.eit['when'] = "NEXT"
						elif running_status in [3,4]:
							self.eit['when'] = "NOW"
						
						self.eit['startdate'] = date
						self.eit['starttime'] = time
						self.eit['duration'] = duration
						
						pos = pos + 12
						short_event_descriptor = []
						extended_event_descriptor = []
						component_descriptor = []
						content_descriptor = []
						linkage_descriptor = []
						parental_rating_descriptor = []
						while pos < len(data):
							rec = ord(data[pos])
							length = ord(data[pos+1]) + 2
							if rec == 0x4D:
								#descriptor_tag = ord(data[pos+1])
								#descriptor_length = ord(data[pos+2])
								#ISO_639_language_code = str(data[pos+3:pos+3])
								event_name_length = ord(data[pos+5])
								short_event_descriptor.append(data[pos+6:pos+6+event_name_length]) 
								short_event_descriptor.append("\n\n")
								text_length = pos+6+event_name_length
								short_event_descriptor.append(data[pos+7+event_name_length:pos+8+text_length])
							elif rec == 0x4E:
								extended_event_descriptor.append(data[pos+8:pos+length]) 
							elif rec == 0x50:
								component_descriptor.append(data[pos+8:pos+length])
							elif rec == 0x54:
								content_descriptor.append(data[pos+8:pos+length])
							elif rec == 0x4A:
								linkage_descriptor.append(data[pos+8:pos+length])
							elif rec == 0x55:
								parental_rating_descriptor.append(data[pos+2:pos+length])
							else:
								#print "unsopported descriptor: %x %x" %(rec, pos + 12)
								#print data[pos:pos+length]
								pass 
							pos += length
							
						self.eit['name'] = "".join(short_event_descriptor).decode("cp1252").encode("utf-8")
						self.eit['description'] = "".join(extended_event_descriptor).decode("cp1252").encode("utf-8")
						
					else:
						# No date clear all
						self.eit = {}
					
			else:
				# No path or no file clear all
				self.eit = {}
				
		except Exception, e:
			emcDebugOut("[META] Exception in readEitFile: " + str(e))


#	def __writeEitFile(self):
#		# Generate and pack data
#		data = ""
#		if self.eit_file:
#TODO
#			pass
#		# Write data to file
#		if os.path.exists(self.eit_file):
#TODO w or wb
#			with open(self.eit_file, 'wb') as file:
#				file.write(data)

