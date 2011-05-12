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

import os

from enigma import eServiceReference
from EMCTasker import emcDebugOut


class VlcFileListWrapper:
	def __init__(self):
		pass
	def getNextFile(self):
		return None, None
	def getPrevFile(self):
		return None, None


class VlcPluginInterfaceSel():
	def browsingVLC(self):
		return self.currentPathSel.find("VLC servers") > -1

	def vlcMovieSelected(self, entry):
		try:
			self.hide()
#			from Plugins.Extensions.VlcPlayer.VlcPlayer import VlcPlayer
#			dlg = self.session.open(VlcPlayer, self["list"].vlcServer, VlcFileListWrapper())
#			dlg.playfile(entry[4], entry[3])
			try:	# v2.5
				self["list"].vlcServer.play(self, entry[4], entry[3], VlcFileListWrapper())
			except:	# v2.6
				self["list"].vlcServer.play(self.session, entry[4], entry[3], VlcFileListWrapper())
			self.wasClosed = True
			self.close()
		except Exception, e:
			emcDebugOut("[spVLC] vlcMovieSelected exception:\n" + str(e))


class VlcPluginInterfaceList():
	def currentSelIsVlc(self):
		try:	return self.list[self.getCurrentIndex()][2] == "VLCs"
		except:	return False

	def currentSelIsVlcDir(self):
		try:	return self.list[self.getCurrentIndex()][1] == "VLCd"
		except:	return False

	def reloadVlcServers(self):
		try:
			from Plugins.Extensions.VlcPlayer.VlcServerConfig import vlcServerConfig
			self.vlcServers = vlcServerConfig.getServerlist()	# settings change requires running this
			self.list = []
			if self.vlcServers:
				for srv in self.vlcServers:
					srvName = srv.getName()
					emcDebugOut("[spML] srvName = " + str(srvName))
					sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + self.loadPath+srvName)	# dummy ref
					self.list.append((sref, "VLCd", None, None, srvName, None, 0, ""))
			self.list.sort(key=lambda x: x[4],reverse=False)
			# Insert the back entry
			sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + "..")	# dummy ref
			self.list.insert(0, (sref, None, None, None, "..", None, 0, ""))
			# Assign list to listbox
			self.l.setList(self.list)
		except:	pass

	def reloadVlcFilelist(self):
		self.list = []
		tmplist = []
		loadPath = self.loadPath
		vlcPath = loadPath[loadPath.find("VLC servers/")+12:]	# server/dir/name/
		serverName = vlcPath.split("/")[0]
		emcDebugOut("[spML] path on %s = %s" %(serverName, vlcPath))
		server = None
		self.vlcServer = None
		if self.vlcServers:
			for srv in self.vlcServers:
				if srv.getName() == serverName: 
					#emcDebugOut("[spML] srv = " + str(srv))
					server = srv	# find the server
		if server is not None:
			try:
				self.vlcServer = server
				baseDir = server.getBasedir()
				emcDebugOut("[spML] baseDir = " + baseDir)
				vlcPath = vlcPath[len(serverName):]
				emcDebugOut("[spML] vlcPath = " + vlcPath)
				# Build path
				if baseDir.startswith("/"):
					baseDir = baseDir[1:]
				if baseDir == "":
					if vlcPath.startswith("/"):
						path = vlcPath[1:]
					else:
						path = vlcPath
				elif baseDir.endswith("/"):
					if vlcPath.startswith("/"):
						path = baseDir[:-1]+vlcPath
					else:
						path = baseDir+vlcPath
				else:
					if vlcPath.startswith("/"):
						path = baseDir+vlcPath
					else:
						path = baseDir+"/"+vlcPath
				# Load path
				emcDebugOut("[spML] path = " + path)
				(vlcFiles, vlcDirs) = server.getFilesAndDirs(path, None)
				emcDebugOut("[spML] got files and dirs...")
				if vlcDirs:
					for d in vlcDirs:
						if d[0] == "..": continue
						emcDebugOut("[spML] d[0] = " + str(d[0]) + d[0])
						#sref = eServiceReference("2:0:1:0:0:0:0:0:0:0" + loadPath+d[0])	# dummy ref
						sref = eServiceReference("2:0:1:0:0:0:0:0:0:0") #:")# + loadPath+d[0])	# dummy ref
						sref.setPath(loadPath+d[0])
						emcDebugOut("[spML] sref = " + sref.getPath())
						self.list.append((sref, "VLCd", None, None, d[0], None, 0, ""))
					self.list.sort(key=lambda x: x[4],reverse=False)
				if vlcFiles:
					for f in vlcFiles:
						from Plugins.Extensions.VlcPlayer.VlcFileList import MEDIA_EXTENSIONS
						from MovieCenter import mediaExt
						global mediaExt
						ext = os.path.splitext(f[0])[1].lower()
						if MEDIA_EXTENSIONS.has_key(ext) or ext in mediaExt:
							emcDebugOut("[spML] f[0] = " + str(f[0]))
							sref = eServiceReference("2:0:1:0:0:0:0:0:0:0") #:" + loadPath+f[0])	# dummy ref
							sref.setPath(loadPath+f[0])
							#sref.setPath(path+f[0])
							tmplist.append((sref, None, "VLCs", f[0], f[1], None, 0, ext))
					tmplist.sort(key=lambda x: x[4],reverse=False)
			except Exception, e:
				emcDebugOut("[spML] reloadVlcFilelist exception:\n" + str(e))
		# Insert the back entry
		sref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + "..")	# dummy ref
		self.list.insert(0, (sref, None, None, None, "..", None, 0, ""))
		# Combine folders and files
		self.list.extend( tmplist )
		# Assign list to listbox
		self.l.setList(self.list)

