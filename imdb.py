# -*- coding: utf-8 -*-
from Components.ActionMap import *
from Components.Label import Label
from Components.MenuList import MenuList

from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from enigma import ePicLoad
from Components.AVSwitch import AVSwitch
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Tools.Directories import fileExists
from Screens.Menu import boundFunction
from Components.PluginComponent import plugins

from Components.Button import Button

from twisted.web.client import getPage

from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, RT_WRAP, eServiceReference
from enigma import getDesktop
from enigma import loadJPG

import re, urllib, urllib2, os, time

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
	elapsed = "%s ms." % elapsed
	res.append(MultiContentEntryText(pos=(0, 0), size=(450, 24), font=4, text=search_title, flags=RT_HALIGN_LEFT))
	res.append(MultiContentEntryText(pos=(460, 0), size=(100, 24), font=4, text=elapsed, flags=RT_HALIGN_LEFT))
	return res

class imdbscan(Screen):
	if getDesktop(0).size().width() == 1280:
		skin = """
			<screen position="center,center" size="800,550" title="EMC iMDB">
				<widget name="menulist" position="220,100" size="572,450" scrollbarMode="showOnDemand" transparent="1"/>
				<widget name="info" position="0,0" size="800,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="poster" zPosition="2" position="20,40" size="170,230" alphatest="blend" />
				<widget name="m_info" position="200,40" size="400,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="genre" position="200,64" size="400,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="done_msg" position="0,500" size="790,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="ButtonGreen" pixmap="skin_default/buttons/key_green.png" position="21,300" zPosition="10" size="35,25" transparent="1" alphatest="on" />
				<widget name="ButtonGreenText" position="65,300" size="300,22" valign="center" halign="left" zPosition="10" font="Regular;20" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="720,500" title="EMC iMDB">
				<widget name="menulist" position="10,10" size="710,380" scrollbarMode="showOnDemand" />
			</screen>"""

	def __init__(self, session, args=0):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		#self["actions"] = HelpableActionMap(self, "sjActions",
		{
			"cancel":		self.exit,
			"green":		self.imdb,

		}, -1)

		self["ButtonGreen"] = Pixmap()
		self["ButtonGreenText"] = Label(_("Start"))
		self["poster"] = Pixmap()
		self.menulist = []
		self["menulist"] = imdblist([])
		self["info"] = Label("")
		self["m_info"] = Label("")
		self["genre"] = Label("")
		self["done_msg"] = Label("")
		self["info"].setText("Um die Suche zu starten, drück bitte die Gruene-Taste")

		self["menulist"].onSelectionChanged.append(self.showInfo)
		#self.onLayoutFinish.append(self.showInfo)
		self.check = "false"
		print data

	def showInfo(self):
		if self.check == "true":
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			m_real_title = self["menulist"].getCurrent()[0][2]
			m_genre = self["menulist"].getCurrent()[0][3]
			m_o_title = self["menulist"].getCurrent()[0][4]
			self.poster_resize(m_poster_path)
			self["m_info"].setText(m_title)
			self["genre"].setText(m_genre)

	### Liste umwandeln und title weitergeben zur imdb suche ###
	def imdb(self):
		#klon = self["list"].list
		#print klon
		self.counter = 0
		self.t_elapsed = 0
		self.menulist = []
		m_list = [["superman", "/home/root/", "saw.ts"], ["alice im wunderland", "/home/root/", "saw.ts"], ["greek", "/home/root/", "saw.ts"], ["saw 4", "/home/root/", "saw.ts"], ["saw", "/home/root/", "saw.ts"], ["sex and the city tv", "/tmp/", "sex and the city.ts"], ["final destination", "/tmp/", "final destination.st"], ["star wars", "/tmp/", "star wars.ts"], ["saw 2", "/home/root/", "saw 2.ts"], ["Terminator", "/home/root/", "terminator.ts"], ["Mad Men", "/home/root/", "Mad Men.ts"]]
		self.count_movies = len(m_list)

		for each in m_list:
        		self.name = each[0].replace(' ','%')
        		self.path = each[1]
			self.o_title = each[2]
			self.start_time = time.clock()
			self.t_start_time = time.clock()

			url = "http://www.imdbapi.com/?t=" + self.name
			print "EMC iMDB:", url
			search_title = self.name.replace('%',' ')
			getPage(url).addCallback(self._gotPageLoadFrameSearch, search_title).addErrback(self.errorLoad)

	def _gotPageLoadFrameSearch(self, data, search_title):
		self.check = "false"
		### Zeitmessung ###
		self.counter = self.counter + 1
		self.end_time = time.clock()
                self.t_end_time = time.clock()
                elapsed = (self.end_time - self.start_time) * 10
		print (self.end_time - self.start_time)
		self.t_elapsed = self.t_elapsed + elapsed
		
		count = "Film: " + str(self.counter) + " von " + str(self.count_movies) + "       Took: " + str(elapsed) + " ms" + "       Total Time: " + str(self.t_elapsed) + " ms"

		### Parsing infos from data ###
		poster_url = re.findall('"Poster":"(.*?)"', data)
		poster_jpg= poster_url[0].replace('http://ia.media-imdb.com/images/M/','')
		
		movie_name = re.findall('"Title":"(.*?)"."Year":"(.*?)"', data)
		movie_title = str(movie_name[0][0]) + " " + str(movie_name[0][1])

		got_genre = re.findall('"Genre":"(.*?)"', data)
		genre = "(%s)" % got_genre[0]

		### Downloading Cover mit file exist check ###
	        poster_path = "/tmp/" + poster_jpg
		if not os.path.exists(poster_path):
			print "EMC iMDB: Download", poster_url[0]
			urllib._urlopener = AppURLopener()
			urllib.urlretrieve(poster_url[0], poster_path)
			urllib.urlcleanup()

		### Uebergabe zum screen ###
		if os.path.exists(poster_path):
			self["info"].setText(count)
			self["m_info"].setText(movie_title)
			self["genre"].setText(genre)
			self.menulist.append(imdb_show(movie_title, poster_path, str(elapsed), genre, search_title))
		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)
		self.check = "true"
		avg = self.t_elapsed / self.counter
		print avg
		done = "%s Filme in %s ms gefunden. Durchschnittsgeschwindigkeit: %.1f ms" % (str(self.counter), str(self.t_elapsed), int(avg))
		self["done_msg"].setText(done)

	def errorLoad(self, error):
		print "Please report: %s" % str(error)

	def exit(self):
		self.check = "false"
		self.close()

	### Cover resize ###
	def poster_resize(self, poster_path):
		self["poster"].hide()
		sc = AVSwitch().getFramebufferScale() # Maybe save during init
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.showCoverCallback)
		size = self["poster"].instance.size()
		self.picload.setPara((size.width(), size.height(), sc[0], sc[1], False, 1, "#00000000")) # Background dynamically
		self.picload.startDecode(poster_path)

	def showCoverCallback(self, picInfo=None):
                if picInfo:
                        ptr = self.picload.getData()
                        if ptr != None:
                                print "anzeigen"
                                self["poster"].instance.setPixmap(ptr)
                                self["poster"].show()
