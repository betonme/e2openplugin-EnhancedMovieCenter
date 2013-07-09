# -*- coding: utf-8 -*-

from __init__ import _

from Components.ActionMap import *
from Components.Label import Label
from Components.MenuList import MenuList

from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from enigma import ePicLoad
from Tools.LoadPixmap import LoadPixmap
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Tools.Directories import fileExists
from Screens.Menu import boundFunction
from Components.PluginComponent import plugins

from Components.Button import Button

from twisted.web import client
from twisted.web.client import downloadPage, getPage

from Components.config import *
from Components.ConfigList import *

from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, RT_WRAP, eServiceReference
from enigma import getDesktop
from enigma import loadJPG

from Tools.BoundFunction import boundFunction
from DelayedFunction import DelayedFunction
from time import time

import re, urllib, urllib2, os, time, shutil

config.EMC.imdb = ConfigSubsection()
config.EMC.imdb.search = ConfigSelection(default='0', choices=[('0', _('imdb.de')), ('1', _('themoviedb.org')), ('2', _('ofdb.de')), ('3', _('csfd.cz'))])
config.EMC.imdb.singlesearch = ConfigSelection(default='0', choices=[('0', _('imdb.de')), ('1', _('thetvdb.com')), ('2', _('csfd.cz')), ('3', _('all'))])

class AppURLopener(urllib.FancyURLopener):
	version = "Mozilla/5.0 (X11; U; Linux x86_64; de; rv:1.9.0.15) Gecko/2009102815 Ubuntu/9.04 (jaunty) Firefox/3."

class imdblist(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, False, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 14))
		self.l.setFont(1, gFont("Regular", 16))
		self.l.setFont(2, gFont("Regular", 18))
		self.l.setFont(3, gFont("Regular", 20))
		self.l.setFont(4, gFont("Regular", 22))
		self.l.setFont(5, gFont("Regular", 24))

def imdb_show(title, pp, elapsed, genre, search_title):
	res = [ (title, pp, elapsed, genre, search_title) ]
	if not re.match('.*?(Exist|N/A)', elapsed):
		elapsed = "%s ms." % elapsed
	res.append(MultiContentEntryText(pos=(0, 0), size=(650, 24), font=4, text=search_title, flags=RT_HALIGN_LEFT))
	res.append(MultiContentEntryText(pos=(660, 0), size=(172, 24), font=4, text=elapsed, flags=RT_HALIGN_LEFT))
	return res

def showCoverlist(title, url, path, art):
	res = [ (title, url, path) ]
	title = art + title
	res.append(MultiContentEntryText(pos=(0, 0), size=(550, 24), font=4, text=title, flags=RT_HALIGN_LEFT))
	return res

class EMCImdbScan(Screen):
	if getDesktop(0).size().width() == 1280:
		skin = """
			<screen position="center,center" size="1000,560" title="EMC Cover search">
				<!-- Info: Amount of searched Covers -->
				<widget name="info" position="10,10" size="900,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<!-- aktual movie name -->
				<widget name="m_info" position="200,40" size="800,24" zPosition="0" font="Regular;24" halign="center" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
				<!-- Movie Listbox -->
				<widget name="menulist" position="220,80" size="772,420" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/cursor.png" scrollbarMode="showOnDemand" transparent="1" enableWrapAround="on" />
				<!-- Cover picture -->
				<widget name="poster" position="10,40" size="185,230" zPosition="4" alphatest="on" />
				<!-- Amount of "downloaded", "exist", and "not found" covers -->
				<widget name="download" position="10,371" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<widget name="exist" position="10,323" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<widget name="no_poster" position="10,347" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<!-- Infoline of coversearch -->
				<widget name="done_msg" position="220,512" size="772,48" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<!-- Buttons  -->
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green.png" position="10,278" size="30,30" alphatest="on" />
				<widget name="ButtonGreenText" position="50,285" size="300,22" valign="center" halign="left" zPosition="1" font="Regular;20" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-yellow.png" position="10,418" size="30,30" alphatest="on" />
				<eLabel text="Manage Cover" position="50,425" size="300,22" font="Regular;21" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="10,453" size="30,30" alphatest="on" />
				<widget name="ButtonRedText" position="50,460" size="300,22" valign="center" halign="left" zPosition="1" font="Regular;20" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_menu.png" position="10,495" size="35,25" alphatest="on" />
				<eLabel text="Setup" position="50,498" size="300,22" font="Regular;21" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_ok.png" position="10,530" size="35,25" alphatest="on" />
				<eLabel text="Single search" position="50,533" size="300,22" font="Regular;21" halign="left" valign="center" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="620,500" title="EMC Cover search">
				<!-- actual movie name -->
				<widget name="m_info" position="5,5" size="610,22" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#00bab329" backgroundColor="#000000"/>
				<!-- Movie Listbox -->
				<widget name="menulist" position="5,28" size="610,310" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/cursor.png" scrollbarMode="showOnDemand" transparent="1" enableWrapAround="on" />
				<!-- Cover picture -->
				<widget name="poster" position="160,345" size="115,150" zPosition="4" alphatest="on" />
				<!-- Info: Amount of searched Covers -->
				<widget name="info" position="290,345" size="325,20" zPosition="0" font="Regular;18" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<!-- Amount of "downloaded", "exist", and "not found" covers -->
				<widget name="exist" position="290,375" size="325,20" zPosition="0" font="Regular;18" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<widget name="no_poster" position="290,395" size="325,20" zPosition="0" font="Regular;18" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<widget name="download" position="290,415" size="325,20" zPosition="0" font="Regular;18" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<!-- Infoline of coversearch -->
				<widget name="done_msg" position="290,450" size="325,40" zPosition="0" font="Regular;18" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
				<!-- Buttons  -->
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-green.png" position="5,352" size="30,25" alphatest="on" />
				<widget name="ButtonGreenText" position="45,352" size="300,25" valign="center" halign="left" zPosition="1" font="Regular;18" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-yellow.png" position="5,382" size="30,25" alphatest="on" />
				<eLabel text="Manage Cover" position="45,382" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="5,412" size="30,25" alphatest="on" />
				<widget name="ButtonRedText" position="45,412" size="300,25" valign="center" halign="left" zPosition="1" font="Regular;18" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_menu.png" position="5,442" size="35,25" alphatest="on" />
				<eLabel text="Setup" position="45,442" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_ok.png" position="5,472" size="35,25" alphatest="on" />
				<eLabel text="Single search" position="45,472" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
			</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, data)
		self.m_list = data
		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":		self.exit,
			"EMCOK":		self.ok,
			"EMCGreen":		self.imdb,
			"EMCRed":		self.red,
			"EMCYellow":		self.verwaltung,
			"EMCRedLong":		self.redLong,
			"EMCMenu":		self.config,
		}, -1)
		
		self["ButtonGreen"] = Pixmap()
		self["ButtonGreenText"] = Label(_("Search"))
		self["ButtonRed"] = Pixmap()
		self["ButtonRedText"] = Label(_("Delete"))
		self["poster"] = Pixmap()
		self.menulist = []
		self["menulist"] = imdblist([])
		self["info"] = Label("")
		self["m_info"] = Label("")
		self["genre"] = Label("")
		self["download"] = Label("")
		self["exist"] = Label("")
		self["no_poster"] = Label("")
		self["done_msg"] = Label(_("Press green button to start search"))
		self["info"].setText("")
		self.no_image_poster = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png"
		self.check = "false"
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.running = "false"
		
		self.picload = ePicLoad()
		#self.picload.PictureData.get().append(self.showCoverCallback)
		self.file_format = "(.ts|.avi|.mkv|.divx|.f4v|.flv|.img|.iso|.m2ts|.m4v|.mov|.mp4|.mpeg|.mpg|.mts|.vob|.wmv)"
		
		self.setShowSearchSiteName()

	def verwaltung(self):
		self.menulist = []
		self.count_movies = len(self.m_list)
		self.vm_list = self.m_list[:]
		count_existing = 0
		count_na = 0
		for each in sorted(self.vm_list):			
			(title, path) = each
			path = re.sub(self.file_format + "$", '.jpg', path)
			if os.path.exists(path):
				count_existing += 1
				self.menulist.append(imdb_show(title, path, "Exist", "", title))
			else:
				count_na += 1
				self.menulist.append(imdb_show(title, path, "N/A", "", title))

		if self.menulist:
			self["menulist"].l.setList(self.menulist)
			self["menulist"].l.setItemHeight(28)
			self.check = "true"
			self.showInfo()
			self["done_msg"].setText(("Total: %s - Exist: %s - N/A: %s") % (self.count_movies, count_existing, count_na))

	def setShowSearchSiteName(self):
		if config.EMC.imdb.search.value == "0":
			self.showSearchSiteName = "IMDB"
			print 'set to: %s' % self.showSearchSiteName
		elif config.EMC.imdb.search.value == "1":
			self.showSearchSiteName = "TMDb"
			print 'set to: %s' % self.showSearchSiteName
		elif config.EMC.imdb.search.value == "2":
			self.showSearchSiteName = "OFDB"
			print 'set to: %s' % self.showSearchSiteName
		elif config.EMC.imdb.search.value == "3":
			self.showSearchSiteName = "CSFD"
			print "set to: %s" % self.showSearchSiteName
		else:
			self.showSearchSiteName = "IMDB"
			print "set to: %s" % self.showSearchSiteName

	def showInfo(self):
		if self.check == "true":
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			#m_real_title = self["menulist"].getCurrent()[0][2]
			m_genre = self["menulist"].getCurrent()[0][3]
			#m_o_title = self["menulist"].getCurrent()[0][4]
			if os.path.exists(m_poster_path):
				DelayedFunction(500, self.poster_resize(m_poster_path))
			else:
				DelayedFunction(500, self.poster_resize(self.no_image_poster))

			self["m_info"].setText(m_title)

	def no_cover(self):
		if os.path.exists(self.no_image_poster):
			DelayedFunction(500, self.poster_resize(self.no_image_poster))

	def imdb(self):
		if self.running == "true":
			print "EMC iMDB: Search already Running."

		elif self.running == "false":
			print "EMC iMDB: Search started..."
			self["done_msg"].show()
			self.no_cover()
			self.running = "true"
			self.counter = 0
			self.counter2 = 0
			self.counter3 = 0
			self.counter_download = 0
			self.counter_exist = 0
			self.counter_no_poster = 0
			self.t_elapsed = 0
			self.menulist = []
			self.count_movies = len(self.m_list)
			self["exist"].setText(_("Exist: %s") % "0")
			self["no_poster"].setText(_("No Cover: %s") % "0")
			self["download"].setText(_("Download: %s") % "0")
			self["done_msg"].setText(_("Searching..."))
			self.counter_a = 0
			self.starttime = 0
			self.t_start_time = time.clock()
			self.s_supertime = time.time()
			self.cm_list = self.m_list[:]
			self.search_list = []
			self.exist_list = []
			self.check = "false"
			self["done_msg"].setText(_("Creating Search List.."))
			for each in sorted(self.cm_list):
				(title, path) = each
				path = re.sub(self.file_format + "$", '.jpg', path)
				if os.path.exists(path):
					self.counter2 += 1
					print "EMC iMDB: Cover vorhanden - %s" % title
					self.display_exist(title, path)
				else:
					elem2 = (title, path)
					self.search_list.append(elem2)

			#print "exist:", self.exist_list
			#print "search:", self.search_list
			self.imdb_start()

	def imdb_start(self):
		self["done_msg"].setText(_("Searching.."))
		self.starttime = time.time()
		self.run10 = "false"
		for i in xrange(10):
			#if self.search_list:
			if not len(self.search_list) == 0:
				(title, path) = self.search_list.pop()
				self.start_time = time.clock()

				if config.EMC.imdb.search.value == "0":
					self.name = title.replace(' ','.').replace(':','.').replace('..','.')
					path = re.sub(self.file_format + "$", '.jpg', path)
					search_title = self.name.replace('.',' ')

					if not os.path.exists(path):
						self.counter3 += 1
						url = "http://www.imdbapi.com/?t=" + self.name.replace('Ã¶','%F6').replace(' ','%20').replace('.','%20')
						print "EMC imdbapi.com:", url
						getPage(url, timeout = 10).addCallback(self.imdbapi, search_title, path).addErrback(self.errorLoad, search_title)

				if config.EMC.imdb.search.value == "1":
					self.name = title.replace(' ','+').replace(':','+').replace('-','').replace('++','+')
					path = re.sub(self.file_format + "$", '.jpg', path)
					search_title = self.name.replace('+',' ')

					if not os.path.exists(path):
						self.counter3 += 1
						url = "http://api.themoviedb.org/2.1/Movie.search/de/xml/8789cfd3fbab7dccf1269c3d7d867aff/" + self.name
						print "EMC themoviedb.org:", url
						getPage(url, timeout = 10).addCallback(self.themoviedb, search_title, path).addErrback(self.errorLoad, search_title)

				if config.EMC.imdb.search.value == "2":
					self.name = title.replace(' ','+').replace(':','+').replace('-','').replace('++','+')
					path = re.sub(self.file_format + "$", '.jpg', path)
					search_title = self.name.replace('+',' ')

					if not os.path.exists(path):
						self.counter3 += 1
						url = "http://ofdbgw.home-of-root.de/search/%s" % self.name
						#url = "http://ofdbgw.home-of-root.de/search/" + self.name
						print "EMC ofdb.de:", url				
						getPage(url).addCallback(self.ofdb_search, search_title, path).addErrback(self.errorLoad, search_title)

				if config.EMC.imdb.search.value == "3":
					self.name = title.replace(':', ' ').replace('-', ' ').replace('++', '+')
					path = re.sub(self.file_format + "$", '.jpg', path)
					search_title = urllib.quote(self.name.replace('+', ' '))

					if not os.path.exists(path):
						self.counter3 += 1
						url = "http://www.csfd.cz/hledat/?q=%s" % search_title
						print "EMC csfd.cz:", url				
						getPage(url).addCallback(self.csfd_search, self.name, path).addErrback(self.errorLoad, self.name)

			else:
				print "EMC iMDB: MovieList is empty, search is DONE. - BREAK..."
				#self.e_supertime = time.time()
				#total_movie = self.counter3 + self.counter2 
				#total_time = self.e_supertime - self.s_supertime
				#avg = (total_time / total_movie)
				#self.done = _("%s Filme in %.1f sec gefunden. Avg. Speed: %.1f sec") % (total_movie, total_time, avg) 
				#self["done_msg"].setText(self.done)
				#self.running = "false"
				break

	def csfd_search(self, data, search_title, path):
		if self.search_list and self.run10 == "false":
			#and self.counter_a % 10 == 0:
			print "EMC iMDB - csfd: 10sec. DelayFunction gestatet"
			DelayedFunction(10000 - int(time.time() - self.starttime) + 100, boundFunction(self.imdb_start))
			self.display_delay()
			self.run10 = "true"

		if re.match('.*?Error 503 Service Unavailable|.*?500 Internal Server Error', data, re.S):
			print "EMC iMDB - csfd 1 : CSFD.cz is down or No results found - %s" % search_title
			self.display_na(search_title, path)
		else:
			movie_search = re.findall('<img src=\"(//img.csfd.cz/files/images/film/posters/.*?)\".*?<h3 class="subject"><a href=.*?class="film c.">(.*?)</a>.*?</li>', data, re.DOTALL | re.IGNORECASE)
			if movie_search:
				poster_url = "http:" + movie_search[0][0]
				movie_title = movie_search[0][1]
				print "EMC csfd: Download - movie_title: ", movie_title, poster_url
				print "EMC csfd: Download", search_title, poster_url
				#os.system("wget %s -O '%s'" % (poster_url, path))
				urllib.urlretrieve(poster_url, path)
				if os.path.exists(path):
					self.display_download(movie_title, search_title, path)
				else:
					print "EMC iMDB - csfd: Film gefunden aber kein poster vorhanden - %s" % search_title
					self.display_na(search_title, path)
			else:
				movie_search = re.findall('<img src=\"(//img.csfd.cz/files/images/film/posters/.*?)" alt="poster"', data, re.DOTALL | re.IGNORECASE)
				if movie_search:
					title_s = re.findall('<title>(.*?)\|', data, re.S)
					if title_s:
						movie_title = title_s[0]
					else:
						movie_title = search_title
					poster_url = "http:" + movie_search[0]
					print "EMC csfd: Download - movie_title: ", movie_title, poster_url
					print "EMC csfd: Download", search_title, poster_url
					#os.system("wget %s -O '%s'" % (poster_url, path))
					urllib.urlretrieve(poster_url, path)
					if os.path.exists(path):
						self.display_download(movie_title, search_title, path)
					else:
						print "EMC iMDB - csfd 3 : CSFD.cz is down or No results found - %s" % search_title
						self.display_na(search_title, path)
				else:
					print "EMC iMDB - csfd 2 : CSFD.cz is down or No results found - %s" % search_title
					self.display_na(search_title, path)
		self['menulist'].l.setList(self.menulist)
		self['menulist'].l.setItemHeight(28)

	def ofdb_search(self, data, search_title, path):
		if self.search_list and self.run10 == "false":
			#and self.counter_a % 10 == 0:
			print "EMC iMDB: 10sec. DelayFunction gestatet"
			DelayedFunction(10000 - int(time.time() - self.starttime) + 100, boundFunction(self.imdb_start))
			self.display_delay()
			self.run10 = "true"

		if re.match('.*?<rcodedesc>Ok.*?', data, re.S):
			bild = re.findall('<bild>(.*?)</bild', data)
			movie_title = re.findall('<titel>(.*?)</titel>', data)
			if bild:
				if bild[0] == "http://img.ofdb.de/film/na.gif":
					print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
					self.display_na(search_title, path)
				else:
					#os.system("wget %s -O '%s'" % (bild[0], path))
					urllib.urlretrieve(bild[0], path)
					if os.path.exists(path):
						self.display_download(movie_title[0], search_title, path)
					else:
						print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
						self.display_na(search_title, path)
			else:
				print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
				self.display_na(search_title, path)
		else:
			print "EMC iMDB: ofdb.de is down or No results found - %s" % search_title
			self.display_na(search_title, path)

	def themoviedb(self, data, search_title, path):
		if self.search_list and self.run10 == "false":
			#and self.counter_a % 10 == 0:
			print "EMC iMDB: 10sec. DelayFunction gestatet"
			DelayedFunction(10000 - int(time.time() - self.starttime) + 100, boundFunction(self.imdb_start))
			self.display_delay()
			self.run10 = "true"
		### Parsing infos from data ###
		if re.match('.*?<movies>Nothing found.</movies>|.*?<opensearch:totalResults>0</opensearch:totalResults>|.*?Error 503 Service Unavailable|.*?500 Internal Server Error', data, re.S):
			print "EMC iMDB: Themoviedb.org is down or No results found - %s" % search_title
			self.display_na(search_title, path)
		else:
			movie_title = re.findall('<name>(.*?)</name>', data)
			poster_url = re.findall('<image type="poster" url="(.*?)" size="cover"', data)
			if poster_url:
				print "EMC themoviedb: Download", search_title, poster_url[0]
				### Cover Download ###

				### download durch urllib
				#urllib._urlopener = AppURLopener()
				#urllib.urlretrieve(poster_url[0], path)
				#urllib.urlcleanup()

				### download durch wget
				#os.system("wget %s -O '%s'" % (poster_url[0], path))
				urllib.urlretrieve(poster_url[0], path)
				if os.path.exists(path):
					self.display_download(movie_title[0], search_title, path)
				else:
					print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
					self.display_na(search_title, path)
			else:
				print "EMC iMDB: Themoviedb.org is down or No results found - %s" % search_title
				self.display_na(search_title, path)

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)

	def imdbapi(self, data, search_title, path):
		self.counter_a += 1
		if self.search_list and self.run10 == "false":
			#and self.counter_a % 10 == 0:
			print "EMC iMDB: 10sec. DelayFunction gestatet"
			self.display_delay()
			DelayedFunction(10000 - int(time.time() - self.starttime) + 100, boundFunction(self.imdb_start))
			self.run10 = "true"
		
		### Parsing infos from data ###
		if re.match('.*?"Response":"True"', data):
			movie_name = re.findall('"Title":"(.*?)"."Year":"(.*?)"', data)
			movie_title = str(movie_name[0][0]) + " " + str(movie_name[0][1])
			poster_url = re.findall('"Poster":"(.*?)"', data)
			if poster_url[0] == "N/A":
				print "EMC iMDB: theimdbapi.com is down or No results found - %s" % search_title
				self.display_na(search_title, path)
			else:
				print "EMC iMDB: theimdbapi.com Download", search_title, poster_url[0]
				### Cover Download ###

				### download durch urlib
				#urllib._urlopener = AppURLopener()
				#urllib.urlretrieve(poster_url[0], path)
				#urllib.urlcleanup()

				### twisted downloadPage part
				#downloadPage(poster_url[0], path).addCallback(self.download_file, movie_title, search_title, path).addErrback(self.errorLoad)

				### download durch wget
				#os.system("wget %s -O '%s'" % (poster_url[0], path))
				urllib.urlretrieve(poster_url[0], path)
				if os.path.exists(path):
					self.display_download(movie_title, search_title, path)
				else:
					print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % search_title
					self.display_na(search_title, path)

		elif re.match('.*?"Response":"Parse Error"', data):
			print "EMC iMDB: theimdbapi.com is down or No results found - %s" % search_title
			self.display_na(search_title, path)

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)

### twisted downloadPage part
#	def download_file(self, string, movie_title, search_title, path):
#		print "doooowwwwnnnloD:", path
#		if os.path.exists(path):
#			self.display_download(movie_title, search_title, path)
#		else:
#			print "EMC iMDB: Film gefunden aber kein poster vorhanden - %s" % path
#			self.display_na(search_title, path)

	def errorLoad(self, error, search_title):
		print "keine daten zu %s gefunden." % search_title
		#print "Please report: %s" % str(error)     

	def display_na(self, search_title, path):
		self.counter += 1
		self.counter_no_poster = self.counter_no_poster + 1
		self.count = ("%s: %s von %s") % (self.showSearchSiteName, self.counter, self.count_movies)
		self["info"].setText(self.count)
		self["m_info"].setText(search_title)
		self["no_poster"].setText(_("No Cover: %s") % str(self.counter_no_poster))
		self.menulist.append(imdb_show(search_title, path, "N/A", "", search_title))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		if self.count_movies == self.counter:
			self.check = "true"
			self.init_ende()

	def display_exist(self, search_title, path):
		self.counter += 1
		self.counter_exist = self.counter_exist + 1
		self.count = ("%s: %s von %s") % (self.showSearchSiteName, self.counter, self.count_movies)
		self["info"].setText(self.count)
		self["m_info"].setText(search_title)
		self["exist"].setText(_("Exist: %s") % str(self.counter_exist))
		self.menulist.append(imdb_show(search_title, path, _("Exist"), "", search_title))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		if self.count_movies == self.counter:
			self.check = "true"
			self.init_ende()

	def display_download(self, movie_title, search_title, path):
		self.counter += 1
		self.counter_download = self.counter_download + 1
		self.end_time = time.clock()
		elapsed = (self.end_time - self.start_time) * 10
		self.count = ("%s: %s von %s") % (self.showSearchSiteName, self.counter, self.count_movies)
		self["info"].setText(self.count)
		self["m_info"].setText(movie_title)
		self["download"].setText(_("Download: %s") % str(self.counter_download))
		self.menulist.append(imdb_show(movie_title, path, str(elapsed), "", search_title))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		if self.count_movies == self.counter:
			self.check = "true"
			self.init_ende()

	def init_ende(self):
		print "EMC iMDB: MovieList is empty, search is DONE."
		self.e_supertime = time.time()
		total_movie = self.counter3 + self.counter2
		total_time = self.e_supertime - self.s_supertime
		avg = (total_time / total_movie)
		self.done = ("%s movies in %.1f sec found. Avg. Speed: %.1f sec.") % (total_movie, total_time, avg)
		self["done_msg"].setText(self.done)
		self.running = "false"

	def display_delay(self):
		self["done_msg"].setText(_("Delay of 10 sec. due the search flooding.."))
		
	def exit(self):
		if self.picload:
			del self.picload
		self.check = "false"
		self.close()

	def red(self):
		if self.check == "true":
			m_poster_path = self["menulist"].getCurrent()[0][1]
			if os.path.exists(m_poster_path):
				if m_poster_path == self.no_image_poster:
					print "no_poster.jpg kann nicht geloescht werden."
				else:
					os.remove(m_poster_path)
					self.verwaltung()
					self.no_cover()
					self["done_msg"].setText(_("%s removed.") % m_poster_path)

	def redLong(self):
		pass

	def ok(self):
		if self.check == "true" and self.menulist:
			data_list = []
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			print m_poster_path
			data_list = [(m_title, m_poster_path)]
			self.session.openWithCallback(self.setupFinished2, getCover, data_list)

	### Cover resize ###
	def poster_resize(self, poster_path):
		self["poster"].instance.setPixmap(None)
		self["poster"].hide()
		sc = AVSwitch().getFramebufferScale() # Maybe save during init
		size = self["poster"].instance.size()
		if self.picload:
			self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background dynamically
			#self.picload.startDecode(poster_path)
			if self.picload.startDecode(poster_path, 0, 0, False) == 0:
				#def showCoverCallback(self, picInfo=None):
				#if picInfo:
				ptr = self.picload.getData()
				if ptr != None:
					print "anzeigen"
					self["poster"].instance.setPixmap(ptr)
					self["poster"].show()
				else:
					print "nicht angezeigt"
		
	def config(self):
		self.session.openWithCallback(self.setupFinished, imdbSetup)

	def setupFinished(self, result):
		print "EMC iMDB Config Saved."
		if result:
			self["done_msg"].show()
			self.setShowSearchSiteName()
			print "was ist settteeedd:", self.showSearchSiteName
			self.showInfo()
			self["done_msg"].setText(_("Search site set to: %s" % self.showSearchSiteName))
			#DelayedFunction(3000, self["done_msg"].hide)

	def setupFinished2(self, result):
		print "EMC iMDB single search done."
		if result:
			self.verwaltung()
			#self.showInfo()
			self["done_msg"].show()
			self["done_msg"].setText("Cover is Saved.")
			#DelayedFunction(3000, self["done_msg"].hide)

class imdbSetup(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="550,400" title="EMC Cover search setup" >
			<widget name="config" position="20,10" size="510,330" scrollbarMode="showOnDemand" />
			<widget name="key_red" position="0,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="#ffffff" font="Regular;18"/>
			<widget name="key_green" position="140,350" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="#ffffff" font="Regular;18"/>
			<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="140,350" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))

		self.list = []
		self.list.append(getConfigListEntry(_("Search Site:"), config.EMC.imdb.search))
		self.list.append(getConfigListEntry(_("Single Search:"), config.EMC.imdb.singlesearch))
		ConfigListScreen.__init__(self, self.list, session)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green":	self.keySave,
			"cancel":	self.keyClose,
			"ok":		self.keySave,
		}, -2)

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close(True)

	def keyClose(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False)

class getCover(Screen):
	if getDesktop(0).size().width() == 1280:
		skin = """
			<screen position="center,center" size="1000,560" title="EMC Cover Selecter" >
				<widget name="poster" zPosition="2" position="10,10" size="185,230" alphatest="on" />
				<widget name="menulist" position="220,10" size="760,507" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/cursor.png" scrollbarMode="showOnDemand" transparent="1" enableWrapAround="on" />
				<widget name="info" position="10,535" size="990,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
			</screen>"""
	else:
		skin = """			
			<screen position="center,center" size="620,500" title="EMC Cover Selecter" >
				<widget name="poster" zPosition="2" position="5,10" size="115,150" alphatest="on" />
				<widget name="menulist" position="125,10" size="490,422" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/cursor.png" scrollbarMode="showOnDemand" transparent="1" enableWrapAround="on" />
				<widget name="info" position="10,460" size="605,21" zPosition="0" font="Regular;20" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="#000000"/>
			</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, data)

		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":	self.exit,
			#"green":	self.keySave,
			#"cancel":	self.keyClose,
			"EMCOK":	self.ok,
		}, -1)

		(title, o_path) = data.pop()
		self.title = title
		self.o_path = o_path
		self.menulist = []
		self["menulist"] = imdblist([])
		self["poster"] = Pixmap()
		self["info"] = Label(_("Searching for %s") % self.title)
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.check = "false"
		self.path = "/tmp/tmp.jpg"
		self.cover_count = 0
		self.search_check = 0
		self.einzel_start_time = time.clock()
		
		self.picload = ePicLoad()
		#self.picload.PictureData.get().append(self.showCoverCallback)
		
		if config.EMC.imdb.singlesearch.value == "0":
			self.searchCover(self.title)
			#self.search_done()
		
		if config.EMC.imdb.singlesearch.value == "1":
			self.searchtvdb(self.title)
			#self.search_done()
		
		if config.EMC.imdb.singlesearch.value == "2":
			self.searchcsfd(self.title)
			#self.search_done()
		
		if config.EMC.imdb.singlesearch.value == "3":
			self.searchcsfd(self.title)
			self.searchtvdb(self.title)
			self.searchCover(self.title)
			#self.search_done()
			#self.check = "true"
			#self.showInfo()
			#self.einzel_end_time = time.clock()
			#self.einzel_elapsed = (self.einzel_end_time - self.einzel_start_time)
			#self["info"].setText(_("found %s covers in %.1f sec") % (self.cover_count, self.einzel_elapsed))

	def searchcsfd_detail(self, url, title):
		getPage(url).addCallback(self.showCovers_detail_csfd, title).addErrback(self.errorLoad, title)

	def showCovers_detail_csfd(self, data, title):
		title_s = re.findall('<title>(.*?)\|', data, re.S)
		if title_s:
			csfd_title = title_s[0]
			print "EMC csfd: Movie found - %s" % csfd_title
		else:
			csfd_title = title
		bild = re.findall('<img src="(//img.csfd.cz/files/images/film/posters/.*?)" alt="poster"', data, re.DOTALL | re.IGNORECASE)
		if bild:
			print "EMC csfd: Cover Select - %s" % title
			self.cover_count = self.cover_count + 1
			csfd_url = "http:" + bild[0].replace('\\','').strip()
			print "csfd_url: %s" % csfd_url
			self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
			bild = re.findall('<h3>Plak.*?ty</h3>(.*?)</table>', data, re.S)
			if bild:
				bild1 = re.findall('style=\"background-image\: url\(\'(.*?)\'\)\;', bild[0], re.DOTALL | re.IGNORECASE)
				if bild1:
					for each in bild1:
						print "EMC csfd: Cover Select - %s" % title
						self.cover_count = self.cover_count + 1
						csfd_url = "http:" + each.replace('\\','').strip()
						print "csfd_url: %s" % csfd_url
						self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
				else:
					print "EMC csfd 3 : no else covers - %s" % title
			else:
				print "EMC csfd 2 : no else covers - %s" % title
		else:
			print "EMC csfd 1 : keine infos gefunden - %s" % title

	def searchcsfd(self, title):
		search_title = urllib.quote(title.replace('+', ' ').replace('-', ' '))
		url = "http://www.csfd.cz/hledat/?q=%s" % search_title
		getPage(url).addCallback(self.showCovers_csfd, title).addErrback(self.errorLoad, title)

	def showCovers_csfd(self, data, title):
		bild = re.findall('<img src=\"(//img.csfd.cz/files/images/film/posters/.*?)\".*?<h3 class="subject"><a href="(.*?)" class="film c.">(.*?)</a>.*?</li>', data, re.DOTALL | re.IGNORECASE)
		if bild:
			for each in bild:
				print "EMC csfd: Cover Select - %s" % title
				self.cover_count = self.cover_count + 1
				csfd_title = each[2]
				csfd_detail_url = "http://www.csfd.cz" + each[1]
				print "csfd_detail_url: %s" % csfd_detail_url
				csfd_url = "http:" + each[0]
				print "csfd_url: %s" % csfd_url
				self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, 'csfd: '))
				self.searchcsfd_detail(csfd_detail_url, csfd_title)
		else:
			title_s = re.findall('<title>(.*?)\|', data, re.S)
			if title_s:
				csfd_title = title_s[0]
				print "EMC iMDB csfd: Movie found - %s" % csfd_title
			else:
				csfd_title = title
			bild = re.findall('<img src="(//img.csfd.cz/files/images/film/posters/.*?)" alt="poster"', data, re.DOTALL | re.IGNORECASE)
			if bild:
				print "EMC iMDB csfd: Cover Select - %s" % title
				self.cover_count = self.cover_count + 1
				csfd_url = "http:" + bild[0].replace('\\','').strip()
				print "csfd_url: %s" % csfd_url
				self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
				bild = re.findall('<h3>Plak.*?ty</h3>(.*?)</table>', data, re.S)
				if bild:
					bild1 = re.findall('style=\"background-image\: url\(\'(.*?)\'\)\;', bild[0], re.DOTALL | re.IGNORECASE)
					if bild1:
						for each in bild1:
							print "EMC iMDB - csfd: Cover Select - %s" % title
							self.cover_count = self.cover_count + 1
							csfd_url = "http:" + each.replace('\\','').strip()
							print "csfd_url: %s" % csfd_url
							self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
					else:
						print "EMC iMDB csfd 3 : no else covers - %s" % title
				else:
					print "EMC iMDB csfd 2 : no else covers - %s" % title
			else:
				print "EMC iMDB csfd 1 : keine infos gefunden - %s" % title

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		self.search_check += 1
		if not config.EMC.imdb.singlesearch.value == "3":		
			self.check = "true"
			self.showInfo()
			self.einzel_end_time = time.clock()
			self.einzel_elapsed = self.einzel_end_time - self.einzel_start_time
			self["info"].setText(("found %s covers in %.1f sec") % (self.cover_count, self.einzel_elapsed))

	def searchtvdb(self, title):
		url = "http://www.thetvdb.com/api/GetSeries.php?seriesname=%s&language=de" % title.replace(' ','+')
		getPage(url).addCallback(self.parsetvdb, title).addErrback(self.errorLoad, title)

	def parsetvdb(self, data, title):
		id = re.findall('<id>(.*?)</id>', data)
		if id:
			url = "http://www.thetvdb.com/api/2AAF0562E31BCEEC/series/%s/" % id[0]
			getPage(url).addCallback(self.showCovers_tvdb, title).addErrback(self.errorLoad, title)

	def showCovers_tvdb(self, data, title):
		bild = re.findall('<poster>(.*?)</poster>', data)
		if bild:
			print "EMB iMDB: Cover Select - %s" % title
			self.cover_count = self.cover_count + 1
			print "http://www.thetvdb.com/banners/_cache/%s" % bild[0]
			tvdb_url = "http://www.thetvdb.com/banners/_cache/%s" % bild[0]
			print "bild:", tvdb_url
			self.menulist.append(showCoverlist(title, tvdb_url, self.o_path, "tvdb: "))
		else:
			#self["info"].setText(_("Nothing found for %s") % title)
			print "EMC iMDB tvdb: keine infos gefunden - %s" % title

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		self.search_check += 1 
		if not config.EMC.imdb.singlesearch.value == "3":		
			self.check = "true"
			self.showInfo()
			self.einzel_end_time = time.clock()
			self.einzel_elapsed = (self.einzel_end_time - self.einzel_start_time)
			self["info"].setText(("found %s covers in %.1f sec") % (self.cover_count, self.einzel_elapsed))

	def searchCover(self, title):
		print title
		url = "http://m.imdb.com/find?q=%s" % title.replace(' ','+')
		getPage(url).addCallback(self.showCovers, title).addErrback(self.errorLoad, title)

	def showCovers(self, data, title):
		print "EMB iMDB: Cover Select - %s" % title
		#print data
		bild = re.findall('<img src="http://ia.media-imdb.com/images/(.*?)".*?<a href="/title/(.*?)/".*?">(.*?)</a>.*?\((.*?)\)', data, re.S)
		if bild:
			for each in bild:
				#print self.cover_count
				self.cover_count = self.cover_count + 1
				imdb_title = each[2]
				imdb_url = each[0]
				imdb_url = re.findall('(.*?)\.', imdb_url)
				extra_imdb_convert = "._V1_SX320.jpg"
				imdb_url = "http://ia.media-imdb.com/images/%s%s" % (imdb_url[0], extra_imdb_convert)

				self.menulist.append(showCoverlist(imdb_title, imdb_url, self.o_path, "imdb: "))
		else:
			self["info"].setText(_("Nothing found for %s") % title)
			print "EMC iMDB: keine infos gefunden - %s" % title

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		self.search_check += 1

		#if not config.EMC.imdb.singlesearch.value == "3":
		self.check = "true"
		self.showInfo()
		self.einzel_end_time = time.clock()
		self.einzel_elapsed = (self.einzel_end_time - self.einzel_start_time)
		self["info"].setText(("found %s covers in %.1f sec") % (self.cover_count, self.einzel_elapsed))

	def errorLoad(self, error, title):
		print "keine daten zu %s gefunden." % title
		print error

	def search_done(self):
		#if self.search_check == "2":
		self.check = "true"
		self.showInfo()
		self.einzel_end_time = time.clock()
		self.einzel_elapsed = (self.einzel_end_time - self.einzel_start_time)
		self["info"].setText(("found %s covers in %.1f sec") % (self.cover_count, self.einzel_elapsed))

	def showInfo(self):
		if self.check == "true" and self.menulist:
			m_title = self["menulist"].getCurrent()[0][0]
			m_url = self["menulist"].getCurrent()[0][1]
			print m_title, m_url
			if m_url:
				#m_url = re.findall('(.*?)\.', m_url)
				#extra_imdb_convert = "._V1_SX320.jpg"
				#m_url = "http://ia.media-imdb.com/images/%s%s" % (m_url[0], extra_imdb_convert)
				print "EMC iMDB: Download Poster - %s" % m_url
				urllib._urlopener = AppURLopener()
				urllib.urlretrieve(m_url, self.path)
				urllib.urlcleanup()
				if os.path.exists(self.path):
					self.poster_resize(self.path, m_title)
					
					#ptr = LoadPixmap(self.path)
					#if ptr is None:
					#        ptr = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png")
					#        print "EMC iMDB: Load default NO Poster."
					#if ptr is not None:
					#        self["poster"].instance.setPixmap(ptr)
					#        print "EMC iMDB: Load Poster - %s" % m_title
				else:
					print "EMC iMDB: No url found for - %s" % m_title
			else:
				print "EMC iMDB: No url found for - %s" % m_title

	def poster_resize(self, poster_path, m_title):
		self.m_title = m_title
		self["poster"].instance.setPixmap(None)
		self["poster"].hide()
		sc = AVSwitch().getFramebufferScale() # Maybe save during init
		size = self["poster"].instance.size()
		if self.picload:
			self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background dynamically
			#self.picload.startDecode(poster_path)
			if self.picload.startDecode(poster_path, 0, 0, False) == 0:
				#def showCoverCallback(self, picInfo=None):
				#if picInfo:
				ptr = self.picload.getData()
				if ptr != None:
					print "EMC iMDB: Load Poster - %s" % self.m_title
					self["poster"].instance.setPixmap(ptr)
					self["poster"].show()

	def exit(self):
		if self.picload:
			del self.picload
		self.check = "false"
		self.close(False)

	def ok(self):
		if self.check == "true" and self.menulist:
			shutil.move(self.path, self.o_path)
			print "EMC iMDB: mv poster to real path - %s %s" % (self.path, self.o_path) 
			self.check = "false"
			self.close(True)
