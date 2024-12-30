#! /bin/bash

sleep 30

while true
do
	cd /home/pluto/Projects/gphotos-sync
	/home/pluto/.local/bin/gphotos-sync /home/pluto/gphotos/som --progress --rescan --retry-download
	echo "Pass" > /home/pluto/Projects/gphotos-sync/gphotos.txt
	sleep 3600
done
