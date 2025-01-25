#! /bin/bash

#sleep 30

while true
do
	source /home/pluto/Projects/.venv/bin/activate
	#/home/pluto/.local/bin/gphotos-sync /home/pluto/gphotos/som --progress --rescan --retry-download
	/home/pluto/Projects/.venv/bin/gphotos-sync /home/pluto/gphotos/som --progress --rescan --retry-download
	echo "Pass" > /home/pluto/Projects/gphotos/gphotos.txt
	sleep 3600
done
