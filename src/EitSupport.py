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

from datetime import datetime

from Components.config import config
from Components.Language import language
from EMCTasker import emcDebugOut
from IsoFileSupport import IsoSupport

from MetaSupport import getInfoFile

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

decoding_charSpecHR = {u'Ć': u'\u0106', u'æ': u'\u0107', u'®': u'\u017D', u'¾': u'\u017E', u'©': u'\u0160', u'¹': u'\u0161', u'Č': u'\u010C', u'è': u'\u010D', u'ð': u'\u0111'}

decoding_charSpecCZSK = {u'Ï'+u'C': u'Č',u'Ï'+u'E': u'Ě',u'Ï'+u'L': u'Ľ',u'Ï'+u'N': u'Ň',u'Ï'+u'R': u'Ř',u'Ï'+u'S': u'Š',u'Ï'+u'T': u'Ť',u'Ï'+u'Z': u'Ž',u'Ï'+u'c': u'č',u'Ï'+u'd': u'ď',u'Ï'+u'e': u'ě',u'Ï'+u'l': u'ľ', u'Ï'+u'n': u'ň',
u'Ï'+u'r': u'ř',u'Ï'+u's': u'š',u'Ï'+u't': u'ť',u'Ï'+u'z': u'ž',u'Ï'+u'D': u'Ď',u'Â'+u'A': u'Á',u'Â'+u'E': u'É',u'Â'+u'I': u'Í',u'Â'+u'O': u'Ó',u'Â'+u'U': u'Ú',u'Â'+u'a': u'á',u'Â'+u'e': u'é',u'Â'+u'i': u'í',u'Â'+u'o': u'ó',
u'Â'+u'u': u'ú',u'Â'+u'y': u'ý',u'Ã'+u'o': u'ô',u'Ã'+u'O': u'Ô',u'Ê'+u'u': u'ů',u'Ê'+u'U': u'Ů',u'È'+u'A': u'Ä',u'È'+u'E': u'Ë',u'È'+u'I': u'Ï',u'È'+u'O': u'Ö',u'È'+u'U': u'Ü',u'È'+u'Y': u'Ÿ',u'È'+u'a': u'ä',u'È'+u'e': u'ë',
u'È'+u'i': u'ï',u'È'+u'o': u'ö',u'È'+u'u': u'ü',u'È'+u'y': u'ÿ'}

def convertCharSpecHR(text):
	for i, j in decoding_charSpecHR.iteritems():
		text = text.replace(i, j)
	return text

def convertCharSpecCZSK(text):
	for i, j in decoding_charSpecCZSK.iteritems():
		text = text.replace(i, j)
	return text

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
#TEST
#print LanguageCodes["sv"]
#print language_iso639_2to3("sv")


# Eit File support class
# Description
# http://de.wikipedia.org/wiki/Event_Information_Table
class EitList():

	EIT_SHORT_EVENT_DESCRIPTOR 		= 0x4d
	EIT_EXTENDED_EVENT_DESCRIPOR 	=	0x4e

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

	# Wrapper
	def getEitShortDescription(self):
		return self.getEitName()

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
		
		#lang = language.getLanguage()[:2]
		lang = language_iso639_2to3( config.EMC.epglang.value.lower()[:2] )

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
							descriptor_tag = ord(data[pos+1])
							descriptor_length = ord(data[pos+2])
							ISO_639_language_code = str(data[pos+3:pos+5])
							if ISO_639_language_code == lang:
								event_name_length = ord(data[pos+5])
								short_event_descriptor.append(data[pos+6:pos+6+event_name_length])
							
						elif rec == 0x4E:
							ISO_639_language_code = str(data[pos+3:pos+5])
							if ISO_639_language_code == lang:
								for i in range (pos+8,pos+length):
									if str(ord(data[i]))=="138":
										pass
									else:
										if data[i]== '\x10' or data[i]== '\x00' or  data[i]== '\x02':
											pass
										else:
											extended_event_descriptor.append(data[i])
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

					# Very bad but there can be both encodings
					# User files can be in cp1252
					# Is there no other way?
					short_event_descriptor = " ".join(short_event_descriptor)
					if short_event_descriptor:
						#try:
						#	short_event_descriptor = short_event_descriptor.decode("iso-8859-1").encode("utf-8")
						#except UnicodeDecodeError:
						#	pass
						try:
							short_event_descriptor.decode('utf-8')
						except UnicodeDecodeError:
							try:
								short_event_descriptor = short_event_descriptor.decode("cp1252").encode("utf-8")
							except UnicodeDecodeError:
								# do nothing, otherwise cyrillic wont properly displayed
								#short_event_descriptor = short_event_descriptor.decode("iso-8859-1").encode("utf-8")
								pass
							if (lang == "cs") or (lang == "sk") or (config.EMC.langsupp.value == "CZ&SK"):
								short_event_descriptor = str(convertCharSpecCZSK(short_event_descriptor))
							if (lang == "hr") or (config.EMC.langsupp.value == "HR"):
								short_event_descriptor = str(convertCharSpecHR(short_event_descriptor))
					self.eit['name'] = short_event_descriptor

					# Very bad but there can be both encodings
					# User files can be in cp1252
					# Is there no other way?
					extended_event_descriptor = "\n".join(extended_event_descriptor)
					if extended_event_descriptor:
						#try:
						#	extended_event_descriptor = extended_event_descriptor.decode("iso-8859-1").encode("utf-8")
						#except UnicodeDecodeError:
						#	pass
						try:
							extended_event_descriptor.decode('utf-8')
						except UnicodeDecodeError:
							try:
								extended_event_descriptor = extended_event_descriptor.decode("cp1252").encode("utf-8")
							except UnicodeDecodeError:
								# do nothing, otherwise cyrillic wont properly displayed
								#extended_event_descriptor = extended_event_descriptor.decode("iso-8859-1").encode("utf-8")
								pass
							if (lang == "cs") or (lang == "sk") or (config.EMC.langsupp.value == "CZ&SK"):
								extended_event_descriptor = str(convertCharSpecCZSK(extended_event_descriptor))
							if (lang == "hr") or (config.EMC.langsupp.value == "HR"):
								extended_event_descriptor = str(convertCharSpecHR(extended_event_descriptor))
					self.eit['description'] = extended_event_descriptor

				else:
					# No date clear all
					self.eit = {}

		else:
			# No path or no file clear all
			self.eit = {}