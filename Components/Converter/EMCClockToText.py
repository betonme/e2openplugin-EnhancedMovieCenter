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
			if config.osd.language.value == "de_DE":
				return strftime("%A, %d. %B %Y", t)
			else:
				return strftime("%A %B %d, %Y", t)
		elif self.type == self.FORMAT:
			spos = self.fmt_string.find('%')
			if spos > -1:
				s1 = self.fmt_string[:spos]
				s2 = strftime(self.fmt_string[spos:], t)
				return str(s1 + s2)
			else:
				return strftime(self.fmt_string, t)
		else:
			return "???"

	text = property(getText)
