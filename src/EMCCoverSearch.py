# -*- coding: utf-8 -*-
# mod by einfall (09.11.2014)
# change to themoviedb.org / thetvdb.com - Api

from __init__ import _

from Components.ActionMap import *
from Components.Label import Label
from Components.MenuList import MenuList

from Components.MultiContent import MultiContentEntryText
from Components.Pixmap import Pixmap
from enigma import ePicLoad, gPixmapPtr
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
from twisted.internet import defer

from Components.config import *
from Components.ConfigList import *

from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, RT_WRAP, eServiceReference
from enigma import getDesktop
from enigma import loadJPG

from Tools.BoundFunction import boundFunction
from DelayedFunction import DelayedFunction
from time import time

from MovieCenter import getMovieNameWithoutExt, getMovieNameWithoutPhrases

import re, urllib, urllib2, os, time, shutil

config.EMC.imdb = ConfigSubsection()
config.EMC.imdb.search = ConfigSelection(default='1', choices=[('1', _('themoviedb.org'))])
config.EMC.imdb.singlesearch = ConfigSelection(default='0', choices=[('0', _('imdb.de')), ('1', _('thetvdb.com')), ('2', _('csfd.cz')), ('3', _('all'))])
config.EMC.imdb.themoviedb_coversize = ConfigSelection(default="w185", choices = ["w92", "w185", "w500", "original"])
config.EMC.imdb.savetotxtfile = ConfigYesNo(default = False)

try:
	from enigma import eMediaDatabase
	is7080hd = True
except:
	try:
		file = open("/proc/stb/info/model", "r")
		dev = file.readline().strip()
		file.close()
		if dev == "dm7080":
			is7080hd = True
		else:
			is7080hd = False
	except:
			is7080hd = False

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
	s1=_("Exist") + "|" + _("N/A")
	if not re.match('.*?(' + s1 + ')', elapsed):
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
				<widget name="Manage Cover" position="50,425" size="300,22" font="Regular;21" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="10,453" size="30,30" alphatest="on" />
				<widget name="ButtonRedText" position="50,460" size="300,22" valign="center" halign="left" zPosition="1" font="Regular;20" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_menu.png" position="10,495" size="35,25" alphatest="on" />
				<widget name="Setup" position="50,498" size="300,22" font="Regular;21" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_ok.png" position="10,530" size="35,25" alphatest="on" />
				<widget name="Single search" position="50,533" size="300,22" font="Regular;21" halign="left" valign="center" transparent="1" />
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
				<widget name="Manage Cover" position="45,382" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key-red.png" position="5,412" size="30,25" alphatest="on" />
				<widget name="ButtonRedText" position="45,412" size="300,25" valign="center" halign="left" zPosition="1" font="Regular;18" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_menu.png" position="5,442" size="35,25" alphatest="on" />
				<widget name="Setup" position="45,442" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/key_ok.png" position="5,472" size="35,25" alphatest="on" />
				<widget name="Single search" position="45,472" size="300,25" font="Regular;18" halign="left" valign="center" transparent="1" />
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
			"EMCYellow":	self.verwaltung,
			"EMCRedLong":	self.redLong,
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
		self["Manage Cover"] = Label(_("Manage Cover"))
		self["Setup"] = Label(_("Setup"))
		self["Single search"] = Label(_("Single search"))
		self.no_image_poster = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.png"
		self.check = False
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.running = False

		self.picload = ePicLoad()
		#self.picload_conn = self.picload.PictureData.connect(self.showCoverCallback)
		self.file_format = "(.ts|.avi|.mkv|.divx|.f4v|.flv|.img|.iso|.m2ts|.m4v|.mov|.mp4|.mpeg|.mpg|.mts|.vob|.wmv)"
		self.onLayoutFinish.append(self.layoutFinished)

		self.setShowSearchSiteName()

	def layoutFinished(self):
		self.setTitle(_("EMC Cover search"))

	def verwaltung(self):
		self.menulist = []
		self.count_movies = len(self.m_list)
		self.vm_list = self.m_list[:]
		count_existing = 0
		count_na = 0

		for each in sorted(self.vm_list):
			(title, path) = each
			title = getMovieNameWithoutPhrases(getMovieNameWithoutExt(title))
			path = re.sub(self.file_format + "$", '.jpg', path)
			if os.path.exists(path):
				count_existing += 1
				self.menulist.append(imdb_show(title, path, _("Exist"), "", title))
			else:
				count_na += 1
				self.menulist.append(imdb_show(title, path, _("N/A"), "", title))

		if self.menulist:
			self["menulist"].l.setList(self.menulist)
			self["menulist"].l.setItemHeight(28)
			self.check = True
			self.showInfo()
			self["done_msg"].setText((_("Total") + ": %s - " + _("Exist") + ": %s - " + _("N/A") + ": %s") % (self.count_movies, count_existing, count_na))

	def setShowSearchSiteName(self):
		if config.EMC.imdb.search.value == "0":
			self.showSearchSiteName = "IMDB"
			print 'EMC set to: %s' % self.showSearchSiteName
		elif config.EMC.imdb.search.value == "1":
			self.showSearchSiteName = "TMDb"
			print 'EMC set to: %s' % self.showSearchSiteName
		elif config.EMC.imdb.search.value == "2":
			self.showSearchSiteName = "OFDB"
			print 'EMC set to: %s' % self.showSearchSiteName
		elif config.EMC.imdb.search.value == "3":
			self.showSearchSiteName = "CSFD"
			print "EMC set to: %s" % self.showSearchSiteName
		else:
			self.showSearchSiteName = "IMDB"
			print "EMC set to: %s" % self.showSearchSiteName

	def showInfo(self):
		check = self["menulist"].getCurrent()
		if check == None:
			return
		if self.check:
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
		if self.running:
			print "EMC iMDB: Search already Running."

		elif not self.running:
			print "EMC iMDB: Search started..."
			self["done_msg"].show()
			self.no_cover()
			self.running = True
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
			self.starttime = 0
			self.t_start_time = time.clock()
			self.s_supertime = time.time()
			self.cm_list = self.m_list[:]
			self.search_list = []
			self.exist_list = []
			self.check = False
			self["done_msg"].setText(_("Creating Search List.."))
			self.counting = 0
			self.count_total = len(self.cm_list)
			urls = []
			for each in sorted(self.cm_list):
				(title, path) = each
				cover_path = re.sub(self.file_format + "$", '.jpg', path)
				if os.path.exists(cover_path):
					self.counter_exist += 1
					self.counting += 1
					self.menulist.append(imdb_show(title, cover_path, _("Exist"), "", title))
					self["m_info"].setText(title)
					self["no_poster"].setText(_("No Cover: %s") % str(self.counter_no_poster))
					self["exist"].setText(_("Exist: %s") % str(self.counter_exist))
					self["download"].setText(_("Download: %s") % str(self.counter_download))
					self["menulist"].l.setList(self.menulist)
					self["menulist"].l.setItemHeight(28)
					self.check = True
					print "EMC iMDB: Cover vorhanden - %s" % title
				else:
					filename = path
					title = getMovieNameWithoutPhrases(getMovieNameWithoutExt(title))
					if re.search('[Ss][0-9]+[Ee][0-9]+', title) is not None:
						season = None
						episode = None
						seasonEpisode = re.findall('.*?[Ss]([0-9]+)[Ee]([0-9]+)', title, re.S|re.I)
						if seasonEpisode:
							(season, episode) = seasonEpisode[0]
						name2 = re.sub('[Ss][0-9]+[Ee][0-9]+.*[a-zA-Z0-9_]+','', title, flags=re.S|re.I)
						url = 'http://thetvdb.com/api/GetSeries.php?seriesname=%s&language=de' % name2.replace(' ','%20')
						urls.append(("serie", title, url, cover_path, season, episode))
					else:
						url = 'http://api.themoviedb.org/3/search/movie?api_key=8789cfd3fbab7dccf1269c3d7d867aff&query=%s&language=de' % title.replace(' ','%20')
						urls.append(("movie", title, url, cover_path, None, None))

			if len(urls) != 0:
				ds = defer.DeferredSemaphore(tokens=2)
				downloads = [ds.run(self.download, url).addCallback(self.parseWebpage, type, title, url, cover_path, season, episode).addErrback(self.dataError) for type, title, url, cover_path, season, episode in urls]
				finished = defer.DeferredList(downloads).addErrback(self.dataError2)
			else:
				self["done_msg"].setText(_("No Movies found!"))

	def download(self, url):
		return getPage(url, timeout=20, headers={'Accept': 'application/json'})

	def parseWebpage(self, data, type, title, url, cover_path, season, episode):
		self.counting += 1
		self.start_time = time.clock()
		if type == "movie":
			list = []
			list = re.findall('original_title":"(.*?)".*?"poster_path":"(.*?)"', data, re.S)
			if list:
				purl = "http://image.tmdb.org/t/p/%s%s" % (config.EMC.imdb.themoviedb_coversize.value, list[0][1])
				self.counter_download += 1
				self.end_time = time.clock()
				elapsed = (self.end_time - self.start_time) * 10
				self.menulist.append(imdb_show(title, cover_path, str(elapsed), "", title))
				if not fileExists(cover_path):
					downloadPage(purl, cover_path).addErrback(self.dataError)
			else:
				self.counter_no_poster += 1
				self.menulist.append(imdb_show(title, cover_path, _("N/A"), "", title))

			# get description
			if config.EMC.imdb.savetotxtfile.value:
				idx = []
				idx = re.findall('"id":(.*?),', data, re.S)
				if idx:
					iurl = "http://api.themoviedb.org/3/movie/%s?api_key=8789cfd3fbab7dccf1269c3d7d867aff&language=de" % idx[0]
					getPage(iurl, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getInfos, id, type, cover_path).addErrback(self.dataError)

		elif type == "serie":
			list = []
			list = re.findall('<seriesid>(.*?)</seriesid>', data, re.S)
			if list:
				purl = "http://www.thetvdb.com/banners/_cache/posters/%s-1.jpg" % list[0]
				#self.guilist.append(((cleanTitle, True, filename),))
				self.counter_download += 1
				self.end_time = time.clock()
				elapsed = (self.end_time - self.start_time) * 10
				self.menulist.append(imdb_show(title, cover_path, str(elapsed), "", title))
				if not fileExists(cover_path):
					downloadPage(purl, cover_path).addErrback(self.dataError)

				# get description
				if config.EMC.imdb.savetotxtfile.value:
					if season and episode:
						iurl = "http://www.thetvdb.com/api/2AAF0562E31BCEEC/series/%s/default/%s/%s/de.xml" % (list[0], str(int(season)), str(int(episode)))
						getPage(iurl, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.getInfos, id, type, cover_path).addErrback(self.dataError)
			else:
				self.counter_no_poster += 1
				self.menulist.append(imdb_show(title, cover_path, _("N/A"), "", title))

		self.count = ("%s: %s " + _("from") + " %s") % (self.showSearchSiteName, self.counting, self.count_total)
		self["info"].setText(self.count)
		self["no_poster"].setText(_("No Cover: %s") % str(self.counter_no_poster))
		self["exist"].setText(_("Exist: %s") % str(self.counter_exist))
		self["download"].setText(_("Download: %s") % str(self.counter_download))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		self.check = True

		if self.counting == self.count_total:
			self.e_supertime = time.time()
			total_time = self.e_supertime - self.s_supertime
			avg = (total_time / self.count_total)
			self.done = ("%s " + _("movies in") + " %.1f " + _("sec found. Avg. Speed:") + " %.1f " + _("sec.")) % (self.count_total, total_time, avg)
			self["done_msg"].setText(self.done)
			self.running = False

	def getInfos(self, data, id, type, cover_path):
		if type == "movie":
			infos = re.findall('"genres":\[(.*?)\].*?"overview":"(.*?)"', data, re.S)
			if infos:
				(genres, desc) = infos[0]
				self.writeTofile(self.decodeHtml(desc), cover_path)

		elif type == "serie":
			infos = re.findall('<Overview>(.*?)</Overview>', data, re.S)
			if infos:
				desc = infos[0]
				self.writeTofile(self.decodeHtml(desc), cover_path)

	def writeTofile(self, text, cover_path):
		print cover_path
		if not fileExists(cover_path.replace('.jpg','.txt')):
			wFile = open(cover_path.replace('.jpg','.txt'),"w") 
			wFile.write(text) 
			wFile.close()

	def dataError(self, error):
		print "ERROR:", error

	def dataError2(self, error):
		self.counting = int(self.counting) + 1
		print "ERROR:", error

	def errorLoad(self, error, search_title):
		print "EMC keine daten zu %s gefunden." % search_title
		#print "Please report: %s" % str(error)
		
	def exit(self):
		self.check = False
		if self.picload:
			del self.picload
		self.close()

	def red(self):
		if self.check:
			m_poster_path = self["menulist"].getCurrent()[0][1]
			if os.path.exists(m_poster_path):
				if m_poster_path == self.no_image_poster:
					print "EMC no_poster.jpg kann nicht geloescht werden."
				else:
					os.remove(m_poster_path)
					self.verwaltung()
					self.no_cover()
					self["done_msg"].setText(_("%s removed.") % m_poster_path)

	def redLong(self):
		pass

	def ok(self):
		if self.check and self.menulist:
			data_list = []
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			data_list = [(m_title, m_poster_path)]
			self.session.openWithCallback(self.setupFinished2, getCover, data_list)

	### Cover resize ###
	def poster_resize(self, poster_path):
		if fileExists(poster_path):
			self["poster"].instance.setPixmap(gPixmapPtr())
			scale = AVSwitch().getFramebufferScale()
			size = self["poster"].instance.size()
			self.picload.setPara((size.width(), size.height(), scale[0], scale[1], False, 1, "#00000000"))
			if is7080hd:
				if self.picload.startDecode(poster_path, False) == 0:
					ptr = self.picload.getData()
					if ptr != None:
						self["poster"].instance.setPixmap(ptr)
						self["poster"].show()
			else:
				if self.picload.startDecode(poster_path, 0, 0, False) == 0:
					ptr = self.picload.getData()
					if ptr != None:
						self["poster"].instance.setPixmap(ptr)
						self["poster"].show()
		
	def config(self):
		self.session.openWithCallback(self.setupFinished, imdbSetup)

	def setupFinished(self, result):
		print "EMC iMDB Config Saved."
		if result:
			self["done_msg"].show()
			self.setShowSearchSiteName()
			print "EMC was ist settteeedd:", self.showSearchSiteName
			self.showInfo()
			self["done_msg"].setText(_("Search site set to: %s") % (self.showSearchSiteName))
			#DelayedFunction(3000, self["done_msg"].hide)

	def setupFinished2(self, result):
		print "EMC iMDB single search done."
		if result:
			self.verwaltung()
			#self.showInfo()
			self["done_msg"].show()
			self["done_msg"].setText("Cover is Saved.")
			#DelayedFunction(3000, self["done_msg"].hide)

	def decodeHtml(self, text):
		text = text.replace('&auml;','ä')
		text = text.replace('\u00e4','ä')
		text = text.replace('&#228;','ä')

		text = text.replace('&Auml;','Ä')
		text = text.replace('\u00c4','Ä')
		text = text.replace('&#196;','Ä')

		text = text.replace('&ouml;','ö')
		text = text.replace('\u00f6','ö')
		text = text.replace('&#246;','ö')

		text = text.replace('&ouml;','Ö')
		text = text.replace('&Ouml;','Ö')
		text = text.replace('\u00d6','Ö')
		text = text.replace('&#214;','Ö')

		text = text.replace('&uuml;','ü')
		text = text.replace('\u00fc','ü')
		text = text.replace('&#252;','ü')

		text = text.replace('&Uuml;','Ü')
		text = text.replace('\u00dc','Ü')
		text = text.replace('&#220;','Ü')

		text = text.replace('&szlig;','ß')
		text = text.replace('\u00df','ß')
		text = text.replace('&#223;','ß')

		text = text.replace('&amp;','&')
		text = text.replace('&quot;','\"')
		text = text.replace('&gt;','>')
		text = text.replace('&apos;',"'")
		text = text.replace('&acute;','\'')
		text = text.replace('&ndash;','-')
		text = text.replace('&bdquo;','"')
		text = text.replace('&rdquo;','"')
		text = text.replace('&ldquo;','"')
		text = text.replace('&lsquo;','\'')
		text = text.replace('&rsquo;','\'')
		text = text.replace('&#034;','"')
		text = text.replace('&#34;','"')
		text = text.replace('&#038;','&')
		text = text.replace('&#039;','\'')
		text = text.replace('&#39;','\'')
		text = text.replace('&#160;',' ')
		text = text.replace('\u00a0',' ')
		text = text.replace('\u00b4','\'')
		text = text.replace('\u003d','=')
		text = text.replace('\u0026','&')
		text = text.replace('&#174;','')
		text = text.replace('&#225;','a')
		text = text.replace('&#233;','e')
		text = text.replace('&#243;','o')
		text = text.replace('&#8211;',"-")
		text = text.replace('&#8212;',"—")
		text = text.replace('&mdash;','—')
		text = text.replace('\u2013',"–")
		text = text.replace('&#8216;',"'")
		text = text.replace('&#8217;',"'")
		text = text.replace('&#8220;',"'")
		text = text.replace('&#8221;','"')
		text = text.replace('&#8222;',',')
		text = text.replace('\u014d','ō')
		text = text.replace('\u016b','ū')
		text = text.replace('\u201a','\"')
		text = text.replace('\u2018','\"')
		text = text.replace('\u201e','\"')
		text = text.replace('\u201c','\"')
		text = text.replace('\u201d','\'')
		text = text.replace('\u2019s','’')
		text = text.replace('\u00e0','à')
		text = text.replace('\u00e7','ç')
		text = text.replace('\u00e8','é')
		text = text.replace('\u00e9','é')
		text = text.replace('\u00c1','Á')
		text = text.replace('\u00c6','Æ')
		text = text.replace('\u00e1','á')

		text = text.replace('&#xC4;','Ä')
		text = text.replace('&#xD6;','Ö')
		text = text.replace('&#xDC;','Ü')
		text = text.replace('&#xE4;','ä')
		text = text.replace('&#xF6;','ö')
		text = text.replace('&#xFC;','ü')
		text = text.replace('&#xDF;','ß')
		text = text.replace('&#xE9;','é')
		text = text.replace('&#xB7;','·')
		text = text.replace("&#x27;","'")
		text = text.replace("&#x26;","&")
		text = text.replace("&#xFB;","û")
		text = text.replace("&#xF8;","ø")
		text = text.replace("&#x21;","!")
		text = text.replace("&#x3f;","?")

		text = text.replace('&#8230;','...')
		text = text.replace('\u2026','...')
		text = text.replace('&hellip;','...')

		text = text.replace('&#8234;','')
		return text

	def cleanFile(text):
		cutlist = ['x264','720p','1080p','1080i','PAL','GERMAN','ENGLiSH','WS','DVDRiP','UNRATED','RETAIL','Web-DL','DL','LD','MiC','MD','DVDR','BDRiP','BLURAY','DTS','UNCUT','ANiME',
					'AC3MD','AC3','AC3D','TS','DVDSCR','COMPLETE','INTERNAL','DTSD','XViD','DIVX','DUBBED','LINE.DUBBED','DD51','DVDR9','DVDR5','h264','AVC',
					'WEBHDTVRiP','WEBHDRiP','WEBRiP','WEBHDTV','WebHD','HDTVRiP','HDRiP','HDTV','ITUNESHD','REPACK','SYNC']
		text = text.replace('.wmv','').replace('.flv','').replace('.ts','').replace('.m2ts','').replace('.mkv','').replace('.avi','').replace('.mpeg','').replace('.mpg','').replace('.iso','')
		
		for word in cutlist:
			text = re.sub('(\_|\-|\.|\+)'+word+'(\_|\-|\.|\+)','+', text, flags=re.I)
		text = text.replace('.',' ').replace('-',' ').replace('_',' ').replace('+','')

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
		self.list.append(getConfigListEntry(_("themoviedb cover resolution:"), config.EMC.imdb.themoviedb_coversize))
		self.list.append(getConfigListEntry(_("Save description to movie.txt file:"), config.EMC.imdb.savetotxtfile))
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
		configfile.save()
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
		self.einzel_start_time = time.clock()
		self.einzel_elapsed = time.clock()
		self.einzel_end_time = time.clock()

		self.picload = ePicLoad()
		#self.picload_conn = self.picload.PictureData.connect(self.showCoverCallback)

		self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		if config.EMC.imdb.singlesearch.value == "0":
			self.searchCover(self.title)
		elif config.EMC.imdb.singlesearch.value == "1":
			self.searchtvdb(self.title)
		elif config.EMC.imdb.singlesearch.value == "2":
			self.searchcsfd(self.title)
		elif config.EMC.imdb.singlesearch.value == "3":
			self.searchcsfd(self.title)
			self.searchtvdb(self.title)
			self.searchCover(self.title)

	def showCovers_adddetail_csfd(self, data, title):
		title_s = re.findall('<title>(.*?)\|', data, re.S)
		if title_s:
			if title_s[0] != "Vyhled\xc3\xa1v\xc3\xa1n\xc3\xad ":
				csfd_title = title_s[0]
			else:
				csfd_title = title
			print "EMC csfd: Movie name - %s" % csfd_title
		else:
			csfd_title = title
		bild = re.findall('<img src="(//img.csfd.cz/files/images/film/posters/.*?|//img.csfd.cz/posters/.*?)" alt="poster"', data, re.DOTALL | re.IGNORECASE)
		if bild:
			print "EMC csfd: Cover Select - %s" % title
			self.cover_count = self.cover_count + 1
			csfd_url = "http:" + bild[0].replace('\\','').strip()
			self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
			self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
			bild = re.findall('<h3>Plak.*?ty</h3>(.*?)</table>', data, re.S)
			if bild:
				bild1 = re.findall('style=\"background-image\: url\(\'(.*?)\'\)\;', bild[0], re.DOTALL | re.IGNORECASE)
				if bild1:
					for each in bild1:
						print "EMC csfd: Cover Select - %s" % title
						self.cover_count = self.cover_count + 1
						csfd_url = "http:" + each.replace('\\','').strip()
						self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, "csfd: "))
						self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
				else:
					print "EMC csfd 3 : no else covers - %s" % title
			else:
				print "EMC csfd 2 : no else covers - %s" % title
		else:
			print "EMC csfd 1 : keine infos gefunden - %s" % title

	@defer.inlineCallbacks
	def searchcsfd(self, title):
		print "EMC csfd - searchcsfd: ", title
		search_title = urllib.quote(title.replace('+', ' ').replace('-', ' '))
		url = "http://www.csfd.cz/hledat/?q=%s" % search_title
		data = yield getPage(url).addErrback(self.errorLoad, title)
		bild = re.findall('<img src=\"(//img.csfd.cz/files/images/film/posters/.*?|//img.csfd.cz/posters/.*?)\".*?<h3 class="subject"><a href="(.*?)" class="film c.">(.*?)</a>.*?</li>', data, re.DOTALL | re.IGNORECASE)
		if bild:
			for each in bild:
				print "EMC csfd: Cover Select - %s" % title
				self.cover_count = self.cover_count + 1
				csfd_title = each[2]
				csfd_detail_url = "http://www.csfd.cz" + each[1]
				csfd_url = "http:" + each[0]
				self.menulist.append(showCoverlist(csfd_title, csfd_url, self.o_path, 'csfd: '))
				data1 = yield getPage(csfd_detail_url).addErrback(self.errorLoad, csfd_title)
				self.showCovers_adddetail_csfd(data1, csfd_title)
				self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		else:
			self.showCovers_adddetail_csfd(data, title)
			self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		self.search_done()

	@defer.inlineCallbacks
	def searchtvdb(self, title):
		url = "http://www.thetvdb.com/api/GetSeries.php?seriesname=%s&language=de" % title.replace(' ','+')
		data = yield getPage(url).addErrback(self.errorLoad, title)
		id = re.findall('<id>(.*?)</id>', data)
		if id:
			url = "http://www.thetvdb.com/api/2AAF0562E31BCEEC/series/%s/" % id[0]
			data = yield getPage(url).addErrback(self.errorLoad, title)
			bild = re.findall('<poster>(.*?)</poster>', data)
			if bild:
				print "EMB iMDB: Cover Select - %s" % title
				self.cover_count = self.cover_count + 1
				print "EMC http://www.thetvdb.com/banners/_cache/%s" % bild[0]
				tvdb_url = "http://www.thetvdb.com/banners/_cache/%s" % bild[0]
				self.menulist.append(showCoverlist(title, tvdb_url, self.o_path, "tvdb: "))
				self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
			else:
				#self["info"].setText(_("Nothing found for %s") % title)
				print "EMC iMDB tvdb: keine infos gefunden - %s" % title
		self.search_done()

	@defer.inlineCallbacks
	def searchCover(self, title):
		url = "http://m.imdb.com/find?q=%s" % title.replace(' ','+')
		data = yield getPage(url).addErrback(self.errorLoad, title)
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
				self["info"].setText((_("found") + " %s " + _("covers")) % (self.cover_count))
		else:
			print "EMC iMDB: keine infos gefunden - %s" % title
		self.search_done()

	def errorLoad(self, error, title):
		print "EMC keine daten zu %s gefunden." % title
		print error

	def search_done(self):
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(28)
		self.check = "true"
		self.showInfo()
		self.einzel_end_time = time.clock()
		self.einzel_elapsed = (self.einzel_end_time - self.einzel_start_time)
		self["info"].setText((_("found") + " %s " + _("covers in") + " %.1f " + _("sec")) % (self.cover_count, self.einzel_elapsed))

	def showInfo(self):
		if self.check == "true" and self.menulist:
			m_title = self["menulist"].getCurrent()[0][0]
			m_url = self["menulist"].getCurrent()[0][1]
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
		self["poster"].instance.setPixmap(gPixmapPtr())
		self["poster"].hide()
		sc = AVSwitch().getFramebufferScale() # Maybe save during init
		size = self["poster"].instance.size()
		if self.picload:
			self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background dynamically
			#self.picload.startDecode(poster_path)
			if not is7080hd:
				result = self.picload.startDecode(poster_path, 0, 0, False)
			else:
				result = self.picload.startDecode(poster_path, False)
			if result == 0:
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
