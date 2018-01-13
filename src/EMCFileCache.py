#!/usr/bin/python
# encoding: utf-8
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

from Components.config import config
from datetime import datetime
import os

MinCacheLimit = config.EMC.min_file_cache_limit.getValue()
pathisfile = os.path.isfile
pathisdir  = os.path.isdir
pathislink = os.path.islink
pathexists = os.path.exists
pathreal   = os.path.realpath

idx_isLink=0
idx_isDir=1
idx_isFile=2
idx_Date=3
idx_realpath=4
idx_num=5

class EMCFileCache():
	def __init__(self):
		self.cacheDirectoryList = {}
		self.cacheFileList = {}
		self.cacheAttributeList = {}
		self.cacheCountSizeList = {}

	def addCountSizeToCache(self, path, count, size):
#		print "EMC addCountSizeToCache", path
		if self.cacheCountSizeList.has_key(path):
			lastcount, lastsize = self.cacheCountSizeList[path]
			if lastcount != count or lastsize != size:
				del self.cacheCountSizeList[path]
				self.cacheCountSizeList[path] = count, size
		else:
			self.cacheCountSizeList[path] = count, size
#		print "EMC addCountSizeToCache", self.cacheCountSizeList

	def getCountSizeFromCache(self, path):
		if self.cacheCountSizeList.has_key(path):
			return self.cacheCountSizeList[path]
		else:
			return None
#		print "EMC getCountSizeFromCache", self.cacheCountSizeList

	def delcacheCountSizeList(self):
		self.cacheCountSizeList = {}
		print "EMC delete cacheCountSizeList", self.cacheCountSizeList

	def delcacheCountSizeListEntriesOnFileOp(self,path):
		#print "EMC delcacheCountSizeListEntriesOnFileOp",path
		rescanPaths = []
		if path:
			for k in self.cacheCountSizeList.keys():
				if (k+"/").startswith(path+"/") or (path+"/").startswith(k+"/"): # drop dirs containing path, but not "a/bc" when path is "a/bcd/e", therefore append "/"
					del self.cacheCountSizeList[k]
					rescanPaths.append(k)
					#print "EMC delcacheCountSizeListEntriesOnFileOp IS  deleting",k," due to OP on path ",path
				#else:
					#print "EMC delcacheCountSizeListEntriesOnFileOp NOT deleting",k," due to OP on path ",path
		return rescanPaths

	def IsPathInCountSizeList(self, path):
		if self.cacheCountSizeList.has_key(path):
			return True
		else:
			return False

	def addPathToCache(self, path, subdirlist, filelist, MovieCenterInst):
		if config.EMC.files_cache.value:
			print "EMC addPathToCache", path
			if (len(subdirlist)>MinCacheLimit) or (len(filelist)>MinCacheLimit):
				self.cacheDirectoryList[path] = subdirlist
				for p, n, e in subdirlist:
					if not (p in self.cacheAttributeList):
						AttributeList=[None]*idx_num
						AttributeList[idx_isLink] = pathislink(p)
						AttributeList[idx_isDir]  = True # we are in subdirlist
						AttributeList[idx_isFile] = False # we are in subdirlist
						AttributeList[idx_Date]   = pathexists(p) and MovieCenterInst.checkDate(p, True)
						AttributeList[idx_realpath] = pathreal(p) #for dirs only
						self.cacheAttributeList[p] = AttributeList
				self.cacheFileList[path] = filelist
				for p, n, e in filelist:
					if not (p in self.cacheAttributeList):
						AttributeList=[None]*idx_num
						AttributeList[idx_isLink] = pathislink(p)
						AttributeList[idx_isDir]  = False # we are in filelist, no entry is a real directrory ...
						AttributeList[idx_isFile] = pathisfile(p) # ... but filelist might contain virtual directories
						AttributeList[idx_Date]   = pathexists(p) and MovieCenterInst.checkDate(p, False)
						#AttributeList[idx_realpath] = pathreal(p) #for dirs only
						self.cacheAttributeList[p] = AttributeList
			else:
				if self.cacheDirectoryList.has_key(path):
					self.deleteAssociatedListEntries(self.cacheDirectoryList[path])
					del self.cacheDirectoryList[path]
				if self.cacheFileList.has_key(path):
					self.deleteAssociatedListEntries(self.cacheFileList[path])
					del self.cacheFileList[path]
#		self.debugPrintDirCache()
#		self.debugPrintFileCache()
#		self.debugPrintFileAttributeCache()

	def addRecToCacheFileList(self, path, rec):
		if config.EMC.files_cache.value:
			if self.cacheFileList.has_key(path):
				filelist = self.cacheFileList[path]
				filelist.append(rec)
				del self.cacheFileList[path]
				self.cacheFileList[path] = filelist

	def getCacheForPath(self, path):
		print "EMC getCacheForPath", path
		if config.EMC.files_cache.value and self.cacheDirectoryList.has_key(path) and self.cacheFileList.has_key(path):
			subdirlist = self.cacheDirectoryList[path]
			filelist = self.cacheFileList[path]
#			self.debugPrintDirCache()
#			self.debugPrintFileCache()
#			self.debugPrintFileAttributeCache()
			return subdirlist, filelist
		else:
			return None, None

	def isLink(self, path):
		isLink = None
		if config.EMC.files_cache.value and (path in self.cacheAttributeList):
			isLink = self.cacheAttributeList[path][idx_isLink]
		if isLink is None:
			isLink = pathislink(path)
		return isLink

	def isDir(self, path):
		isDir = None
		if (config.EMC.check_dead_links.value != "always") and config.EMC.files_cache.value and (path in self.cacheAttributeList):
			isDir = self.cacheAttributeList[path][idx_isDir]
		if isDir is None:
			isDir = pathisdir(path)
		return isDir

	def isFile(self, path):
		isFile = None
		if (config.EMC.check_dead_links.value != "always") and config.EMC.files_cache.value and (path in self.cacheAttributeList):
			isFile = self.cacheAttributeList[path][idx_isFile]
		if isFile is None:
			isFile = pathisfile(path)
		return isFile

	def realpath(self, path):
		realpath = None
		if config.EMC.files_cache.value and (path in self.cacheAttributeList):
			realpath = self.cacheAttributeList[path][idx_realpath]
		if realpath is None:
			realpath = pathreal(path)
		return realpath

	def getDateInfoFromCacheForPath(self, path):
		if config.EMC.files_cache.value and (path in self.cacheAttributeList):
			return self.cacheAttributeList[path][idx_Date]
		else:
			return None

	def getDirsFromCacheForPath(self, path):
		if config.EMC.files_cache.value and self.cacheDirectoryList.has_key(path):
			subdirlist = self.cacheDirectoryList[path]
			return subdirlist
		else:
			return None

	def getFilesFromCacheForPath(self, path):
		if config.EMC.files_cache.value and self.cacheFileList.has_key(path):
			filelist = self.cacheFileList[path]
			return filelist
		else:
			return None

	def IsPathInCache(self, path):
		if config.EMC.files_cache.value and self.cacheDirectoryList.has_key(path) and self.cacheFileList.has_key(path):
			return True
		else:
			return False

	def IsPathWithDirsInCache(self, path):
		if config.EMC.files_cache.value and self.cacheDirectoryList.has_key(path):
			return True
		else:
			return False

	def IsPathWithFilesInCache(self, path):
		if config.EMC.files_cache.value and self.cacheFileList.has_key(path):
			return True
		else:
			return False

	def delPathFromCache(self, path):
		if len(path)>1 and path[-1]=="/":
			path = path[:-1]
		print "EMC delPathFromCache", path
		if self.cacheDirectoryList.has_key(path):
			self.deleteAssociatedListEntries(self.cacheDirectoryList[path])
			del self.cacheDirectoryList[path]
		if self.cacheFileList.has_key(path):
			self.deleteAssociatedListEntries(self.cacheFileList[path])
			del self.cacheFileList[path]
#		self.debugPrintDirCache()
#		self.debugPrintFileCache()
#		self.debugPrintFileAttributeCache()

	def delPathFromDirCache(self, path):
		if len(path)>1 and path[-1]=="/":
			path = path[:-1]
		if self.cacheDirectoryList.has_key(path):
			self.deleteAssociatedListEntries(self.cacheDirectoryList[path])
			del self.cacheDirectoryList[path]

	def delPathFromFileCache(self, path):
		if len(path)>1 and path[-1]=="/":
			path = path[:-1]
		if self.cacheFileList.has_key(path):
			self.deleteAssociatedListEntries(self.cacheFileList[path])
			del self.cacheFileList[path]

	def debugPrintFileCache(self):
		print "cacheFileList:"
		for p in self.cacheFileList:
			print p,self.cacheFileList[p]
		print ""

	def debugPrintDirCache(self):
		print "cacheDirectoryList:"
		for p in self.cacheDirectoryList:
			print p,self.cacheDirectoryList[p]
		print ""

	def debugPrintFileAttributeCache(self):
		print "cacheAttributeList:"
		for p in self.cacheAttributeList:
			print p,self.cacheAttributeList[p]
		print ""

	def deleteAssociatedListEntries(self, list):
		for p, n, e in list:
			if p in self.cacheAttributeList and (config.EMC.check_dead_links.value != "only_initially"):
				del self.cacheAttributeList[p]

movieFileCache = EMCFileCache()
