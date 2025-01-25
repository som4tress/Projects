import asyncio
import sys
import os
import time as tm
from flask.cli import F
from homeassistant_api import Client, State
from math import radians, cos, sin, asin, sqrt, atan2

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
        
        # self._logFile = os.environ['PLUTO_HOME_DIR'] + "/BMWLockMonitor/BMWLockMonitorAutomation.log"
        # self._logFileHandle = open(self._logFile, 'w')
        self._logFileHandle = sys.stdout
        
        self._longLivedToken = os.environ["HA_LONG_LIVE_TOKEN"]
        
    def haversine(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 # Radius of earth in kilometers. Use 3956 for miles
        return c * r
    
    def updateLocation(self):
        client = Client("https://som4tress.duckdns.org:8123/api", self._longLivedToken, use_async=False)
        
        self._curLong = client.get_state(entity_id="device_tracker.x5_xdrive40i").attributes["longitude"]
        self._curLat = client.get_state(entity_id="device_tracker.x5_xdrive40i").attributes["latitude"]
        self._curdir = client.get_state(entity_id="device_tracker.x5_xdrive40i").attributes["direction"]
        print(f"Current Longitude : {self._curLong}", file=self._logFileHandle)
        print(f"Current Latitude : {self._curLat}", file=self._logFileHandle)
        print(f"Current Dir : {self._curdir}", file=self._logFileHandle)
        
        if self._prevLat is not None and self._prevLong is not None and self._prevdir is not None:
            distance = BMWLockMonitorWrapper.haversine(self._prevLat, self._prevLong, self._curLat, self._curLong)
            
            print(f"Previous Longitude : {self._prevLong}", file=self._logFileHandle)
            print(f"Previous Latitude : {self._prevLat}", file=self._logFileHandle)
            print(f"Previous Dir : {self._prevdir}", file=self._logFileHandle)
            print(f"Distance : {distance}", file=self._logFileHandle)
            
            if distance != 0 or self._prevdir != self._curdir:
                distance = 1
                self._driving = True
            else:
                distance = 0
                self._driving = False
            
            client.set_state(State(state=str(distance), entity_id="sensor.x5_xdrive40i_driving", attributes={"driving":distance}))            
        
        self._prevLat = self._curLat
        self._prevLong = self._curLong
        self._prevdir = self._curdir
        
        door = client.get_state(entity_id="binary_sensor.x5_xdrive40i_door_lock_state").state
        window = client.get_state(entity_id="binary_sensor.x5_xdrive40i_windows").state
        lids = client.get_state(entity_id="binary_sensor.x5_xdrive40i_lids").state
        print(f"Door State : {door}", file=self._logFileHandle)
        print(f"Window State : {window}", file=self._logFileHandle)
        print(f"Lids State : {lids}", file=self._logFileHandle)
        
        if (door == "on" or window == "on" or lids == "on"):
            if self._driving == False:
                self._iter += 1
                if self._iter >= 2:
                    print("sending notification", file=self._logFileHandle)
                    #client.call_service("notify", service="mobile_app_som4tress_iphone", data={"message": "BMW X5 doors or windows or lids might not be locked!"})
                    self._iter = 0  
            else:
                self._iter = 0
            
def main():
    bmwWrapper = BMWLockMonitorWrapper()
    
    while True:
        bmwWrapper.updateLocation()
        
        if bmwWrapper._logFileHandle != sys.stdout:
            bmwWrapper._logFileHandle.flush()
            os.fsync(bmwWrapper._logFileHandle.fileno())
        
        tm.sleep(60)
    
if __name__ == "__main__":
    main()