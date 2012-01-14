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
	if not re.match('.*?(Exist|N/A)', elapsed):
		print "nicht:", elapsed
		elapsed = "%s ms." % elapsed
	res.append(MultiContentEntryText(pos=(0, 0), size=(510, 24), font=4, text=search_title, flags=RT_HALIGN_LEFT))
	res.append(MultiContentEntryText(pos=(500, 0), size=(172, 24), font=4, text=elapsed, flags=RT_HALIGN_LEFT))
	return res

class imdbscan(Screen):
	if getDesktop(0).size().width() == 1280:
		skin = """
			<screen position="center,center" size="900,560" title="EMC iMDB">
				<widget name="menulist" position="220,100" size="672,408" scrollbarMode="showOnDemand" transparent="1"/>
				<widget name="info" position="0,0" size="900,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="poster" zPosition="2" position="20,40" size="170,230" alphatest="blend" />
				<widget name="m_info" position="200,40" size="700,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="download" position="10,398" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="exist" position="10,350" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="no_poster" position="10,374" size="200,24" zPosition="0" font="Regular;21" halign="left" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="genre" position="200,64" size="700,24" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="done_msg" position="0,512" size="840,48" zPosition="0" font="Regular;21" halign="center" valign="center" transparent="1" foregroundColor="#ffffff" backgroundColor="black"/>
				<widget name="ButtonGreen" pixmap="skin_default/buttons/key_green.png" position="21,300" zPosition="10" size="35,25" transparent="1" alphatest="on" />
				<widget name="ButtonGreenText" position="65,300" size="300,22" valign="center" halign="left" zPosition="10" font="Regular;20" transparent="1" />
				<widget name="ButtonRed" pixmap="skin_default/buttons/key_red.png" position="21,460" zPosition="10" size="35,25" transparent="1" alphatest="on" />
				<widget name="ButtonRedText" position="65,460" size="300,22" valign="center" halign="left" zPosition="10" font="Regular;20" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="720,500" title="EMC iMDB">
				<widget name="menulist" position="10,10" size="710,380" scrollbarMode="showOnDemand" />
			</screen>"""

	def __init__(self, session, data):
		Screen.__init__(self, session, data)
		self.m_list = data
		self["actions"] = HelpableActionMap(self, "EMCimdb",
		{
			"EMCEXIT":		self.exit,
			"EMCOK":                self.ok,
			"EMCGreen":		self.imdb,
			"EMCRed":		self.red,

		}, -1)

		self["ButtonGreen"] = Pixmap()
		self["ButtonGreenText"] = Label(_("Start"))
		self["ButtonRed"] = Pixmap()
                self["ButtonRedText"] = Label(_("Loeschen"))

		self["poster"] = Pixmap()
		self.menulist = []
		self["menulist"] = imdblist([])
		self["info"] = Label("")
		self["m_info"] = Label("")
		self["genre"] = Label("")
		self["download"] = Label("")
		self["exist"] = Label("")
		self["no_poster"] = Label("")
		self["done_msg"] = Label("")
		self["info"].setText("Um die Suche zu starten, dr�ck bitte die Gruene-Taste")
		self.no_image_poster = "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.jpg"
		self["menulist"].onSelectionChanged.append(self.showInfo)
		self.check = "false"
		self.running = "false"
		print data

	def showInfo(self):
		if self.check == "true":
			m_title = self["menulist"].getCurrent()[0][0]
			m_poster_path = self["menulist"].getCurrent()[0][1]
			#m_real_title = self["menulist"].getCurrent()[0][2]
			m_genre = self["menulist"].getCurrent()[0][3]
			#m_o_title = self["menulist"].getCurrent()[0][4]
			if os.path.exists(m_poster_path):
				self.poster_resize(m_poster_path)
			else:
				self.poster_resize(self.no_image_poster)
				
			self["m_info"].setText(m_title)
			self["genre"].setText(m_genre)

	def imdb(self):
		if self.running == "true":
			print "Search already Running."
		elif self.running == "false":
			self.imdb_start()

	### Liste umwandeln und title weitergeben zur imdb suche ###
	def imdb_start(self):
		self.running = "true"
		self.counter = 0
		self.counter_download = 0
		self.counter_exist = 0
		self.counter_no_poster = 0
		self.t_elapsed = 0
		self.menulist = []
		self.count_movies = len(self.m_list)
		self.poster_resize(self.no_image_poster)
		self["exist"].setText("Exist: 0")
		self["no_poster"].setText("No Cover: 0")
		self["download"].setText("Download: 0")

		for each in self.m_list:
        		self.name = each[0].replace(' ','.').replace(':','.').replace('..','.')
        		path = each[1]
			path = path.replace('.ts','.jpg')
			self.start_time = time.clock()
			self.t_start_time = time.clock()
			search_title = self.name.replace('.',' ')

			#self._gotPageLoadFrameSearch(data, search_title, path)
			if not os.path.exists(path):
				url = "http://www.imdbapi.com/?t=" + self.name.replace('ö','%F6')
				##replace('ö','%F6')
				print "EMC iMDB:", url
				getPage(url).addCallback(self._gotPageLoadFrameSearch, search_title, path).addErrback(self.errorLoad, search_title)
			else:
				self.check = "false"
				self.counter_exist = self.counter_exist + 1
				self.end_time = time.clock()
                		self.t_end_time = time.clock()
				self.counter = self.counter + 1
                		elapsed = (self.end_time - self.start_time) * 10
                		self.t_elapsed = self.t_elapsed + elapsed
				self.count = "Film: " + str(self.counter) + " von " + str(self.count_movies) + "     Took: " + str(elapsed) + " ms" + "     Total Time: " + str(self.t_elapsed) + " ms"

				self["info"].setText(self.count)
                                self["m_info"].setText(search_title)
                                self["genre"].setText("")
                                self["exist"].setText("Exist: %s" % str(self.counter_exist))
                                self.menulist.append(imdb_show(search_title, path, "Exist", "", search_title))
				self["menulist"].l.setList(self.menulist)
	                	self["menulist"].l.setItemHeight(24)

	def _gotPageLoadFrameSearch(self, data, search_title, path):
		self.check = "false"
		### Zeitmessung ###
		#self.end_time = time.clock()
                #self.t_end_time = time.clock()
                #elapsed = (self.end_time - self.start_time) * 10
		#self.t_elapsed = self.t_elapsed + elapsed
		
		#self.count = "Film: " + str(self.counter) + " von " + str(self.count_movies) + "     Took: " + str(elapsed) + " ms" + "     Total Time: " + str(self.t_elapsed) + " ms"

		### Parsing infos from data ###

		if re.match('.*?"Response":"True"', data):
			movie_name = re.findall('"Title":"(.*?)"."Year":"(.*?)"', data)
			movie_title = str(movie_name[0][0]) + " " + str(movie_name[0][1])

			poster_url = re.findall('"Poster":"(.*?)"', data)

			if poster_url[0] == "N/A":
				print "N/A"
				self.counter = self.counter + 1
				self.counter_no_poster = self.counter_no_poster + 1
				self.end_time = time.clock()
		                self.t_end_time = time.clock()
           			elapsed = (self.end_time - self.start_time) * 10
                		self.t_elapsed = self.t_elapsed + elapsed
				self.count = "Film: " + str(self.counter) + " von " + str(self.count_movies) + "     Took: " + str(elapsed) + " ms" +"     Total Time: " + str(self.t_elapsed) + " ms"

				self["info"].setText(self.count)
                        	self["m_info"].setText(movie_title)
                        	self["genre"].setText("no genre")
				self["no_poster"].setText("No Cover: %s" % str(self.counter_no_poster))
				self.menulist.append(imdb_show(movie_title, self.no_image_poster, "N/A", "", search_title))
				
			else:
				print "EMC iMDB: Download", poster_url[0]

				got_genre = re.findall('"Genre":"(.*?)"', data)
				genre = "(%s)" % got_genre[0]
				
				self.counter = self.counter + 1
				self.counter_download = self.counter_download + 1
				self.end_time = time.clock()
	        	       	self.t_end_time = time.clock()
        		        elapsed = (self.end_time - self.start_time) * 10
                		self.t_elapsed = self.t_elapsed + elapsed
				self.count = "Film: " + str(self.counter) + " von " + str(self.count_movies) + "     Took: " + str(elapsed) + " ms" +"     Total Time: " + str(self.t_elapsed) + " ms"

				urllib._urlopener = AppURLopener()
				urllib.urlretrieve(poster_url[0], path)
				urllib.urlcleanup()
				if os.path.exists(path):
					self["info"].setText(self.count)
					self["m_info"].setText(movie_title)
					self["genre"].setText(genre)
					self["download"].setText("Download: %s" % str(self.counter_download))
					self.menulist.append(imdb_show(movie_title, path, str(elapsed), genre, search_title))

		elif re.match('.*?"Response":"Parse Error"', data):
			print "NOOOOOOOOOOOOOOOOOOOTTTTTT TRUE -", search_title

			self.counter = self.counter + 1
			self.counter_no_poster = self.counter_no_poster + 1
			self.end_time = time.clock()
	                self.t_end_time = time.clock()
        	        elapsed = (self.end_time - self.start_time) * 10
               		self.t_elapsed = self.t_elapsed + elapsed
			self.menulist.append(imdb_show(search_title, self.no_image_poster, "N/A", "", search_title))
			self.count = "Film: " + str(self.counter) + " von " + str(self.count_movies) + "     Took: " + str(elapsed) + " ms" + "     Total Time: " + str(self.t_elapsed) + " ms"
			self["no_poster"].setText("No Cover: %s" % str(self.counter_no_poster))
                        self["info"].setText(self.count)
                       	self["m_info"].setText(search_title)
                        self["genre"].setText("no genre")

		self["menulist"].l.setList(self.menulist)
		self["menulist"].l.setItemHeight(24)
		self.check = "true"
		avg = self.t_elapsed / self.counter
		done = "%s Filme in %s ms gefunden. Avg. Speed: %.1f ms" % (str(self.counter), str(self.t_elapsed), int(avg))
		self["done_msg"].setText(done)
		self.running = "false"
		#self.showInfo()

	def errorLoad(self, error, search_title):
		print "keine daten zu %s gefunden." % search_title
		#print "Please report: %s" % str(error)
		
	def exit(self):
		self.check = "false"
		self.close()

	def red(self):
		if self.check == "true":
			m_poster_path = self["menulist"].getCurrent()[0][1]
			if os.path.exists(m_poster_path):
				if m_poster_path == "/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/img/no_poster.jpg":
					print "no_poster.jpg kann nicht geloescht werden."
				else:
					os.system("rm '%s'" % (m_poster_path))
					done = "%s removed." % m_poster_path
					self["done_msg"].setText(done)
	def ok(self):
		print "ok"

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
