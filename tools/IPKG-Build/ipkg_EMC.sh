#!/bin/sh

echo "Kopiere Plugin Enhanced Movie Center nach /tmp/temp/"
mkdir -p /tmp/temp/usr/lib/enigma2/python/Plugins/Extensions/
cp -r /usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/ /tmp/temp/usr/lib/enigma2/python/Plugins/Extensions/

echo "Kopiere Converter nach /tmp/temp/"
mkdir -p /tmp/temp/usr/lib/enigma2/python/Components/Converter/
cp -r /usr/lib/enigma2/python/Components/Converter/EMCClockToText.py /tmp/temp/usr/lib/enigma2/python/Components/Converter/
cp -r /usr/lib/enigma2/python/Components/Converter/EMCEventName.py /tmp/temp/usr/lib/enigma2/python/Components/Converter/
cp -r /usr/lib/enigma2/python/Components/Converter/EMCServicePosition.py /tmp/temp/usr/lib/enigma2/python/Components/Converter/
cp -r /usr/lib/enigma2/python/Components/Converter/EMCServiceTime.py /tmp/temp/usr/lib/enigma2/python/Components/Converter/
cp -r /usr/lib/enigma2/python/Components/Converter/EMCMovieInfo.py /tmp/temp/usr/lib/enigma2/python/Components/Converter/
cp -r /usr/lib/enigma2/python/Components/Converter/EMCRecordPosition.py /tmp/temp/usr/lib/enigma2/python/Components/Converter/

echo "Kopiere Renderer nach /tmp/temp/"
mkdir -p /tmp/temp/usr/lib/enigma2/python/Components/Renderer/
cp -r /usr/lib/enigma2/python/Components/Renderer/EMCPositionGauge.py /tmp/temp/usr/lib/enigma2/python/Components/Renderer/

echo "Kopiere Sources nach /tmp/temp/"
mkdir -p /tmp/temp/usr/lib/enigma2/python/Components/Sources/
cp -r /usr/lib/enigma2/python/Components/Sources/EMCCurrentService.py /tmp/temp/usr/lib/enigma2/python/Components/Sources/
cp -r /usr/lib/enigma2/python/Components/Sources/EMCServiceEvent.py /tmp/temp/usr/lib/enigma2/python/Components/Sources/

echo "Kopiere Config Dateien aus /etc/enigma2/ nach /tmp/temp/"
mkdir -p /tmp/temp/etc/enigma2/
cp -r /etc/enigma2/emc-hide.cfg /tmp/temp/etc/enigma2/
cp -r /etc/enigma2/emc-noscan.cfg /tmp/temp/etc/enigma2/
cp -r /etc/enigma2/emc-permsort.cfg /tmp/temp/etc/enigma2/
cp -r /etc/enigma2/emc-topdir.cfg /tmp/temp/etc/enigma2/

echo "Lösche alle *.pyo unter /tmp/temp/"
rm -r /tmp/temp/usr/lib/enigma2/python/Plugins/Extensions/EnhancedMovieCenter/*.pyo

echo "Kopiere control Daten nach /tmp/temp/"
cp -r /media/USB-Extension/ipk/EMC/CONTROL/ /tmp/temp/

echo "IPKG erstellung läuft...."
sh ipkg-build.sh /tmp/temp/ /tmp
echo "IPKG erstellt unter /tmp/"