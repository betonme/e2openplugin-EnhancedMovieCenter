#!/usr/bin/python
# encoding: utf-8
#
# FreesatHuffmanDecoder
# Copyright (C) 2022 pjsharp
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
from enigma import eEnv
from os.path import isabs
import re

# Global constants
START = 0x00
STOP = 0x00
ESCAPE = 0x01


# Support for freeSat huffman decoding
class FreesatHuffmanDecoder():

	coding_tables = [
		['enigma2/freesat.t1', []],
		['enigma2/freesat.t2', []]
		]

	def __init__(self, initializeTables = False):
		if initializeTables:
			for id in range(len(self.coding_tables)):
				self.__getCodingTable(id)
		return

	def __getCodingTable(self, id):
		result = None

		if id > 0 and id <= len(self.coding_tables):
			coding_table = self.coding_tables[id - 1]
			if coding_table[1]:
				result = coding_table[1]
			else:
				coding_table[1] = [{} for i in range(256)]
				try:
					with open(self.__getTableName(coding_table[0]), 'r') as fp:
						pattern = re.compile('^(?:(?P<fromctrl>START|STOP|ESCAPE)|(?:0x(?P<fromhex>[0-9a-fA-F]{2}))|(?P<fromchar>.))\:(?P<binvalue>[01]+)\:(?:(?P<toctrl>STOP|ESCAPE)|(?:0x(?P<tohex>[0-9a-fA-F]{2}))|(?P<tochar>.))')
						line = fp.readline()
						while line:
							try:
								m = pattern.match(line)
								if m:
									fromchar = None
									if m.group("fromchar"):
										fromchar = ord(m.group("fromchar"))
									elif m.group("fromhex"):
										fromchar = int(m.group("fromhex"), base=16)
									elif m.group("fromctrl"):
										fromchar = START if m.group("fromctrl") == "START" else None

									if fromchar == None:
										continue
										
									binvalue = m.group("binvalue")
									
									if binvalue in coding_table[1][fromchar]:
										continue
										
									tochar = ''
									if m.group("tochar"):
										tochar = ord(m.group("tochar"))
									elif m.group("tohex"):
										tochar = int(m.group("tohex"), base=16)
									elif m.group("toctrl"):
										tochar = ESCAPE if m.group("toctrl") == "ESCAPE" else STOP
									coding_table[1][fromchar][binvalue] = tochar
							finally:
								line = fp.readline()
				except Exception as e:
					coding_table[1] = None
					raise
			result = coding_table[1]
		return result

	def __findNextChar(self, reader, table, lastchar):
		nextchar = None
		cdict = table[lastchar]
		bits = ""
		run = 1
		while run:
			c = reader.readBit()
			if c == None:
				run = 0
				break
			bits += str(c)
			nextchar = cdict.get(bits)
			if nextchar != None:
				break;
		return nextchar

	def __getTableName(self, name):
		return name if isabs(name) else eEnv.resolve("${datadir}" + "/" + name)

	def decode(self, data):
		result = ""

		if data == None or len(data) <= 2 or data[0] != 0x1F or (data[1] != 0x01 and data[1] != 0x02):
			return result

		table = self.__getCodingTable(data[1])
		if table == None:
			raise Exception("Coding table could not be loaded")
			
		run = 1
		lastchar = 0
		reader = self.__BinaryReader(data[2:])
		
		while run:
			if lastchar == ESCAPE:
				nextchar = reader.readByte()
				if nextchar == None:
					break
				if (nextchar & 0x80) == 0:
					lastchar = nextchar
				if nextchar != STOP and nextchar != ESCAPE:
					result += chr(nextchar)
			else:
				nextchar = self.__findNextChar(reader, table, lastchar)
				if nextchar == None:
					break
				if nextchar != STOP and nextchar != ESCAPE:
					result += chr(nextchar)
				lastchar = nextchar
				
			if lastchar == STOP:
				run = 0
		return result

	# Helper class for binary reading
	class __BinaryReader(object):

		def __init__(self, data):
			self.data = data		
			self.byteidx = 0 if len(data) > 0 else -1
			self.bitidx = 0

		def readBit(self):
			result = None
			if self.byteidx >= 0:
				byte = self.data[self.byteidx]
				value = byte & (1 << (7 - self.bitidx))
				self.bitidx += 1
				if self.bitidx % 8 == 0:
					if self.byteidx + 1 < len(self.data):
						self.byteidx += 1
						self.bitidx = 0
					else:
						self.byteidx = -1
				result = 1 if value > 0 else 0
			return result

		def readByte(self):
			result = 0
			for i in range(8):
				b = self.readBit()
				if b != None:
					result |= (b << (7 - i))
				else:
					result = None
					break;
			return result
