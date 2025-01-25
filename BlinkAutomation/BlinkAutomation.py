import nest_asyncio
nest_asyncio.apply()

import scapy.all as scapy
import asyncio

import sys
import os

from aiohttp import ClientSession
from blinkpy.blinkpy import Blink
from blinkpy.auth import Auth
from blinkpy.helpers.util import json_load

import time as tm
from datetime import datetime, time
from datetime import datetime
from re import findall
from subprocess import Popen, PIPE

from homeassistant_api import Client, State

class BlinkWrapper :
    def __init__(self):
        #self._blink = blink
        self._doorBellCamera = None
        self._backyardOutCamera = None
        self._shiviDenOutCamera = None
        self._syncName = None
        self._syncModule = None
        self._shiviDenInCamera = None        
        self._livingRoomInCamera = None
        self._somDenInCamera = None
        self._prevSyncTime = None
        self._logFile = os.environ['PLUTO_HOME_DIR'] + "/BlinkAutomation/BlinkAutomation.log"        
        self._logFileHandle = open(self._logFile, 'w')
        #self._logFileHandle = sys.stdout
        
        self._longLivedToken = os.environ["HA_LONG_LIVE_TOKEN"]
        
    async def start(self):
        #blink = Blink(session=ClientSession())
        # Can set no_prompt when initializing auth handler        
        self._session = ClientSession()
        blink = Blink(session=self._session)
        auth = Auth(await json_load("credentials.json"))
        blink.auth = auth
        await blink.start()                
        #await blink.save("credentials.json")
        return blink
    
    async def syncArm(self, flag):        
        print('=======================================', file=self._logFileHandle)
        print("Arming Sync Module", file=self._logFileHandle) if flag == True else print("Dis-Arming Sync Module", file=self._logFileHandle)
        print('=======================================', file=self._logFileHandle)
        result = await self._syncModule.async_arm(flag)              
        return result
    
    async def cameraArm(self, camera, flag):
        print('=======================================', file=self._logFileHandle)
        print("Arming " + camera.name, file=self._logFileHandle) if flag == True else print("Dis-Arming " + camera.name, file=self._logFileHandle)
        print('=======================================', file=self._logFileHandle)
        result = await camera.async_arm(flag)        
        return result
    
    def isNowInTimePeriod(self, startTime, endTime, nowTime): 
        if startTime < endTime: 
            return nowTime >= startTime and nowTime <= endTime 
        else: 
            #Over midnight: 
            return nowTime >= startTime or nowTime <= endTime 

    def SyncWithSchedule(self):
        nowTime = datetime.now()#.astimezone(timezone('US/Pacific'))
    
        if(self._prevSyncTime):
            td = nowTime - self._prevSyncTime
            
            if(td.total_seconds() <= 900):
                print(str(nowTime) + ': ' + "Skipping Sync with schedule - elapsed seconds : " + str(td.total_seconds()) + " between calls, so throttling", file=self._logFileHandle)
                return
            
        # schedule = self._syncModule.list_schedule()
        
        # if(len(schedule) == 0):
        #     return None

        # if(len(schedule[0]["schedule"]) < 0):
        #     return None

        # if("arm".lower() in schedule[0]["schedule"][0]["action"].lower()):
        #     armTime = parser.parse(schedule[0]["schedule"][0]["time"]).astimezone(timezone('US/Pacific')).time()
        #     disarmTime = parser.parse(schedule[0]["schedule"][1]["time"]).astimezone(timezone('US/Pacific')).time()
        # else:
        #     armTime = parser.parse(schedule[0]["schedule"][1]["time"]).astimezone(timezone('US/Pacific')).time()
        #     disarmTime = parser.parse(schedule[0]["schedule"][0]["time"]).astimezone(timezone('US/Pacific')).time()
        
        armTime = time(00, 00, 00)    
        disarmTime = time(6, 00, 00)
        print("nowTime : " + str(nowTime.time()) + " armTime : " + str(armTime) + " disarmTime : " + str(disarmTime), file=self._logFileHandle)
        
        #print(str(nowTime) + ': ' + "Syncing with schedule, Arming Sync Module ...")
        #asyncio.run(self.syncArm(True))
        #return

        client = Client(os.environ["HA_EXTERNAL_API_URL"], self._longLivedToken, use_async=False)        

        if(self.isNowInTimePeriod(nowTime.time(), armTime, disarmTime)):
            print(str(nowTime) + ': ' + "Arming Backyard Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._backyardOutCamera, True))
            client.set_state(State(state="on", entity_id="sensor.blink_backyard_camera", attributes={"battery": self._backyardOutCamera.battery}))
            tm.sleep(10)
            
            print(str(nowTime) + ': ' + "Arming Shivi Den Out Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._shiviDenOutCamera, True))
            client.set_state(State(state="on", entity_id="sensor.blink_shivi_den_out_camera", attributes={"battery": self._shiviDenOutCamera.battery}))
            tm.sleep(10)
            
            print(str(nowTime) + ': ' + "Arming Shivi Den In Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._shiviDenInCamera, True))  
            client.set_state(State(state="on", entity_id="sensor.blink_shivi_den_in_camera", attributes={"battery": self._shiviDenInCamera.battery}))          
            tm.sleep(10)
            
            # print(str(nowTime) + ': ' + "Arming Som Den In Camera ...")
            # self._somDenInCamera.arm = True
            # time.sleep(10)
        else:
            print(str(nowTime) + ': ' + "Disarming Backyard Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._backyardOutCamera, False))
            client.set_state(State(state="off", entity_id="sensor.blink_backyard_camera", attributes={"battery": self._backyardOutCamera.battery}))
            tm.sleep(10)
            
            print(str(nowTime) + ': ' + "Disarming Shivi Den Out Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._shiviDenOutCamera, False))
            client.set_state(State(state="off", entity_id="sensor.blink_shivi_den_out_camera", attributes={"battery": self._shiviDenOutCamera.battery}))
            tm.sleep(10)
            
            print(str(nowTime) + ': ' + "Disarming Shivi Den In Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._shiviDenInCamera, False))            
            client.set_state(State(state="off", entity_id="sensor.blink_shivi_den_in_camera", attributes={"battery": self._shiviDenInCamera.battery}))
            tm.sleep(10)
            
            #print(str(nowTime) + ': ' + "Disarming Som Den In Camera ...", file=self._logFileHandle)
            #self._somDenInCamera.arm = False
            #tm.sleep(10)
            
            print(str(nowTime) + ': ' + "Disarming Living Room In Camera ...", file=self._logFileHandle)
            asyncio.run(self.cameraArm(self._livingRoomInCamera, False))             
            client.set_state(State(state="off", entity_id="sensor.blink_living_room_in_camera", attributes={"battery": self._livingRoomInCamera.battery}))
            tm.sleep(10)

        print(str(nowTime) + ': ' + "Arming Door Bell Camera ...", file=self._logFileHandle)
        asyncio.run(self.cameraArm(self._doorBellCamera, True))
        client.set_state(State(state="on", entity_id="sensor.blink_door_bell_camera", attributes={"battery": self._doorBellCamera.battery}))
        tm.sleep(10)
        
        self._prevSyncTime = nowTime

        print("==================================================================================================", file=self._logFileHandle)

    def OverrideSchedule(self):
        client = Client(os.environ["HA_EXTERNAL_API_URL"], self._longLivedToken, use_async=False)
        
        nowTime = datetime.now()#.astimezone(timezone('US/Pacific'))

        print(str(nowTime) + ': ' + "Overriding Sync with schedule, Arming System ...", file=self._logFileHandle)
        asyncio.run(self.syncArm(True))
        client.set_state(State(state="on", entity_id="sensor.blink_sync_module"))    
        tm.sleep(10)

        print(str(nowTime) + ': ' + "Arming Backyard Out Camera ...", file=self._logFileHandle)                
        asyncio.run(self.cameraArm(self._backyardOutCamera, True))
        client.set_state(State(state="on", entity_id="sensor.blink_backyard_camera", attributes={"battery": self._backyardOutCamera.battery}))
        tm.sleep(10)
        
        print(str(nowTime) + ': ' + "Arming Shivi Den Out Camera ...", file=self._logFileHandle)
        asyncio.run(self.cameraArm(self._shiviDenOutCamera, True))
        client.set_state(State(state="on", entity_id="sensor.blink_shivi_den_out_camera", attributes={"battery": self._shiviDenOutCamera.battery}))
        tm.sleep(10)
        
        print(str(nowTime) + ': ' + "Arming Shivi Den In Camera ...", file=self._logFileHandle)
        asyncio.run(self.cameraArm(self._shiviDenInCamera, True))
        client.set_state(State(state="on", entity_id="sensor.blink_shivi_den_in_camera", attributes={"battery": self._shiviDenInCamera.battery}))
        tm.sleep(10)
        
        # print(str(nowTime) + ': ' + "Arming Som Den In Camera ...")
        # self._somDenInCamera.arm = True
        # tm.sleep(10)
        
        print(str(nowTime) + ': ' + "Arming Living Room In Camera ...", file=self._logFileHandle)        
        asyncio.run(self.cameraArm(self._livingRoomInCamera, True))
        client.set_state(State(state="on", entity_id="sensor.blink_living_room_in_camera", attributes={"battery": self._livingRoomInCamera.battery}))
        tm.sleep(10)
        
        print(str(nowTime) + ': ' + "Arming Door Bell Camera ...", file=self._logFileHandle)
        asyncio.run(self.cameraArm(self._doorBellCamera, True))
        client.set_state(State(state="on", entity_id="sensor.blink_door_bell_camera", attributes={"battery": self._doorBellCamera.battery}))
        tm.sleep(10)
        
    def Setup(self) :
        self._blink = asyncio.run(self.start())
        
        print("Searching for Home Cameras", file=self._logFileHandle)    

        #print(self._blink.cameras)
        for name, camera in self._blink.cameras.items():
            print(name, file=self._logFileHandle)
            if("door".lower() in name.lower()):
                self._doorBellCamera = camera                                
                print("Found door bell camera ...", file=self._logFileHandle)                                
            elif("backyard".lower() in name.lower()):
                self._backyardOutCamera = camera
                print("Found backyard camera ...", file=self._logFileHandle)                
            elif("shivi den (out)".lower() in name.lower()):
                self._shiviDenOutCamera = camera
                print("Found shivi den out camera ...", file=self._logFileHandle)
            elif("shivi den (in)".lower() in name.lower()):
                self._shiviDenInCamera = camera
                print("Found shivi den in camera ...", file=self._logFileHandle)
            elif("som den".lower() in name.lower()):
                self._somDenInCamera = camera
                print("Found som den in camera", file=self._logFileHandle)
            elif("living room".lower() in name.lower()):
                self._livingRoomInCamera = camera
                print("Found living room in camera", file=self._logFileHandle)

        for syncName, syncModule in self._blink.sync.items():
            print("Searching for Home Cameras Sync Module...", file=self._logFileHandle)
            if "home cameras" in syncName.lower():
                self._syncName = syncName
                self._syncModule = syncModule
                print("Found Home Cameras Sync Module", file=self._logFileHandle)
                return
            else:
                continue
            
def detect_iphone(logFileHandle):
    nowTime = datetime.now()#.astimezone(timezone('US/Pacific'))
    
    print(str(nowTime) + ':' + " Trying to detect iPhone in Network .....", file=logFileHandle)

    found_flag = False    
    
    ip_list = [os.environ['SOM_IPHONE_IP'], os.environ['SHOBHA_IPHONE_IP']]

    ## Ping Test
    for ip in ip_list:
        try:        
            print(f"Pinging {ip} ...", file=logFileHandle)
            data = ""
            output = Popen(f"ping {ip} -c {5}", stdout=PIPE, encoding="utf-8", shell=True)        
            for line in output.stdout:
                data = data + line            
                ping_test = findall("TTL", data.upper())
                
            if ping_test:
                #print("Ping Test Pass", file=logFileHandle)
                found_flag = True
                break
            else:
                found_flag = False
        except Exception as e:
            print(f'Exception during Ping Test : {e}')
    
    ## ARP Test
    if found_flag == False:
        try:            
            print("Initiating ARP Test", file=logFileHandle)
            scapy.conf.verb = 0
            request = scapy.ARP()
            request.pdst = '10.0.0.1/24'
            broadcast = scapy.Ether()
            broadcast.dst = 'ff:ff:ff:ff:ff:ff'
            request_broadcast = broadcast / request
            clients = scapy.srp(request_broadcast, timeout = 1)[0]
            for element in clients:        
                if os.environ["SOM_IPHONE_IP"] in element[1].psrc:
                    print("Somdutta iPhone Detected", file=logFileHandle)
                    found_flag = True
                    break
                if os.environ["SHOBHA_IPHONE_IP"] in element[1].psrc:
                    print("Shobha iPhone Detected", file=logFileHandle)
                    found_flag = True
                    break
        except Exception as e:
            print(f'Exception during ARP Test : {e}')
            
    
    detect_phone_res = 'Phone Detection Passed' if found_flag else 'Phone Detection Failed'
    print(detect_phone_res, file=logFileHandle)
    
    return found_flag

def main():    
    
    blinkWrapper = BlinkWrapper()
    
    if blinkWrapper.Setup() == False:
       print("Login Failed", file=blinkWrapper._logFileHandle)
       exit()
       
    prevDetectTime = None
    startTime = datetime.now()
    
    while(True):
        nowTime = datetime.now()#.astimezone(timezone('US/Pacific'))
        
        logResetDeltaTime = nowTime - startTime
        if logResetDeltaTime.total_seconds() >= (60 * 60):
            blinkWrapper._logFileHandle.close()
            tm.sleep(5)
            blinkWrapper._logFileHandle = open(blinkWrapper._logFile, 'w')
            startTime = datetime.now()
            
        tm.sleep(10)

        if(detect_iphone(blinkWrapper._logFileHandle) == True):
            print(str(nowTime) + ':' + " iPhone Detected, syncing Cameras to schedule......", file=blinkWrapper._logFileHandle)
            blinkWrapper.SyncWithSchedule()
            prevDetectTime = nowTime
        elif(prevDetectTime):
            td = nowTime - prevDetectTime
            print(str(nowTime) + ':' + " Elapsed time between iPhone detection : " + str(td.total_seconds()) + " seconds", file=blinkWrapper._logFileHandle)
            if(td.total_seconds() >= 600):
                blinkWrapper.OverrideSchedule()
                prevDetectTime = nowTime
        elif(prevDetectTime == None):
            prevDetectTime = nowTime
            
        if blinkWrapper._logFileHandle != sys.stdout:
            blinkWrapper._logFileHandle.flush()
            os.fsync(blinkWrapper._logFileHandle.fileno())

if __name__ == "__main__":
    main()
