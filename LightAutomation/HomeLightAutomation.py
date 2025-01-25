import asyncio
import sys
import os
import time as tm
from datetime import datetime
from kasa import Discover
from homeassistant_api import Client, State
import numpy

class KasaHAWrapper :
    def __init__(self):
        self._livingRoomDimmerIP = None
        self._kitchenIslandSwitchIP = None
        self._officeWaxWarmerSwitchIP = None
        self._mainBedroomSwitchIP = None
        self._hallwayDimmerIP = None
        self._shiviBedroomLightSwitchIP = None
        self._livingRoomWaxWarmerSwitchIP = None
        
        self._sensorValuesMaxCount = 5
        self._livingRoomDimmerAmbientLightValuesArr = None
        self._hallwayDimmerAmbientLightValuesArr = None
        
        self._prevTime = None        
        
        self._logFile = os.environ['PLUTO_HOME_DIR'] + "/LightAutomation/LightAutomation.log"
        self._logFileHandle = open(self._logFile, 'w')
        # self._logFileHandle = sys.stdout
        
        self._longLivedToken = os.environ["HA_LONG_LIVE_TOKEN"]
    
    async def discoverDimmers(self):
        try:
            nowTime = datetime.now()#.astimezone(timezone('US/Pacific'))
            
            if self._prevTime is None or (nowTime - self._prevTime).seconds >= 600:        
                print(f"Discovering Devices...", file=self._logFileHandle) 
                found_devices = await Discover.discover()            
                print(f"Found devices", file=self._logFileHandle)
                
                for key, value in found_devices.items():
                    print(f"Key:{key} | Value:{value}", file=self._logFileHandle)
                    
                    if "Living Room Dimmer" in str(value):
                        self._livingRoomDimmerIP = str(key)
                    elif "Kitchen Island" in str(value):
                        self._kitchenIslandSwitchIP = str(key)
                    elif "Office Wax Warmer" in str(value):
                        self._officeWaxWarmerSwitchIP = str(key)
                    elif "Main Bedroom Lights" in str(value):
                        self._mainBedroomSwitchIP = str(key)
                    elif "Hallway Dimmer" in str(value):
                        self._hallwayDimmerIP = str(key)
                    elif "Shivi Bedroom Light" in str(value):
                        self._shiviBedroomLightSwitchIP = str(key)
                    elif "Living Room Wax Warmer" in str(value):
                        self._livingRoomWaxWarmerSwitchIP = str(key)
                self._prevTime = nowTime
            else:
                print(f"Last Discovery was {(nowTime - self._prevTime).seconds} seconds ago hence skipping discovery")
                        
            print(f"Living Room Dimmer = {self._livingRoomDimmerIP}", file=self._logFileHandle)
            print(f"Kitchen Island Light Switch = {self._kitchenIslandSwitchIP}", file=self._logFileHandle)
            print(f"Office Wax Warmer Switch = {self._officeWaxWarmerSwitchIP}", file=self._logFileHandle)
            print(f"Main Bedroom Lights Switch = {self._mainBedroomSwitchIP}", file=self._logFileHandle)
            print(f"Hallway Dimmer = {self._hallwayDimmerIP}", file=self._logFileHandle)
            print(f"Shivi Bedroom Light Switch = {self._shiviBedroomLightSwitchIP}", file=self._logFileHandle)
            print(f"Living Room Wax Warmer Switch = {self._livingRoomWaxWarmerSwitchIP}", file=self._logFileHandle)
            
            print("Reading Island light status", file=self._logFileHandle)
            dev = await Discover.discover_single(self._kitchenIslandSwitchIP)
            await dev.update()
            print(f"Kitchen Island Light Status : {dev.is_on}", file=self._logFileHandle)
            offset = 0
            if dev.is_on:
                offset = 30
            
            print("Reading Ambient light from Living Room Dimmer", file=self._logFileHandle)        
            dev = await Discover.discover_single(self._livingRoomDimmerIP)
            await dev.update()
            val = str(float(str(dev.features['ambient_light'].value).replace('%', '').strip()) - offset)
            self._livingRoomDimmerAmbientLight = val
            print(f"Living Room Dimmer Ambient Light : {self._livingRoomDimmerAmbientLight}", file=self._logFileHandle)        
            
            print("Reading Ambient light from Hallway Dimmer", file=self._logFileHandle)
            dev = await Discover.discover_single(self._hallwayDimmerIP)
            await dev.update()                
            self._hallwayDimmerAmbientLight = (str(dev.features['ambient_light'].value).replace('%', '').strip())
            print(f"Hallway Dimmer Ambient Light : {self._hallwayDimmerAmbientLight}", file=self._logFileHandle) 
        except Exception as e:
            print(f"Exception in discoverDimmers : {str(e)}", file=self._logFileHandle)
        
    async def HAAdjustLighting(self): ## Adjust Lighting based on Living Room's Ambient Light, Sun Position and Time of the day
        if self._livingRoomDimmerAmbientLightValuesArr is None:
            self._ambientValueReadCount = 0
            self._livingRoomDimmerAmbientLightValuesArr = numpy.zeros(self._sensorValuesMaxCount)
            self._hallwayDimmerAmbientLightValuesArr = numpy.zeros(self._sensorValuesMaxCount)
            #client.set_state(State(state=self._livingRoomDimmerAmbientLight, entity_id="sensor.living_room_ambient_light", attributes={"ambient_light":self._livingRoomDimmerAmbientLight}))
            #client.set_state(State(state=self._hallwayDimmerAmbientLight, entity_id="sensor.hallway_ambient_light", attributes={"ambient_light":self._hallwayDimmerAmbientLight}))
            print("Initializing ambient sensor values array", file=self._logFileHandle)
        
        if self._ambientValueReadCount < self._sensorValuesMaxCount:
            self._livingRoomDimmerAmbientLightValuesArr[self._ambientValueReadCount] = self._livingRoomDimmerAmbientLight
            self._hallwayDimmerAmbientLightValuesArr[self._ambientValueReadCount] = self._hallwayDimmerAmbientLight
            self._ambientValueReadCount += 1
            
        print(f"Living Room Abient Light Values : {self._livingRoomDimmerAmbientLightValuesArr}", file=self._logFileHandle)
        print(f"Hallway Abient Light Values : {self._hallwayDimmerAmbientLightValuesArr}", file=self._logFileHandle)
            
        if self._ambientValueReadCount >= self._sensorValuesMaxCount:
            print("Updating HA Values", file=self._logFileHandle)
                        
            client = Client(os.environ["HA_EXTERNAL_API_URL"], self._longLivedToken, use_async=False)
            sun_state = str(client.get_state(entity_id="sun.sun").state)
            
            val = str(round(abs(numpy.average(self._livingRoomDimmerAmbientLightValuesArr)), 2))
            client.set_state(State(state=val, entity_id="sensor.living_room_ambient_light", attributes={"ambient_light":val}))
            
            val = str(round(abs(numpy.average(self._hallwayDimmerAmbientLightValuesArr)), 2))
            client.set_state(State(state=val, entity_id="sensor.hallway_ambient_light", attributes={"ambient_light":val}))
            
            self._ambientValueReadCount = 0
            self._livingRoomDimmerAmbientLightValuesArr = numpy.zeros(self._sensorValuesMaxCount)
            self._hallwayDimmerAmbientLightValuesArr = numpy.zeros(self._sensorValuesMaxCount)
        
            
    def Setup(self):
        asyncio.run(self.discoverDimmers())        
        asyncio.run(self.HAAdjustLighting())
        
def main():
    kasaWrapper = KasaHAWrapper()
    
    while(True):        
        kasaWrapper.Setup()
        print("--------------------------------------------------", file=kasaWrapper._logFileHandle)
        
        if kasaWrapper._logFileHandle != sys.stdout:
            kasaWrapper._logFileHandle.flush()
            os.fsync(kasaWrapper._logFileHandle.fileno())
        
        tm.sleep(30)
    
if __name__ == "__main__":
    main()