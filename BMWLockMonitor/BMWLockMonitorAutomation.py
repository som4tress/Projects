import json
from datetime import date
import datetime
import sys
import os
import time as tm
from homeassistant_api import Client, State
import requests

class BMWLockMonitorWrapper:
    def __init__(self):
        self._curLat = None
        self._curLong = None
        self._curdir = None
        
        self._prevLat = None
        self._prevLong = None
        self._prevdir = None
        
        self._prevTime = None        
        
        self._driving = False
        self._iter = 0
        
        self._logFile = os.environ['PLUTO_HOME_DIR'] + "/BMWLockMonitor/BMWLockMonitorAutomation.log"
        self._logFileHandle = open(self._logFile, 'w')
        # self._logFileHandle = sys.stdout
        
        self._longLivedToken = os.environ["HA_LONG_LIVE_TOKEN"]
        self._HAExternalURL = os.environ["HA_EXTERNAL_API_URL"]
    
    def trigger_home_automation(self, automation_entity_id, data = None):
        url = f"{self._HAExternalURL}/{automation_entity_id}"
        
        headers = {
            "Authorization": f"Bearer {self._longLivedToken}",
            "Content-Type": "application/json"
        }   

        if data:
            response = requests.post(url, headers=headers, json=data, verify=True)
        else:
            response = requests.post(url, headers=headers, verify=True)
            
        if response.status_code == 200:
            print("Automation triggered successfully")
        else:
            print(f"Error triggering automation: {response.text}")
    
    def updateLocation(self):        
        nowtime = tm.time()
        
        try:
            
            client = Client(self._HAExternalURL, self._longLivedToken, use_async=False)
            
            self._curLong = client.get_state(entity_id="device_tracker.x5_xdrive40i").attributes["longitude"]
            self._curLat = client.get_state(entity_id="device_tracker.x5_xdrive40i").attributes["latitude"]
            self._curdir = client.get_state(entity_id="device_tracker.x5_xdrive40i").attributes["direction"]
            print(f"Current Longitude : {self._curLong}", file=self._logFileHandle)
            print(f"Current Latitude : {self._curLat}", file=self._logFileHandle)
            print(f"Current Dir : {self._curdir}", file=self._logFileHandle)
            
            if self._prevTime is None:
                self._prevTime = nowtime
                    
            delta_time = nowtime - self._prevTime
            print(f"Delta Time : {delta_time}", file=self._logFileHandle)
            
            door = client.get_state(entity_id="binary_sensor.x5_xdrive40i_door_lock_state").state
            window = client.get_state(entity_id="binary_sensor.x5_xdrive40i_windows").state
            lids = client.get_state(entity_id="binary_sensor.x5_xdrive40i_lids").state
            print(f"Door State : {door}", file=self._logFileHandle)
            print(f"Window State : {window}", file=self._logFileHandle)
            print(f"Lids State : {lids}", file=self._logFileHandle)
            
            if self._prevLat is None or self._prevLong is None or self._prevdir is None:
                self._prevLat = self._curLat
                self._prevLong = self._curLong
                self._prevdir = self._curdir
                client.set_state(State(state=str(0), entity_id="sensor.x5_xdrive40i_driving", attributes={"driving":0}))
                self._driving = False
            elif self._curLat != self._prevLat or self._curLong != self._prevLong or self._curdir != self._prevdir:
                print("Location changed", file=self._logFileHandle)
                self._driving = True
                client.set_state(State(state=str(1), entity_id="sensor.x5_xdrive40i_driving", attributes={"driving":1}))
                print("Reset time - driving", file=self._logFileHandle)
                self._prevTime = nowtime
                self._prevLat = self._curLat
                self._prevLong = self._curLong
                self._prevdir = self._curdir
            elif self._curLat == self._prevLat and self._curLong == self._prevLong and self._curdir == self._prevdir:  
                print("Location not changed", file=self._logFileHandle)                      
                if delta_time >= 600:
                    print("Car appears to be stationery", file=self._logFileHandle)
                    self._driving = False
                    client.set_state(State(state=str(0), entity_id="sensor.x5_xdrive40i_driving", attributes={"driving":0}))   
                    
                    if (door == "on" or window == "on" or lids == "on"):                    
                        print("Car is not moving and doors etc. seem to be unlocked, trigger notification", file=self._logFileHandle)                
                        msg = ""
                        if door == "on":
                            msg = "Doors Unlocked. "
                        if window == "on":
                            msg += "Windows Open. "
                        if lids == "on":
                            msg += "Lids Open. "
                        
                        event_data = {
                                        "title": "BMW Monitor",
                                        "message": msg,
                                    }                 
                        self.trigger_home_automation("events/my_test_event", data=event_data)
                    
                    print("Reset time - stationery", file=self._logFileHandle)
                    self._prevTime = nowtime                    
        except Exception as e:
            print(f"Error in updateLocation: {e}", file=self._logFileHandle)
        
            
def main():
    bmwWrapper = BMWLockMonitorWrapper()
    
    while True:
        print(datetime.datetime.now(), file=bmwWrapper._logFileHandle)
        print("---------------------------", file=bmwWrapper._logFileHandle)
        
        bmwWrapper.updateLocation()
        
        if bmwWrapper._logFileHandle != sys.stdout:
            bmwWrapper._logFileHandle.flush()
            os.fsync(bmwWrapper._logFileHandle.fileno())
        
        print("---------------------------", file=bmwWrapper._logFileHandle)
        
        tm.sleep(30)
    
if __name__ == "__main__":
    main()