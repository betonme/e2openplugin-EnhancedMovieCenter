#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 by Coolman & betonme

from Converter import Converter
from time import localtime, strftime, gmtime
from Components.Element import cached
from Components.config import config

class EMCClockToText(Converter, object):
	DEFAULT = 0
	WITH_SECONDS = 1
	IN_MINUTES = 2
	DATE = 3
	FORMAT = 4
	AS_LENGTH = 5
	TIMESTAMP = 6

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "WithSeconds":
			self.type = self.WITH_SECONDS
		elif type == "InMinutes":
			self.type = self.IN_MINUTES
		elif type == "Date":
			self.type = self.DATE
		elif type == "AsLength":
			self.type = self.AS_LENGTH
		elif type == "Timestamp":
			self.type = self.TIMESTAMP
		elif str(type).find("Format") != -1:
			self.type = self.FORMAT
			self.fmt_string = type[7:]
		else:
			self.type = self.DEFAULT

	@cached
	def getText(self):
		time = self.source.time
		if not time or time > 169735005176 or time < 11:
			return ""

		if self.type == self.IN_MINUTES:
			return "%d min" % (time / 60)
		elif self.type == self.AS_LENGTH:
			return "%d:%02d" % (time / 60, time % 60)
		elif self.type == self.TIMESTAMP:
			return str(time)

		if time > (31 * 24 * 60 * 60):
		# No Recording should be longer than 1 month :-)
			t = localtime(time)
		else:
			t = gmtime(time)

		if self.type == self.WITH_SECONDS:
			return "%2d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec)
		elif self.type == self.DEFAULT:
			return "%02d:%02d" % (t.tm_hour, t.tm_min)
		elif self.type == self.DATE:
			CoolString = "%A %B %d, %Y"
			if config.osd.language.value == "de_DE":
				CoolString = "%A, %d. %B %Y"
				t2 = ["Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"][t.tm_wday]
				m2 = ["Januar","Februar",u"M\xe4rz","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"][t.tm_mon - 1]
				CoolString = CoolString.replace('%A', t2)
				CoolString = CoolString.replace('%B', m2)
			return strftime(CoolString, t)
		elif self.type == self.FORMAT:
			pos = self.fmt_string.find('%')
			apos = self.fmt_string.find('%a')
			Apos = self.fmt_string.find('%A')
			bpos = self.fmt_string.find('%b')
			Bpos = self.fmt_string.find('%B')
			if pos > 0:
				s1 = self.fmt_string[:pos]
				s2 = strftime(self.fmt_string[pos:], t)
				CoolString = str(s1+s2)
				if config.osd.language.value == "de_DE":
					if apos > -1:
						CoolString = CoolString.replace('Mon', 'Mo')
						CoolString = CoolString.replace('Tue', 'Di')
						CoolString = CoolString.replace('Wed', 'Mi')
						CoolString = CoolString.replace('Thu', 'Do')
						CoolString = CoolString.replace('Fri', 'Fr')
						CoolString = CoolString.replace('Sat', 'Sa')
						CoolString = CoolString.replace('Sun', 'So')
					if Apos > -1:
						CoolString = CoolString.replace('Monday', 'Montag')
						CoolString = CoolString.replace('Tuesday', 'Dienstag')
						CoolString = CoolString.replace('Wednesday', 'Mittwoch')
						CoolString = CoolString.replace('Thursday', 'Donnerstag')
						CoolString = CoolString.replace('Friday', 'Freitag')
						CoolString = CoolString.replace('Saturday', 'Samstag')
						CoolString = CoolString.replace('Sunday', 'Sonntag')
					if bpos > -1:
						CoolString = CoolString.replace('Mar', 'Mrz')
						CoolString = CoolString.replace('May', 'Mai')
						CoolString = CoolString.replace('June', 'Jun')
						CoolString = CoolString.replace('July', 'Jul')
						CoolString = CoolString.replace('Sept', 'Sep')
						CoolString = CoolString.replace('Oct', 'Okt')
						CoolString = CoolString.replace('Dec', 'Dez')
					if Bpos > -1:
						CoolString = CoolString.replace('January', 'Januar')
						CoolString = CoolString.replace('February', 'Februar')
						CoolString = CoolString.replace('March', 'März')
						CoolString = CoolString.replace('April', 'April')
						CoolString = CoolString.replace('May', 'Mai')
						CoolString = CoolString.replace('June', 'Juni')
						CoolString = CoolString.replace('July', 'Juli')
						CoolString = CoolString.replace('October', 'Oktober')
						CoolString = CoolString.replace('December', 'Dezember')
				return CoolString
			else:
				CoolString = strftime(self.fmt_string, t)
				if config.osd.language.value == "de_DE":
					if apos > -1:
						CoolString = CoolString.replace('Mon', 'Mo')
						CoolString = CoolString.replace('Tue', 'Di')
						CoolString = CoolString.replace('Wed', 'Mi')
						CoolString = CoolString.replace('Thu', 'Do')
						CoolString = CoolString.replace('Fri', 'Fr')
						CoolString = CoolString.replace('Sat', 'Sa')
						CoolString = CoolString.replace('Sun', 'So')
					if Apos > -1:
						CoolString = CoolString.replace('Monday', 'Montag')
						CoolString = CoolString.replace('Tuesday', 'Dienstag')
						CoolString = CoolString.replace('Wednesday', 'Mittwoch')
						CoolString = CoolString.replace('Thursday', 'Donnerstag')
						CoolString = CoolString.replace('Friday', 'Freitag')
						CoolString = CoolString.replace('Saturday', 'Samstag')
						CoolString = CoolString.replace('Sunday', 'Sonntag')
					if bpos > -1:
						CoolString = CoolString.replace('Mar', 'Mrz')
						CoolString = CoolString.replace('May', 'Mai')
						CoolString = CoolString.replace('June', 'Jun')
						CoolString = CoolString.replace('July', 'Jul')
						CoolString = CoolString.replace('Sept', 'Sep')
						CoolString = CoolString.replace('Oct', 'Okt')
						CoolString = CoolString.replace('Dec', 'Dez')
					if Bpos > -1:
						CoolString = CoolString.replace('January', 'Januar')
						CoolString = CoolString.replace('February', 'Februar')
						CoolString = CoolString.replace('March', 'März')
						CoolString = CoolString.replace('April', 'April')
						CoolString = CoolString.replace('May', 'Mai')
						CoolString = CoolString.replace('June', 'Juni')
						CoolString = CoolString.replace('July', 'Juli')
						CoolString = CoolString.replace('October', 'Oktober')
						CoolString = CoolString.replace('December', 'Dezember')
				return CoolString
		else:
			return "???"

	text = property(getText)