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
from __future__ import absolute_import
import os
import struct
import time
import chardet
import sys
import six

from datetime import datetime

from Components.config import config
from Components.Language import language
from .EMCTasker import emcDebugOut
from .IsoFileSupport import IsoSupport

from .MetaSupport import getInfoFile


def parseMJD(MJD):
	# Parse 16 bit unsigned int containing Modified Julian Date,
	# as per DVB-SI spec
	# returning year,month,day
	YY = int((MJD - 15078.2) / 365.25)
	MM = int((MJD - 14956.1 - int(YY * 365.25)) / 30.6001)
	D = MJD - 14956 - int(YY * 365.25) - int(MM * 30.6001)
	K = 0
	if MM == 14 or MM == 15:
		K = 1

	return (1900 + YY + K), (MM - 1 - K * 12), D


def unBCD(byte):
	return (byte >> 4) * 10 + (byte & 0xf)


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


def _ord(val):
	if six.PY3:
		return val
	else:
		return ord(val)


# Convert string to bytes without encoding
def encode_binary(input):
    output = bytes([ord(char) for char in input])
    return output


# Get encoding
def getEventEncoding(data):
	encoding = None
	try:
		if len(data) > 0:
			byte1 = _ord(data[0])			
			if byte1 == 0x01:
				encoding = 'iso-8859-5'
			elif byte1 == 0x02:
				encoding = 'iso-8859-6'
			elif byte1 == 0x03:
				encoding = 'iso-8859-7'
			elif byte1 == 0x04:
				encoding = 'iso-8859-8'
			elif byte1 == 0x05:
				encoding = 'iso-8859-9'
			elif byte1 == 0x06:
				encoding = 'iso-8859-10'
			elif byte1 == 0x07:
				encoding = 'iso-8859-11'
			elif byte1 == 0x09:
				encoding = 'iso-8859-13'
			elif byte1 == 0x0A:
				encoding = 'iso-8859-14'
			elif byte1 == 0x0B:
				encoding = 'iso-8859-15'
			elif byte1 == 0x15:
				encoding = 'utf-8'
			elif byte1 == 0x10 and len(data) > 2:
				byte2 = _ord(data[1])
				if byte2 == 0x00:
					byte3 = _ord(data[2])
					if byte3 == 0x01:
						encoding = 'iso-8859-1'
					elif byte3 == 0x02:
						encoding = 'iso-8859-2'
					elif byte3 == 0x03:
						encoding = 'iso-8859-3'
					elif byte3 == 0x04:
						encoding = 'iso-8859-4'
					elif byte3 == 0x05:
						encoding = 'iso-8859-5'
					elif byte3 == 0x06:
						encoding = 'iso-8859-6'
					elif byte3 == 0x07:
						encoding = 'iso-8859-7'
					elif byte3 == 0x08:
						encoding = 'iso-8859-8'
					elif byte3 == 0x09:
						encoding = 'iso-8859-9'
					elif byte3 == 0x0A:
						encoding = 'iso-8859-10'
					elif byte3 == 0x0B:
						encoding = 'iso-8859-11'
					elif byte3 == 0x0D:
						encoding = 'iso-8859-13'
					elif byte3 == 0x0E:
						encoding = 'iso-8859-14'
					elif byte3 == 0x0F:
						encoding = 'iso-8859-15'			
			elif byte1 >= 0x20 and byte1 <= 0xFF:
				encoding = 'iso6937'
			#elif byte1 >= 0x11 and byte <= 0x14:	### not supported now
			#	encoding = None
	except:
		encoding = None
	return encoding


# Read event data and decode it
def readEventData(data, index, name):
	description = ""
	length = _ord(data[index])
	if length > 0:
		encoding = getEventEncoding(data[index + 1:index + 4])
		if encoding:
			emcDebugOut("[META] Found " + name + " encoding-type: " + encoding)			
		for i in list(range(index + 1, index + length + 1)):
			try:
				if _ord(data[i]) == 0x0A or _ord(data[i]) > 0x1F:
					if six.PY3:
						description += chr(data[i])
					else:
						description += data[i]
			except IndexError as e:
				emcDebugOut("[META] Exception in readEitFile: " + str(e))

		if description:
			try:
				if encoding:
					if encoding != 'iso6937':
						if six.PY3:
							description = encode_binary(description).decode(encoding)
						elif encoding != 'utf-8':
							description = description.decode(encoding).encode("utf-8")
					elif not six.PY3:
						description = description.decode('cp1252').encode("utf-8")
				else:
					description = encode_binary(description)
					encdata = chardet.detect(description)
					enc = encdata['encoding'].lower()
					confidence = str(encdata['confidence'])
					emcDebugOut("[META] Detected " + name + " encoding-type: " + enc + " (" + confidence + ")")
					description = six.ensure_str(description, enc)
			except (UnicodeDecodeError, AttributeError) as e:
				emcDebugOut("[META] Exception in readEitFile: " + str(e))
	return length + 1, description


def addDescriptionToList(description, descriptionList, pluginLanguage, eventLanguage, prevEventLanguage, newLine = True):
	if eventLanguage == pluginLanguage:
		descriptionList[0].append(description)
	if (eventLanguage == prevEventLanguage) or (prevEventLanguage == "x"):
		descriptionList[1].append(description)
	else:
		descriptionList[1].append("\n\n" if newLine else "  " + description)


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
		if len(length) > 2:
			return self.__mk_int((length[0] * 60 + length[1]) * 60 + length[2])
		elif len(length) > 1:
			return self.__mk_int(length[0] * 60 + length[1])
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
				except Exception as e:
					emcDebugOut("[META] Exception in readEitFile: " + str(e))
				finally:
					if f is not None:
						f.close()

				# Parse the data
				if data and 12 <= len(data):
					# go through events
					pos = 0
					e = struct.unpack(">HHBBBBBBH", data[pos:pos + 12])
					event_id = e[0]
					date = parseMJD(e[1])                         # Y, M, D
					time = unBCD(e[2]), unBCD(e[3]), unBCD(e[4])  # HH, MM, SS
					duration = unBCD(e[5]), unBCD(e[6]), unBCD(e[7])  # HH, MM, SS
					running_status = (e[8] & 0xe000) >> 13
					free_CA_mode = e[8] & 0x1000
					descriptors_len = e[8] & 0x0fff

					if running_status in [1, 2]:
						self.eit['when'] = "NEXT"
					elif running_status in [3, 4]:
						self.eit['when'] = "NOW"

					self.eit['startdate'] = date
					self.eit['starttime'] = time
					self.eit['duration'] = duration

					pos = pos + 12
					name_event_descriptors = [ [], [] ]
					short_event_descriptors = [ [], [] ]
					extended_event_descriptors = [ [], [] ]
					extended_event_items = [ [], [] ]
					component_descriptor = []
					content_descriptor = []
					linkage_descriptor = []
					parental_rating_descriptor = []
					endpos = len(data) - 1
					prev1_ISO_639_language_code = "x"
					prev2_ISO_639_language_code = "x"
					while pos < endpos:
						rec = _ord(data[pos])
						if pos + 1 >= endpos:
							break
						length = _ord(data[pos + 1]) + 2
						idx = pos
						#if pos+length>=endpos:
						#	break
						if rec == 0x4D:
							ISO_639_language_code = six.ensure_str(data[idx + 2:idx + 5]).upper()
							idx += 5

							### section name
							(offset, name_event_description) = readEventData(data, idx, "name_event")
							if offset > 0:
								addDescriptionToList(name_event_description, name_event_descriptors, lang, ISO_639_language_code, prev1_ISO_639_language_code, False)
							idx += offset
							
							### section description
							(offset, short_event_description) = readEventData(data, idx, "short_event")
							if offset > 0:
								addDescriptionToList(short_event_description, short_event_descriptors, lang, ISO_639_language_code, prev1_ISO_639_language_code)

							prev1_ISO_639_language_code = ISO_639_language_code							
						elif rec == 0x4E:
							ISO_639_language_code = six.ensure_str(data[idx + 3:idx + 6]).upper()
							idx += 6

							### section items
							length_of_items = _ord(data[idx])
							if length_of_items > 0:
								curlen = 0
								idx_items = idx + 1
								while curlen < length_of_items:
									### item description
									(offset, item_description_text) = readEventData(data, idx_items, "extended_event_item_description")
									idx_items += offset
									curlen += offset

									### item text
									(offset, item_text) = readEventData(data, idx_items, "extended_event_item_text")
									idx_items += offset
									curlen += offset
									extended_event_item = "\n" + item_description_text + ": " + item_text
									addDescriptionToList(extended_event_item, extended_event_items, lang, ISO_639_language_code, prev2_ISO_639_language_code)									
								idx += length_of_items
							idx += 1

							### section event text
							(offset, extended_event_description) = readEventData(data, idx, "extended_event")							
							if len(extended_event_description) > 0:
								addDescriptionToList(extended_event_description, extended_event_descriptors, lang, ISO_639_language_code, prev2_ISO_639_language_code)

							prev2_ISO_639_language_code = ISO_639_language_code
						elif rec == 0x50:
							component_descriptor.append(data[pos + 8:pos + length])
						elif rec == 0x54:
							content_descriptor.append(data[pos + 8:pos + length])
						elif rec == 0x4A:
							linkage_descriptor.append(data[pos + 8:pos + length])
						elif rec == 0x55:
							parental_rating_descriptor.append(data[pos + 2:pos + length])
						else:
#							print "unsupported descriptor: %x %x" %(rec, pos + 12)
#							print data[pos:pos+length]
							pass
						pos += length

					name_event_descriptor = ""
					short_event_descriptor = ""
					extended_event_descriptor = ""
					extended_event_item_descriptor = ""

					if name_event_descriptors[0]:
						name_event_descriptor = "".join(name_event_descriptors[0])
					else:
						name_event_descriptor = ("".join(name_event_descriptors[1])).strip()

					if short_event_descriptors[0]:
						short_event_descriptor = "".join(short_event_descriptors[0])
					else:
						short_event_descriptor = ("".join(short_event_descriptors[1])).strip()

					if extended_event_descriptors[0]:
						extended_event_descriptor = "".join(extended_event_descriptors[0])
					else:
						extended_event_descriptor = ("".join(extended_event_descriptors[1])).strip()

					if extended_event_items[0]:
						extended_event_item_descriptor = "".join(extended_event_items[0])
					elif extended_event_items[1]:
						extended_event_item_descriptor = ("".join(extended_event_items[1])).strip()

					if extended_event_item_descriptor:
						extended_event_descriptor += "\n" + extended_event_item_descriptor

					if not(extended_event_descriptor):
						extended_event_descriptor = short_event_descriptor

					self.eit['name'] = name_event_descriptor
					self.eit['short_description'] = short_event_descriptor

					if extended_event_descriptor:
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
