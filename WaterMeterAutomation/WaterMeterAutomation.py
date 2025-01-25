from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from homeassistant_api import Client, State

import time
import threading
import re
import sys
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np

import json

from flask import Flask, request, jsonify

from collections import OrderedDict
from datetime import timedelta



class WaterSmartWebSiteWrapper:
    
    def __init__(self):
        # the target website url        
        self._url = os.environ["WATER_SMART_URL"] + "/welcome/login"
        self._driver = None
        self._prevtime = None
        
        self._second_last_value = 0
        self._current_value = 0
        self._average_1_week = 0
        self._average_2_weeks = 0
        self._average_1_month = 0
        self._average_2_month = 0
        self._setting_client_state = False
        
        self._longLivedToken = os.environ["HA_LONG_LIVE_TOKEN"]
        self._logFile = os.environ['PLUTO_HOME_DIR'] + "/WaterMeterAutomation/WaterMeterAutomation.log"
        self._logFileHandle = open(self._logFile, 'w')
        # self._logFileHandle = sys.stdout
    
    def calculate_average(self, data, days):
        end_date = max(data.keys())
        start_date = end_date - timedelta(days=days)
        filtered_data = {date: value for date, value in data.items() if start_date <= date <= end_date}
        if filtered_data:
            average = sum(filtered_data.values()) / len(filtered_data)
        else:
            average = 0
            
        return round(average, 2)
    
    def setup(self):
        # the interface for turning on headless mode 
        options = webdriver.FirefoxOptions() 
        options.add_argument("--headless") 
        #options.add_argument('--no-sandbox')
        #options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--window-size=1920,1080")
        
        driver_service = webdriver.FirefoxService(executable_path="/usr/bin/geckodriver")
        self._driver = webdriver.Firefox(options=options, service=driver_service)
    
    def extractConsumptionValues(self):
        final_data = {}
        
        try:
            self._driver.get(self._url) 
            time.sleep(10)
        
            input_elements = self._driver.find_elements(By.TAG_NAME, "input")

            print(f"Found {len(input_elements)} input elements:", file=self._logFileHandle)
            
            email_field = None
            password_field = None
            
            for index, element in enumerate(input_elements):
                input_type = element.get_attribute("type")  # Get the type of the input (e.g., text, password)
                input_name = element.get_attribute("name")  # Get the 'name' attribute
                input_id = element.get_attribute("id")  # Get the 'id' attribute
                input_placeholder = element.get_attribute("placeholder")  # Get the placeholder text
                
                # print(f"\nInput Element {index + 1}:", file=self._logFileHandle)
                # print(f"  Type: {input_type}", file=self._logFileHandle)
                # print(f"  Name: {input_name}", file=self._logFileHandle)
                # print(f"  ID: {input_id}", file=self._logFileHandle)
                # print(f"  Placeholder: {input_placeholder}", file=self._logFileHandle)
                
                if "email" in input_name:
                    email_field = self._driver.find_element(By.NAME, "email")
                    print("Found email field..", file=self._logFileHandle)
                elif "password" in input_name:
                    password_field = self._driver.find_element(By.NAME, "password")
                    print("Found password field..", file=self._logFileHandle)
                    
            
            print("Logging in...", file=self._logFileHandle)
            email_field.send_keys("som4tress@gmail.com")
            password_field.send_keys("Omsairam@watersmart1")
            password_field.send_keys(Keys.RETURN)
            
            time.sleep(5)
            
            print("Login done...", file=self._logFileHandle)
            
            self._driver.get(os.environ["WATER_SMART_URL"] + "/trackUsage")
            
            time.sleep(10)
            
            for i in range(0, 6):
                
                print(f"Extracting data for page {i + 1}...", file=self._logFileHandle)
                
                series_group = self._driver.find_element(By.CLASS_NAME, "highcharts-series-group")
                data_points = series_group.find_elements(By.XPATH, ".//*[name()='path' or name()='circle' or name()='rect']")

                # Parse X and Y values
                highchart_data = []
                for point in data_points:
                    attributes = self._driver.execute_script(
                        "var items = arguments[0].attributes; "
                        "var result = {}; "
                        "for (var i = 0; i < items.length; i++) { "
                        "  result[items[i].name] = items[i].value; "
                        "} "
                        "return result;", 
                        point
                    )

                    # Extract and parse attributes like `d` for paths or `cx`, `cy` for circles
                    data_entry = {"element": point.tag_name, "attributes": attributes}
                    highchart_data.append(data_entry)
                
                for entry in highchart_data:
                    if 'aria-label' in str(entry) and 'highcharts-point' in str(entry):
                        val = str(entry)                    
                        pattern = r'(\d+)\. (\w+), (\w+ {1,2}\d{1,2}, \d{4}), ([\d.]+)\.?'
                        match = re.search(pattern, val)
                        if match:
                            date_str = match.group(3)  # e.g. "Dec 15, 2024"
                            value_str = match.group(4)  # e.g. '435.2950000000001.'
                            date = datetime.strptime(date_str, '%b %d, %Y').date()
                            value = round(float(value_str.rstrip('.')), 2)
                            final_data[date] = value
                            # print(f"Extracted date: {date}")
                            # print(f"Extracted value: {value}")
                        else:
                            print(f"No match found for {val}") 
                
                # Locate the div with class "move left"
                move_left_div = self._driver.find_element(By.CLASS_NAME, 'move.left')

                # Click the div
                move_left_div.click()
                
                time.sleep(10)
            
            self._driver.quit()
        except Exception as e:
            print(f"Error while scrapping: {e}", file=self._logFileHandle)
            return -1            
        
        print("Dumping data to json", file=self._logFileHandle)
        
        # Convert date keys to strings
        final_data_str_keys = {date.strftime('%Y-%m-%d'): value for date, value in final_data.items()}

        # Sort the dictionary by date keys
        sorted_final_data_str_keys = dict(sorted(final_data_str_keys.items()))

        with open('/home/pluto/Projects/WaterMeterAutomation/water_usage.json', 'w') as f:
            json.dump(sorted_final_data_str_keys, f, indent=4) 
            
        self._average_1_week = self.calculate_average(final_data, 7)
        self._average_2_weeks = self.calculate_average(final_data, 14)
        self._average_1_month = self.calculate_average(final_data, 30)
        self._average_2_month = self.calculate_average(final_data, 60)
        
        print(f"Average for 1 week: {self._average_1_week}")
        print(f"Average for 2 weeks: {self._average_2_weeks}")
        print(f"Average for 1 month: {self._average_1_month}")
        print(f"Average for 2 months: {self._average_2_month}")
        
        client = Client(os.environ["HA_EXTERNAL_API_URL"], self._longLivedToken, use_async=False)
        current_date = max(final_data.keys())
        self._current_value = final_data[current_date]
        
        # Get the second last value
        sorted_dates = sorted(final_data.keys())
        second_last_date = sorted_dates[-2] if len(sorted_dates) > 1 else current_date
        self._second_last_value = final_data[second_last_date]

        if self._setting_client_state == False:
            try:
                self._setting_client_state = True
                client = Client(os.environ["HA_EXTERNAL_API_URL"], self._longLivedToken, use_async=False)
                client.set_state(State(state=str(self._second_last_value), entity_id="sensor.water_meter_last_value", attributes={"last_value": self._second_last_value}))
                client.set_state(State(state=str(self._current_value), entity_id="sensor.water_meter_current_value", attributes={"current_value": self._current_value}))
                client.set_state(State(state=str(self._average_1_week), entity_id="sensor.water_meter_values_average_1_week", attributes={"average_1_week": self._average_1_week}))
                client.set_state(State(state=str(self._average_2_weeks), entity_id="sensor.water_meter_values_average_2_weeks", attributes={"average_2_week": self._average_2_weeks}))
                client.set_state(State(state=str(self._average_1_month), entity_id="sensor.water_meter_values_average_1_month", attributes={"average_1_month": self._average_1_month}))
                client.set_state(State(state=str(self._average_2_month), entity_id="sensor.water_meter_values_average_2_month", attributes={"average_2_month": self._average_2_month}))
            except Exception as e:
                print(f"Error setting client states: {e}", file=self._logFileHandle)
                return -1
        
        self._setting_client_state = False
    
        return 0
        
        
def main():
    waterSmartWrapper = WaterSmartWebSiteWrapper()
    
    def flask_thread():
        app = Flask(__name__)
        
        @app.route('/api/water_usage', methods=['GET'])
        def get_water_usage():
            print("GET request received...", file=waterSmartWrapper._logFileHandle)
            
            print("Setting client states state...", file=waterSmartWrapper._logFileHandle)
            
            if waterSmartWrapper._setting_client_state == False:
                try:
                    waterSmartWrapper._setting_client_state = True
                    client = Client(os.environ["HA_EXTERNAL_API_URL"], waterSmartWrapper._longLivedToken, use_async=False)
                    client.set_state(State(state=str(waterSmartWrapper._second_last_value), entity_id="sensor.water_meter_last_value", attributes={"last_value": waterSmartWrapper._second_last_value}))
                    client.set_state(State(state=str(waterSmartWrapper._current_value), entity_id="sensor.water_meter_current_value", attributes={"current_value": waterSmartWrapper._current_value}))
                    client.set_state(State(state=str(waterSmartWrapper._average_1_week), entity_id="sensor.water_meter_values_average_1_week", attributes={"average_1_week": waterSmartWrapper._average_1_week}))
                    client.set_state(State(state=str(waterSmartWrapper._average_2_weeks), entity_id="sensor.water_meter_values_average_2_weeks", attributes={"average_2_week": waterSmartWrapper._average_2_weeks}))
                    client.set_state(State(state=str(waterSmartWrapper._average_1_month), entity_id="sensor.water_meter_values_average_1_month", attributes={"average_1_month": waterSmartWrapper._average_1_month}))
                    client.set_state(State(state=str(waterSmartWrapper._average_2_month), entity_id="sensor.water_meter_values_average_2_month", attributes={"average_2_month": waterSmartWrapper._average_2_month}))
                except Exception as e:
                    print(f"Error setting client states: {e}", file=waterSmartWrapper._logFileHandle)                    
                
            waterSmartWrapper._setting_client_state = False

            with open('/home/pluto/Projects/WaterMeterAutomation/water_usage.json', 'r') as f:
                data = json.load(f)

            formatted_data = [{"Date": f"{date}T00:00:00", "WaterConsumption": value} for date, value in data.items()]
            formatted_data.sort(key=lambda x: datetime.strptime(x["Date"], "%Y-%m-%dT%H:%M:%S"))
            
            if formatted_data:
                formatted_data.pop()  # Remove the last entry

            response = OrderedDict([("object", "list"), ("data", formatted_data)])
            return jsonify(dict(response))
        
        app.run(debug=False, use_reloader=False)
        
    # Start the Flask app in a separate thread
    threading.Thread(target=flask_thread).start()
    
    while(True):
        print("Starting the WaterSmartWebSiteWrapper...", file=waterSmartWrapper._logFileHandle)
        waterSmartWrapper.setup()
        
        print("Extracting consumption values...", file=waterSmartWrapper._logFileHandle)
        if waterSmartWrapper.extractConsumptionValues() == -1:
            print("Error while scrapping the data", file=waterSmartWrapper._logFileHandle)
            continue
        
        if waterSmartWrapper._logFileHandle != sys.stdout:
            waterSmartWrapper._logFileHandle.flush()
            os.fsync(waterSmartWrapper._logFileHandle.fileno())
        
        print("Sleeping for 1 hour...", file=waterSmartWrapper._logFileHandle)
        time.sleep(60 * 60)  # Sleep for 1 hour
        
    
if __name__ == "__main__":
    main()
