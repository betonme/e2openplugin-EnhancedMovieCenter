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

import os, sys
from Components.config import *
from __init__ import _
extensions = [".ts.ap", ".ts.cuts", ".ts.cutsr", ".ts.meta", ".ts.sc", ".eit", ".ts_mp.jpg"]

class RogueFileCheck:
	def __init__(self, path, avoid=""):
		self.found = {}
		self.files = []
		if path is not None:
			self.checkPath(path, avoid)

	def getStatistics(self):
		strg = ""
		for key in self.found:	strg += key + ": " + str(self.found[key]) + _(" files\n")
		if strg == "":	strg = _("No rogue files found.")
		else:			strg = _("Found rogue files:\n\n") + strg
		return strg

	def checkPath(self, path, avoid=""):
		if not os.path.exists(path) or path is avoid: return
		if not path.endswith("/"): path += "/"

		for p in os.listdir(path):
			if os.path.isdir(path + p):
				try: self.checkPath(path + p)
				except: pass
			else:
				for ext in extensions:
					if p.endswith(ext):
						if not os.path.exists( path + p.replace(ext, ".ts") ):
							try:    self.found[ext] += 1
							except: self.found[ext] = 1
							self.files.append(path+p)
						break

	def getDelFilesScript(self):
		strg = ""
		for file in self.files:
			strg += "rm \"" +file+ "\"\n"
		return strg

	def getScript(self, path):
		if not path.endswith("/"): path += "/"
		strg = ""
		if os.path.exists(path) and int(config.EMC.movie_trashcan_limit.value) != 0:	# check if the trashcan exists
			for file in self.files:
				strg += "\nmv \"" +file+ "\" \"" +path+ "\""
		else:
			for file in self.files:
				strg += "\nrm -f \"" +file+ "\""
		return strg[1:]
