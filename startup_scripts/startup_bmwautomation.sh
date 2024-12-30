#! /bin/bash

echo "Disabling ufw"
sudo ufw disable

echo "Waiting for 30 sseconds before launching Home Light Automation"
sleep 30

source /home/pluto/Projects/.venv/bin/activate
cd /home/pluto/Projects/BMWLockMonitor
while true; do echo "Launching BMW Lock Monitoring Automation"; /home/pluto/Projects/.venv/bin/python3 BMWLockMonitorAutomation.py; sleep 30; done
