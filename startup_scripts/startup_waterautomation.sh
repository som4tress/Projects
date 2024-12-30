#! /bin/bash

echo "Disabling ufw"
sudo ufw disable

echo "Waiting for 30 sseconds before launching Home Light Automation"
sleep 30

source /home/pluto/Projects/.venv/bin/activate
cd /home/pluto/Projects/WaterMeterAutomation
while true; do echo "Launching Water Monitoring Automation"; /home/pluto/Projects/.venv/bin/python3 WaterMeterAutomation.py; sleep 30; done
