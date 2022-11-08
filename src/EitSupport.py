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
import chardet

from datetime import datetime

from Components.config import config
from Components.Language import language
from EMCTasker import emcDebugOut
from IsoFileSupport import IsoSupport

from MetaSupport import getInfoFile

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

from Tools.ISO639 import LanguageCodes
def language_iso639_2to3(alpha2):
	ret = alpha2
	if alpha2 in LanguageCodes:
		language = LanguageCodes[alpha2]
		for alpha, name in LanguageCodes.items():
			if name == language:
				if len(alpha) == 3:
					return alpha
	return ret

def getEventCodePage(data):
	encoding = None
	try:
		if len(data) > 0:
			byte1 = ord(data[0])			
			if byte1 == 0x01: encoding = 'iso-8859-5'
			elif byte1 == 0x02: encoding = 'iso-8859-6'
			elif byte1 == 0x03: encoding = 'iso-8859-7'
			elif byte1 == 0x04: encoding = 'iso-8859-8'
			elif byte1 == 0x05: encoding = 'iso-8859-9'
			elif byte1 == 0x06: encoding = 'iso-8859-10'
			elif byte1 == 0x07: encoding = 'iso-8859-11'
			elif byte1 == 0x09: encoding = 'iso-8859-13'
			elif byte1 == 0x0A: encoding = 'iso-8859-14'
			elif byte1 == 0x0B: encoding = 'iso-8859-15'
			elif byte1 == 0x15: encoding = 'utf-8'
			elif byte1 == 0x10 and len(data) > 2:
				byte2 = ord(data[1])
				byte3 = ord(data[2])
				if byte2 == 0x00:
					if byte3 == 0x01: encoding = 'iso-8859-1'
					elif byte3 == 0x02: encoding = 'iso-8859-2'
					elif byte3 == 0x03: encoding = 'iso-8859-3'
					elif byte3 == 0x04: encoding = 'iso-8859-4'
					elif byte3 == 0x05: encoding = 'iso-8859-5'
					elif byte3 == 0x06: encoding = 'iso-8859-6'
					elif byte3 == 0x07: encoding = 'iso-8859-7'
					elif byte3 == 0x08: encoding = 'iso-8859-8'
					elif byte3 == 0x09: encoding = 'iso-8859-9'
					elif byte3 == 0x0A: encoding = 'iso-8859-10'
					elif byte3 == 0x0B: encoding = 'iso-8859-11'
					elif byte3 == 0x0D: encoding = 'iso-8859-13'
					elif byte3 == 0x0E: encoding = 'iso-8859-14'
					elif byte3 == 0x0F: encoding = 'iso-8859-15'
	except:
		encoding = None
	
	return encoding
	
# Eit File support class
# Description
# http://de.wikipedia.org/wiki/Event_Information_Table
class EitList():

	EIT_SHORT_EVENT_DESCRIPTOR = 0x4d
	EIT_EXTENDED_EVENT_DESCRIPOR = 0x4e

	def __init__(self, path=None):
		self.eit_file = None
		self.eit_mtime = 0

		#TODO
		# The dictionary implementation could be very slow
		self.eit = {}
		self.iso = None

		self.__newPath(path)
		self.__readEitFile()

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

			exts = [".eit"]
			fpath = getInfoFile(path, exts)[1]
			path = os.path.splitext(fpath)[0]

			if not os.path.exists(path + ".eit"):
				# Strip existing cut number
				if path[-4:-3] == "_" and path[-3:].isdigit():
					path = path[:-4]
			path += ".eit"
			if self.eit_file != path:
				self.eit_file = path
				self.eit_mtime = 0

	def __mk_int(self, s):
		return int(s) if s else 0

	def __toDate(self, d, t):
		if d and t:
			#TODO Is there another fast and safe way to get the datetime
			try:
				return datetime(int(d[0]), int(d[1]), int(d[2]), int(t[0]), int(t[1]))
			except ValueError:
				return None
		else:
			return None

	##############################################################################
	## Get Functions
	def getEitsid(self):
		return self.eit.get('service', "") #TODO

	def getEitTsId(self):
		return self.eit.get('transportstream', "") #TODO

	def getEitWhen(self):
		return self.eit.get('when', "")

	def getEitStartDate(self):
		return self.eit.get('startdate', "")

	def getEitStartTime(self):
		return self.eit.get('starttime', "")

	def getEitDuration(self):
		return self.eit.get('duration', "")

	def getEitName(self):
		return self.eit.get('name', "").strip()

	def getEitDescription(self):
		return self.eit.get('description', "").strip()

	def getEitShortDescription(self):
		return self.eit.get('short_description', "").strip()

	def getEitExtendedDescription(self):
		return self.getEitDescription()

	def getEitLengthInSeconds(self):
		length = self.eit.get('duration', "")
		#TODO Is there another fast and safe way to get the length
		if len(length)>2:
			return self.__mk_int((length[0]*60 + length[1])*60 + length[2])
		elif len(length)>1:
			return self.__mk_int(length[0]*60 + length[1])
		else:
			return self.__mk_int(length)

	def getEitDate(self):
		return self.__toDate(self.getEitStartDate(), self.getEitStartTime())

	##############################################################################
	## File IO Functions
	def __readEitFile(self):
		data = ""
		path = self.eit_file

		lang = (language_iso639_2to3(config.EMC.epglang.value.lower()[:2])).upper()

		if path and os.path.exists(path):
			mtime = os.path.getmtime(path)
			if self.eit_mtime == mtime:
				# File has not changed
				pass

			else:
				#print "EMC TEST count Eit " + str(path)

				# New path or file has changed
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
					name_event_descriptor = []
					name_event_descriptor_multi = []
					name_event_codepage = None
					short_event_descriptor = []
					short_event_descriptor_multi = []
					short_event_codepage = None
					extended_event_descriptor = []
					extended_event_descriptor_multi = []
					extended_event_codepage = None
					component_descriptor = []
					content_descriptor = []
					linkage_descriptor = []
					parental_rating_descriptor = []
					endpos = len(data) - 1
					prev1_ISO_639_language_code = "x"
					prev2_ISO_639_language_code = "x"
					while pos < endpos:
						rec = ord(data[pos])
						if pos+1>=endpos:
							break
						length = ord(data[pos+1]) + 2
						#if pos+length>=endpos:
						#	break
						if rec == 0x4D:
							descriptor_tag = ord(data[pos+1])
							descriptor_length = ord(data[pos+2])
							ISO_639_language_code = str(data[pos+2:pos+5]).upper()
							event_name_length = ord(data[pos+5])
							name_event_description = ""
							for i in range (pos+6,pos+6+event_name_length):
								try:
									if str(ord(data[i]))=="10" or int(str(ord(data[i])))>31:
										name_event_description += data[i]
								except IndexError, e:
									emcDebugOut("[META] Exception in readEitFile: " + str(e))
							if not name_event_codepage:
								idx = pos+6
								name_event_codepage = getEventCodePage(data[idx:idx+3])
								if name_event_codepage:
									emcDebugOut("[META] Found name_event encoding-type: " + name_event_codepage)
							short_event_description = ""
							if not short_event_codepage:
								idx = pos+7+event_name_length
								short_event_codepage = getEventCodePage(data[idx:idx+3])
								if short_event_codepage:
									emcDebugOut("[META] Found short_event encoding-type: " + short_event_codepage)
							for i in range (pos+7+event_name_length,pos+length):
								try:
									if str(ord(data[i]))=="10" or int(str(ord(data[i])))>31:
										short_event_description += data[i]
								except IndexError, e:
									emcDebugOut("[META] Exception in readEitFile: " + str(e))
							if ISO_639_language_code == lang:
								short_event_descriptor.append(short_event_description)
								name_event_descriptor.append(name_event_description)
							if (ISO_639_language_code == prev1_ISO_639_language_code) or (prev1_ISO_639_language_code == "x"):
								short_event_descriptor_multi.append(short_event_description)
								name_event_descriptor_multi.append(name_event_description)
							else:
								short_event_descriptor_multi.append("\n\n" + short_event_description)
								name_event_descriptor_multi.append(" " + name_event_description)
							prev1_ISO_639_language_code = ISO_639_language_code
						elif rec == 0x4E:
							ISO_639_language_code = ""
							for i in range (pos+3,pos+6):
								ISO_639_language_code += data[i]
							ISO_639_language_code = ISO_639_language_code.upper()
							extended_event_description = ""
							if not extended_event_codepage:
								idx = pos+8
								extended_event_codepage = getEventCodePage(data[idx:idx+3])
								if extended_event_codepage:
									emcDebugOut("[META] Found extended_event encoding-type: " + extended_event_codepage)
							for i in range (pos+8,pos+length):
								try:
									if str(ord(data[i]))=="10" or int(str(ord(data[i])))>31:
										extended_event_description += data[i]
								except IndexError, e:
									emcDebugOut("[META] Exception in readEitFile: " + str(e))
							if ISO_639_language_code == lang:
								extended_event_descriptor.append(extended_event_description)
							if (ISO_639_language_code == prev2_ISO_639_language_code) or (prev2_ISO_639_language_code == "x"):
								extended_event_descriptor_multi.append(extended_event_description)
							else:
								extended_event_descriptor_multi.append("\n\n" + extended_event_description)
							prev2_ISO_639_language_code = ISO_639_language_code
						elif rec == 0x50:
							component_descriptor.append(data[pos+8:pos+length])
						elif rec == 0x54:
							content_descriptor.append(data[pos+8:pos+length])
						elif rec == 0x4A:
							linkage_descriptor.append(data[pos+8:pos+length])
						elif rec == 0x55:
							parental_rating_descriptor.append(data[pos+2:pos+length])
						else:
#							print "unsupported descriptor: %x %x" %(rec, pos + 12)
#							print data[pos:pos+length]
							pass
						pos += length

					if name_event_descriptor:
						name_event_descriptor = "".join(name_event_descriptor)
					else:
						name_event_descriptor = ("".join(name_event_descriptor_multi)).strip()

					if short_event_descriptor:
						short_event_descriptor = "".join(short_event_descriptor)
					else:
						short_event_descriptor = ("".join(short_event_descriptor_multi)).strip()

					if extended_event_descriptor:
						extended_event_descriptor = "".join(extended_event_descriptor)
					else:
						extended_event_descriptor = ("".join(extended_event_descriptor_multi)).strip()

					if not(extended_event_descriptor):
						extended_event_descriptor = short_event_descriptor
						extended_event_codepage = short_event_codepage

					if name_event_descriptor:
						try:
							if name_event_codepage:
								if name_event_codepage != 'utf-8':
									name_event_descriptor = name_event_descriptor.decode(name_event_codepage).encode("utf-8")
								else:
									name_event_descriptor.decode('utf-8')
							else:
								encdata = chardet.detect(name_event_descriptor)
								enc = encdata['encoding'].lower()
								confidence = str(encdata['confidence'])
								emcDebugOut("[META] Detected name_event encoding-type: " + enc + " (" + confidence + ")")
								if enc == "utf-8":
									name_event_descriptor.decode(enc)
								else:
									name_event_descriptor = name_event_descriptor.decode(enc).encode('utf-8')
						except (UnicodeDecodeError, AttributeError), e:
							emcDebugOut("[META] Exception in readEitFile: " + str(e))
					self.eit['name'] = name_event_descriptor

					if short_event_descriptor:
						try:
							if short_event_codepage:
								if short_event_codepage != 'utf-8':
									short_event_descriptor = short_event_descriptor.decode(short_event_codepage).encode("utf-8")
								else:
									short_event_descriptor.decode('utf-8')
							else:
								encdata = chardet.detect(short_event_descriptor)
								enc = encdata['encoding'].lower()
								confidence = str(encdata['confidence'])
								emcDebugOut("[META] Detected short_event encoding-type: " + enc + " (" + confidence + ")")
								if enc == "utf-8":
									short_event_descriptor.decode(enc)
								else:
									short_event_descriptor = short_event_descriptor.decode(enc).encode('utf-8')
						except (UnicodeDecodeError, AttributeError), e:
							emcDebugOut("[META] Exception in readEitFile: " + str(e))
					self.eit['short_description'] = short_event_descriptor

					if extended_event_descriptor:
						try:
							if extended_event_codepage:
								if extended_event_codepage != 'utf-8':
									extended_event_descriptor = extended_event_descriptor.decode(extended_event_codepage).encode("utf-8")
								else:
									extended_event_descriptor.decode('utf-8')
							else:
								encdata = chardet.detect(extended_event_descriptor)
								enc = encdata['encoding'].lower()
								confidence = str(encdata['confidence'])
								emcDebugOut("[META] Detected extended_event encoding-type: " + enc + " (" + confidence + ")")
								if enc == "utf-8":
									extended_event_descriptor.decode(enc)
								else:
									extended_event_descriptor = extended_event_descriptor.decode(enc).encode('utf-8')
						except (UnicodeDecodeError, AttributeError), e:
							emcDebugOut("[META] Exception in readEitFile: " + str(e))

						# This will fix EIT data of RTL group with missing line breaks in extended event description
						import re
						extended_event_descriptor = re.sub('((?:Moderat(?:ion:|or(?:in){0,1})|Vorsitz: |Jur(?:isten|y): |G(?:\xC3\xA4|a)st(?:e){0,1}: |Mit (?:Staatsanwalt|Richter(?:in){0,1}|den Schadenregulierern) |Julia Leisch).*?[a-z]+)(\'{0,1}[0-9A-Z\'])', r'\1\n\n\2', extended_event_descriptor)
					self.eit['description'] = extended_event_descriptor

				else:
					# No date clear all
					self.eit = {}

		else:
			# No path or no file clear all
			self.eit = {}