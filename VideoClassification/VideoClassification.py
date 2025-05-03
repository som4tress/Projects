import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import torch
import cv2
import os
import subprocess
import numpy as np
import ollama
import shutil
#import cupy as cp
#import base64

from ultralytics import YOLO

from torchvision import models, transforms
from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
from PIL import Image
 
 
class VideoAnalyser:
    
    def __init__(self, video_path, output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
        os.makedirs(output_dir, exist_ok=True)
        
        self._video_path = video_path
        self._output_dir = output_dir
        
        self._model = "gemma3:12b"  # or another vision-compatible model
        
    def adjust_video(self, input_video_path, output_video_path):       
        # Construct the ffmpeg command with CUDA acceleration
        ffmpeg_command = f"ffmpeg -hwaccel cuda -i '{input_video_path}' -to 00:00:25 -c copy {output_video_path}"
        
        # Execute the ffmpeg command and capture the output
        print(f"Executing command: {ffmpeg_command}")
        result = subprocess.run(ffmpeg_command, shell=True, capture_output=True, text=True)
     
    def video_to_frames(self, filter_movement=True):
        subprocess.run("ollama stop llama3.2-vision", shell=True, capture_output=True, text=True)
        
        #self.adjust_video(self._video_path, os.path.join(self._output_dir, "converted_video.mp4"), target_fps=15)

        # Open the video file
        cap = cv2.VideoCapture(os.path.join(self._output_dir, self._video_path))
        frame_count = 0
        name_count = 0
        prev_frame_gray = None
        curr_frame_gray = None
        fname_list = []

        # Get the total number of frames per second (FPS) in the video
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Processing video at {fps} FPS")        
        
        model = YOLO("yolo11n.pt").cuda()

        # Define the target classes (person and animals)
        TARGET_CLASSES = ["person", "dog", "cat", "truck", "car", "trash", "bicycle", "motorcycle", "bird", "backpack"]
        detected_labels = {label: 0 for label in TARGET_CLASSES}
        #print(detected_labels)
        i = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % int(fps) != 0:
                frame_count += 1
                continue
            else:
                frame_count += 1
                
            # Crop the frame
            frame = frame[:, 200:-650]
            
            # Resize the frame
            frame = cv2.resize(frame, (1623, 768), interpolation=cv2.INTER_LANCZOS4)
                
            if filter_movement:
                curr_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_frame_gray is None:
                    prev_frame_gray = curr_frame_gray
                    mean_diff = 0                    
                else:                                        
                    gray_frame_diff = cv2.absdiff(curr_frame_gray, prev_frame_gray)
                    mean_diff = np.mean(gray_frame_diff)
                    #print(f"Mean Diff : {mean_diff}")                        
            
            # # Convert frame to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Perform object detection using YOLO
            with torch.no_grad():
                results = model(frame_rgb, device='cuda:0', stream=False, conf=0.4, half=False, verbose=False, augment=True, iou=0.3, agnostic_nms=False)

            # Extract bounding boxes and labels
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            labels = model.names
            detections = []
            
            if len(confidences) > 0:            
            # Calculate dynamic threshold per label
                label_confidences = {label: [] for label in TARGET_CLASSES}
                for i, conf in enumerate(confidences):
                    label = labels[int(classes[i])]
                    if label in TARGET_CLASSES:
                        label_confidences[label].append(conf)

                dynamic_thresholds = {}
                for label, confs in label_confidences.items():
                    if confs:
                        dynamic_thresholds[label] = np.percentile(confs, 30)
                        #print(f"Dynamic threshold for {label}: {dynamic_thresholds[label]}")                
                
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box
                    conf = confidences[i]
                    cls = classes[i]
                    label = labels[int(cls)]
                    if label in TARGET_CLASSES and conf >= dynamic_thresholds.get(label, 0):
                        # Draw bounding box and confidence value
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        cv2.putText(frame, f'{label}:{conf:.1f}', (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                        detections.append(label)
                
                if detections.__len__() > 0 and 'person' in detections:                    
                    for label in TARGET_CLASSES:
                        detected_labels[label] = max(detected_labels[label], detections.count(label))
                    
                    frame_path = os.path.join(self._output_dir, f"frame_{name_count:04d}.jpg")
                    fname_list.append({
                                "path": frame_path,
                                "mean_diff": mean_diff,
                            })
                    name_count += 1                    
                    cv2.imwrite(frame_path, frame)
                    prev_frame_gray = curr_frame_gray   
        
        cap.release()
        
        if filter_movement:
            # Calculate the histogram of mean differences
            mean_diffs = [item['mean_diff'] for item in fname_list]
            hist, bin_edges = np.histogram(mean_diffs, bins='auto')

            # Determine the threshold for significant differences
            threshold_bin_index = int(len(bin_edges) * 0.5)
            bin_start = bin_edges[threshold_bin_index]

            # Filter frames based on the highest occurring bin of mean differences
            filtered_fnames = [item['path'] for item in fname_list if item['mean_diff'] > bin_start]

            print(f"Mean difference threshold bin start: {bin_start}")
            print(f"Filtered frames: {len(filtered_fnames)}, {filtered_fnames}")
            
            min_frame_count = min(3, len(fname_list))

            if len(filtered_fnames) < min_frame_count:
                while len(filtered_fnames) < min_frame_count:
                    for item in fname_list:
                        if item['path'] not in filtered_fnames:
                            filtered_fnames.append(item['path'])                                            
                return detected_labels, filtered_fnames          
            else:
                return detected_labels, filtered_fnames
        else:
            return detected_labels, [item['path'] for item in fname_list]

    def analyze_security_camera_images(self, image_list, detection_dict, timestamp):
            """Analyze multiple security camera images and provide a final summary."""          
            detection_summary = ", ".join([f"{value} {key}s" for key, value in detection_dict.items() if value > 0])
            detect_str = f"{detection_summary}"
            print(f"Detection summary: {detect_str}")        
            
            analyses = ""
            analysis_result = "No previous frame analysis"
            frame_count = 1
            
            for image in image_list:           
                try:
                    print(f"Processing {image}")
                    
                    response = ollama.chat(
                            model=self._model,  # or another vision-compatible model
                            messages=[                            
                                {"role": "system", "content": f"You are analyzing frame number {frame_count} from the same video footage from my home surveillance camera that got triggered on {timestamp} because it detected {detect_str}."},                                                
                                {"role": "user", "content": f"Describe {detect_str} attire and breed."},
                                {"role": "user", "content": f"Track positions of {detect_str} to compare with earlier frames and highlight changes." if frame_count == 1 else f"Do you see {detect_str} walking or driving."},
                                {"role": "user", "content": "Keep your response to the point under 50 words in a single paragraph and highlight suspicious movements." },
                                {"role": "user", "images": [image] }                                                                                                               
                            ], stream=False, options={'temperature': 1.0,
                                                    "top_k": 0.2,
                                                    'top_p': 0.5,
                                                    'mirostat_tau': 1,
                                                    'num_ctx': 4096,
                                                    'seed': 42,
                                                    'num_predict': 128}
                            )

                    # Store the analysis result
                    analysis_result = f"{response["message"]["content"]}"  
                    print(f"Analysis result: {analysis_result} \n")                
                    analyses += f"{analysis_result}.\n"
                    frame_count += 1
                    
                    max_len = 1500
                    if len(analyses) >= max_len:
                        analyses = analyses + "..."
                        break
                    
                except FileNotFoundError:
                    print(f"Error: Image file not found: {image}")
            
            
            print(f"\n\n\n\n {analyses}\n\n\n\n")
            
            final_response_long = ollama.chat(
                model=self._model,
                messages=[
                        {"role": "system", "content": f"You are analysing summaries of multiple frames of a video footage from my home surveillance camera as it detected {detect_str}. Keep your response under 150 words and to the point"},
                        {"role": "user", "content": f"Do not put time, date and parked cars in the response, and avoid frame numbers."},
                        {"role": "user", "content": f"Directly start from the summary."},
                        {"role": "user", "content": f"Generate a sarcastic and humorous summary combining the individual frame analysis"},
                        {"role": "user", "content": f"{analyses}"},
                        ], 
                    stream=False, options={'temperature': 0.5,
                                                "top_k": 0.2,
                                                'top_p': 0.8,
                                                'mirostat_tau': 0.5,
                                                'num_ctx': 4096,
                                                'seed': 42,
                                                'num_predict': 200}
            )
                    
            return final_response_long["message"]["content"]
