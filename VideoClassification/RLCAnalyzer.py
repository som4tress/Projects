import requests
from datetime import datetime, timedelta
import pytz
import os
import time

from VideoClassification import VideoAnalyser

def trigger_home_automation(automation_entity_id, data = None):
    try:
        url = f"{os.environ['HA_EXTERNAL_API_URL']}/{automation_entity_id}"
        
        headers = {
            "Authorization": f"Bearer {os.environ['HA_LONG_LIVE_TOKEN']}",
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
    except Exception as e:
        print(f"Error: {e} while triggering automation {automation_entity_id}")

def find_closest_file(latest_off_time_str):
    # Convert the latest_off_time string to a datetime object
    latest_off_time = datetime.fromisoformat(latest_off_time_str)
    
    # Extract year, month, day, and time from latest_off_time
    year = latest_off_time.year
    month = latest_off_time.month
    day = latest_off_time.day
    hour = latest_off_time.hour
    minute = latest_off_time.minute
    second = latest_off_time.second

    # Format the directory path and file pattern
    directory_path = f"/mnt/Seagate_Expansion/recolink/{year}/{month:02d}/{day:02d}"
    #file_pattern = f"Frontyard RLC-510wa_00_{year}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}"

    # List all files in the directory
    files = os.listdir(directory_path)    

    # Find the closest file
    closest_file = None
    closest_time_diff = float('inf')   
    for file in files:
        if file.endswith(".mp4"):
            file_path = os.path.join(directory_path, file)
            file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path)).astimezone(pytz.timezone('America/Los_Angeles'))            
            # Ignore seconds and milliseconds for comparison
            file_creation_time = file_creation_time.replace(second=0, microsecond=0)
            latest_off_time = latest_off_time.replace(second=0, microsecond=0)   
            #print(f"File time: {file_time}, Latest off time: {latest_off_time}")     
            if file_creation_time >= latest_off_time:                                
                time_diff = abs((latest_off_time - file_creation_time).total_seconds())
                if time_diff < closest_time_diff:
                    closest_time_diff = time_diff
                    closest_file = file                     

    if closest_file:        
        return os.path.join(directory_path, closest_file)
    else:
        print("No matching file found")
    
    return None

    

def get_ha_person_sensor_stats():
    try:
        HA_API_URL = os.environ["HA_EXTERNAL_API_URL"]
        HA_TOKEN = os.environ["HA_LONG_LIVE_TOKEN"]

        # Calculate the end time (current time) and start time (30 seconds ago)
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=30)
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%S%z")

        print(f"Start time: {start_time}, End time: {end_time}")   

        # Define the headers for the request
        headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

        # Define the entity ID for the binary sensor
        #entity_id = "binary_sensor.frontyard_rlc_510wa_person"
        entity_id = "binary_sensor.frontyard_reolink_duo_person"

        # Define the URL for the history endpoint
        history_url = f"{HA_API_URL}/history/period"

        # Define the parameters for the request
        params = {
            "filter_entity_id": entity_id,    
            "start_time": start_time_str,
            "end_time": end_time_str,
        }

        # Prepare the request
        req = requests.Request('GET', history_url, headers=headers, params=params)
        prepared = req.prepare()

        # Print the actual HTTP request string
        print(f"Request URL: {prepared.url}")
        print(f"Request Headers: {prepared.headers}")

        # Make the request to the history endpoint
        response = requests.Session().send(prepared)

        if response.status_code == 200:
            history = response.json()
            print(f"History for {entity_id}:")
            time_state_list = []
            for state in history[0]:
                utc_time = datetime.fromisoformat(state['last_changed'])
                pdt_time = utc_time.astimezone(pytz.timezone('America/Los_Angeles'))
                #print(f"Time: {pdt_time}, State: {state['state']}")
                time_state_list.append((pdt_time, state['state']))
                
            latest_off_time = None

            for i in range(len(time_state_list) - 1, 0, -1):
                if time_state_list[i][1] == "off" and time_state_list[i - 1][1] == "on":
                    latest_off_time = time_state_list[i][0]
                    break
            
            #print(f"Latest off time: {latest_off_time}")
            return latest_off_time
        else:
            print(f"Failed to retrieve history: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error: {e}")
     
    return None
            
def copy_closest_file_to_remote(closest_file):
    remote_path = "pluto@pluto.local:/usr/share/hassio/media/RLC.mp4"
    password = os.environ["PLUTO_PWD"]
    
    # Construct the SCP command
    scp_command = f"sshpass -p '{password}' scp '{closest_file}' {remote_path}"
    
    # Execute the SCP command
    os.system(scp_command)

def main():
    # last_file_processed = ""    
    # closest_file = "/mnt/Seagate_Expansion/recolink/2025/03/Frontyard Reolink Duo_00_20250315153325.mp4"    
    # vl = VideoAnalyser(video_path=closest_file, output_dir="/home/somdutta/Projects/VideoClassification/output_frames")    
    # converted_file, detected_labels_dict, fname_list = vl.video_to_frames(filter_movement=True)  
    # print(converted_file)  
    # analysis_long = vl.analyze_security_camera_images(image_list=fname_list, detection_dict=detected_labels_dict, timestamp="2025-03-02 13:22:57")
    # print(f"Analysis_long: {analysis_long}")
    # return
    
    last_file_processed = ""
    while True:
        start_time = datetime.now()
        
        latest_off_time = get_ha_person_sensor_stats()        
        
        if latest_off_time != None:
            print(f"Latest off time: {latest_off_time.strftime("%Y-%m-%d %H:%M:%S")}")
            closest_file = find_closest_file(latest_off_time.isoformat())                        
            print(f"Closest file: {closest_file}")                                            
            if closest_file != None:                            
                if last_file_processed != closest_file:
                    vl = VideoAnalyser(video_path=closest_file, output_dir="/home/somdutta/Projects/VideoClassification/output_frames")                    
                    detected_labels_dict, fname_list = vl.video_to_frames(filter_movement=True)                     
                    print(f"Detected labels: {detected_labels_dict}")
                    print(f"File list: {fname_list}")                                                      
                    if 'person' in detected_labels_dict and detected_labels_dict['person'] > 0 and len(fname_list) > 0:
                        vl.adjust_video(closest_file, "/home/somdutta/Projects/VideoClassification/output_frames/adjusted_video.mp4")
                        copy_closest_file_to_remote("/home/somdutta/Projects/VideoClassification/output_frames/adjusted_video.mp4")     
                        analysis_long = vl.analyze_security_camera_images(image_list=fname_list, detection_dict=detected_labels_dict, timestamp=latest_off_time.strftime("%Y-%m-%d %H:%M:%S"))                        
                        print(f"Analysis_long: {analysis_long}")                    
                        event_data = {
                            "title": f"Frontyard Camera - {latest_off_time.strftime('%Y-%m-%d %H:%M:%S')}",
                            #"message_short": analysis_short,
                            "message_long": analysis_long,
                        }                        
                        trigger_home_automation("events/camera_notification", data=event_data)                    
                        last_file_processed = closest_file                                            
                else:
                    print(f"File already processed: {closest_file}")        
                
        if datetime.now() - start_time < timedelta(seconds=60):
            print("Sleeping for 60 seconds...")
            time.sleep(60)




######################################################################################### Test Code #########################################################################################


    # vl = VideoAnalyser(video_path="/home/somdutta/Projects/VideoClassification/input_delivery.mp4", output_dir="/home/somdutta/Projects/VideoClassification/output_frames")
    # fname_list = vl.video_to_frames(filter_movement=True)
    # analysis_short, analysis_long = vl.analyze_security_camera_images(image_list=fname_list)
    # print(f"Analysis_short: {analysis_short}, Analysis_long: {analysis_long}")
    
    # event_data = {
    #                 "title": "Frontyard Camera",
    #                 "message_short": analysis_short,
    #                 "message_long": analysis_long,
    #             }
    
    # trigger_home_automation("events/camera_notification", data=event_data)
    
    # time.sleep(5)
    
    # vl = VideoAnalyser(video_path="/home/somdutta/Projects/VideoClassification/input_cycle.mp4", output_dir="/home/somdutta/Projects/VideoClassification/output_frames")
    # fname_list = vl.video_to_frames(filter_movement=True)
    # analysis = vl.analyze_security_camera_images(image_list=fname_list)
    # print(f"Analysis: {analysis}")
    
    # event_data = {
    #                 "title": "Frontyard Camera",
    #                 "message": analysis,
    #             }
    
    # trigger_home_automation("events/camera_notification", data=event_data)
    
    # time.sleep(5)
    
    # vl = VideoAnalyser(video_path="/home/somdutta/Projects/VideoClassification/input_2ped_walking.mp4", output_dir="/home/somdutta/Projects/VideoClassification/output_frames")
    # fname_list = vl.video_to_frames(filter_movement=True)
    # analysis = vl.analyze_security_camera_images(image_list=fname_list)
    # print(f"Analysis: {analysis}")
    
    # event_data = {
    #                 "title": "Frontyard Camera",
    #                 "message": analysis,
    #             }
    
    # trigger_home_automation("events/camera_notification", data=event_data)
    
    # time.sleep(5)
    
    # vl = VideoAnalyser(video_path="/home/somdutta/Projects/VideoClassification/input_ped_walking.mp4", output_dir="/home/somdutta/Projects/VideoClassification/output_frames")
    # fname_list = vl.video_to_frames(filter_movement=True)
    # analysis = vl.analyze_security_camera_images(image_list=fname_list)
    # print(f"Analysis: {analysis}")
    
    # event_data = {
    #                 "title": "Frontyard Camera",
    #                 "message": analysis,
    #             }
    
    # trigger_home_automation("events/camera_notification", data=event_data)
    
    # time.sleep(5)
    
    # vl = VideoAnalyser(video_path="/home/somdutta/Projects/VideoClassification/input_video.mp4", output_dir="/home/somdutta/Projects/VideoClassification/output_frames")
    # fname_list = vl.video_to_frames(filter_movement=True)
    # analysis = vl.analyze_security_camera_images(image_list=fname_list)
    # print(f"Analysis: {analysis}")
    
    # event_data = {
    #                 "title": "Frontyard Camera",
    #                 "message": analysis,
    #             }
    
    # trigger_home_automation("events/camera_notification", data=event_data)
    
    # time.sleep(5)
    
    # vl = VideoAnalyser(video_path="/home/somdutta/Projects/VideoClassification/input_video_night.mp4", output_dir="/home/somdutta/Projects/VideoClassification/output_frames")
    # fname_list = vl.video_to_frames(filter_movement=True)
    # analysis = vl.analyze_security_camera_images(image_list=fname_list)
    # print(f"Analysis: {analysis}")
    
    # event_data = {
    #                 "title": "Frontyard Camera",
    #                 "message": analysis,
    #             }
    
    # trigger_home_automation("events/camera_notification", data=event_data)

if __name__ == "__main__":
    main()