#! /bin/bash

echo "Disabling ufw"
sudo ufw disable

echo "Waiting for 30 seconds before launching Blink Automation"
sleep 30

#source /home/pluto/blinkpy/blinkpy/bin/activate
source /home/pluto/Projects/.venv/bin/activate
cd /home/pluto/Projects/BlinkAutomation/
while true; do echo "Launching Blink Automation"; /home/pluto/Projects/.venv/bin/python3 BlinkAutomation.py; sleep 30; done
