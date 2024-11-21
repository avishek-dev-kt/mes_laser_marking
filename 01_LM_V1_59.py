import os
import csv
import json
import shutil
import threading
import time
import logging
import requests
import urllib
import schedule
from datetime import datetime
import urllib.parse
from collections import defaultdict
import sys

# Define the password for reset (retrieve from environment variable for security else default value)
RESET_PASSWORD = os.getenv('RESET_PASSWORD', 'Kayneskt01')  # Changes based on plant - WIN - set RESET_PASSWORD=anypassword

# Configure logging
log_file_path = os.path.join(os.path.dirname(__file__), 'LM_app.log')
logging.basicConfig(filename=log_file_path, 
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Get the current directory of the app
current_directory = os.path.dirname(os.path.abspath(__file__))

# Defining folder names
folders = {
    "JSON_Data_Folder": os.path.join(current_directory, "JSON_Data_Folder"),
    "Scan_Folder": os.path.join(current_directory, "Scan_Folder"),
    "Backup_Folder": os.path.join(current_directory, "Backup_Folder"),
    "Logs_Folder": os.path.join(current_directory, "Logs_Folder"),
    "Done_Folder": os.path.join(current_directory, "Done_Folder"),  # Added cmd.py_10

}

# Defining log files in Logs_Folder
log_folders = {
    "Copy_Logs": os.path.join(folders["Logs_Folder"], "Copy_Logs"),
    "Backup_Logs": os.path.join(folders["Logs_Folder"], "Backup_Logs"),
    "Parser_Logs": os.path.join(folders["Logs_Folder"], "Parser_Logs"),
}

# Create folders. error handling added in cmd_3.py
def create_folders():
    try:
        for folder in folders.values():
            os.makedirs(folder, exist_ok=True)
        for log_folder in log_folders.values():
            os.makedirs(log_folder, exist_ok=True)
        logging.info("Folders created successfully.")
    except Exception as e:
        logging.error(f"Error creating folders: {e}")
        print(f"Error creating folders: {e}")

# Config file creation. Changed to JSON from TXT file in cmd_5.py
def write_folder_paths_to_file(api_key, api_secret, erp_url, machine_data_folder):
    try:
        config_data = {
            "API_Key": api_key,
            "API_Secret": api_secret,
            "ERP_URL": erp_url,
            "Machine_Data_Folder": machine_data_folder,
            "Folders": folders,
            "Log_Folders": log_folders
        }

        config_file = os.path.join(current_directory, "config.json")
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        logging.info("Configuration file created.")
    except Exception as e:
        logging.error(f"Failed to write configuration file: {e}")
        print(f"Failed to write configuration file: {e}")

# Function to load inputs from the config file
def load_inputs_from_file():
    try:
        config_file = os.path.join(current_directory, "config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                logging.info("Inputs loaded from Config file.")
                return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration file: {e}")
    return None

# Function to get inputs from the user (if not available in the config file)
def get_inputs():
    print("Please provide the following inputs:")
    api_key = input("API Key (api.py): ")
    api_secret = input("API Secret (api.py): ")
    erp_url = input("ERP URL (api.py): ")
    machine_data_folder = input("Machine Target DATA folder Path (mvf.py): ")
    logging.info("User Input Registered.")
    return api_key, api_secret, erp_url, machine_data_folder

# File Mover Functionality with error handling (added in cmd_5.py) - mvf.py
def copy_new_files(src_folder, dest_folder, copy_log_file):
    # logging.info("Triggered File Mover functionality.")
    try:
        if os.path.exists(copy_log_file):
            with open(copy_log_file, 'r') as log:
                copied_files = log.read().splitlines()
        else:
            copied_files = []

        src_files = os.listdir(src_folder)
        for file_name in src_files:
            src_file_path = os.path.join(src_folder, file_name)
            dest_file_path = os.path.join(dest_folder, file_name)
            
            if file_name not in copied_files:
                shutil.copy2(src_file_path, dest_file_path)
                with open(copy_log_file, 'a') as log:
                    log.write(f"{file_name}\n")
                print(f"Copied {file_name} to {dest_folder}")
                logging.info(f"Copied {file_name} to {dest_folder}")
    except Exception as e:
        logging.error(f"Error during file copying: {e}")
        print(f"Error during file copying: {e}")

# Function to move files to backup folder with better error handling and no skip log verification - PSR logic will be added later
def move_files_to_backup(src_folder, backup_folder, backup_log_file):
    try:
        src_files = os.listdir(src_folder)
        for file_name in src_files:
            src_file_path = os.path.join(src_folder, file_name)
            backup_file_path = os.path.join(backup_folder, file_name)
            shutil.move(src_file_path, backup_file_path)
            with open(backup_log_file, 'a') as log:
                log.write(f"{file_name} moved from {src_folder} to {backup_folder} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            print(f"Moved {file_name} to {backup_folder}")
            logging.info(f"Backed Up {file_name} to {backup_folder}")
    except Exception as e:
        logging.error(f"Error during file backup: {e}")
        print(f"Error during file backup: {e}")

#---------------------------------------------------------------------------Parser----!

# CSV to JSON parser function with better error handling and logging
def parse_csv_to_json(csv_file, json_file, log_file):
    try:
        existing_data, last_pd_no = load_existing_json(json_file)

        # Extract model_id from the first record if available
        model_id = None
        laser_marking_data = existing_data.get("laser_marking", [])
        
        panel_dict = {}

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                serial_no = row['SerialNo']
                panel_no = row['PanelNo']
                panel_time = row['DateTime']
                model_id = row['ModelID']  # Fetch model_id from the CSV file (WO)

                if panel_no.endswith('-T'):
                    # Initialize top panel data in panel_dict
                    panel_dict[serial_no] = {
                        'serial_no': serial_no,
                        'model_id': model_id,
                        'program_name': row['ProgramName'],
                        'top_panel': panel_no,
                        'top_time': panel_time
                    }
                elif panel_no.endswith('-B'):
                    # Add bottom panel data if matching serial_no exists
                    if serial_no in panel_dict:
                        panel_dict[serial_no]['bottom_panel'] = panel_no
                        panel_dict[serial_no]['bottom_time'] = panel_time
                    else:
                        # Initialize bottom panel data if top is missing
                        panel_dict[serial_no] = {
                            'serial_no': serial_no,
                            'model_id': model_id,
                            'program_name': row['ProgramName'],
                            'bottom_panel': panel_no,
                            'bottom_time': panel_time
                        }

                    # Assign pd_no and add to laser_marking_data
                    last_pd_no = generate_pd_no(last_pd_no)
                    panel_dict[serial_no]['pd_no'] = last_pd_no
                    laser_marking_data.append(panel_dict[serial_no])
                    del panel_dict[serial_no]  # Remove after adding

            # Add remaining unmatched entries from panel_dict (single-sided marks)
            for panel_data in panel_dict.values():
                last_pd_no = generate_pd_no(last_pd_no)
                panel_data['pd_no'] = last_pd_no
                laser_marking_data.append(panel_data)

        # Update the model_id field in the JSON data
        existing_data["model_id"] = model_id
        existing_data["laser_marking"] = laser_marking_data

        with open(json_file, 'w') as json_output:
            json.dump(existing_data, json_output, indent=4)

        log_parsed_file(log_file, csv_file)
        print(f"Data from {csv_file} has been parsed and saved to {json_file}")
        logging.info(f"Data from {csv_file} has been parsed and saved to {json_file}")
    
    except Exception as e:
        logging.error(f"Error parsing CSV file {csv_file}: {e}")
        print(f"Error parsing CSV file {csv_file}: {e}")


#-------------------------------------------------------------------------------API---!

# Function to check if any record present for the given mode_id or not
def get_parent_record(model_id, api_key, api_secret, erp_url):
    headers = {
        "Authorization": f"token {api_key}:{api_secret}",
        "Content-Type": "application/json"
    }
    
    # Create the filter dynamically
    filters = f'[["model_id", "=", "{model_id}"]]'
    
    # URL-encode the filter
    encoded_filters = urllib.parse.quote(filters)
    
    # Ensure the erp_url ends without a trailing slash
    if erp_url.endswith('/'):
        erp_url = erp_url[:-1]  # Remove the trailing slash if it exists
    
    # Construct the correct filter URL
    filter_url = f"{erp_url}?filters={encoded_filters}"  # No need to add /api/resource/SMT%20Traceability again
    
    print(f"Request URL: {filter_url}")  # Debugging line
    
    response = requests.get(filter_url, headers=headers)
    
    # Handle HTTP errors
    response.raise_for_status()
    
    result = response.json()  # Get the response data as JSON
    
    # Check if data is returned and extract the name field
    if result.get("data"):
        return result["data"][0]["name"]
    else:
        return None
    
# Function to check if ERP server is reachable
def is_erp_server_running(erp_url, retries=3, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            # Sending a HEAD request to check if server is up
            response = requests.head(erp_url, timeout=10)
            response.raise_for_status()  # Will raise HTTPError for bad responses
            return True  # Server is up
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to ERP server: {e}")
            logging.error(f"Error connecting to ERP server: {e}")
            attempt += 1
            if attempt < retries:
                print(f"Retrying connection in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries reached. ERP server is down.")
                return False

#Send to ERP API call with POST & PUT mode - GET added when parent with child exists - no Overwriting
# Function to handle API requests with logging and error handling
def send_to_erpnext(data, api_key, api_secret, erp_url, retries=3, delay=15, timeout=10):
    logging.info("Triggered API functionality.")
    
    headers = {
        "Authorization": f"token {api_key}:{api_secret}",
        "Content-Type": "application/json"
    }
    
    # Check if ERP server is reachable before proceeding
    if not is_erp_server_running(erp_url, retries=3, delay=5):
        return False  # Exit if the server is not reachable
    
    # Group records by model_id (WorkOrder no.)
    grouped_data = defaultdict(list)
    for record in data:
        grouped_data[record["model_id"]].append(record)

    all_successful = True
    for model_id, records in grouped_data.items():
        # Fetch parent document name based on model_id
        parent_name = get_parent_record(model_id, api_key, api_secret, erp_url)
        logging.info(f"Parent Name: {parent_name}")

        # Preparing child data for the laser_marking field with default values if no data is present
        child_data = [{
            "serial_no": record.get("serial_no", ""),
            "model_id": record.get("model_id", ""),
            "program_name": record.get("program_name", ""),
            "top_panel": record.get("top_panel", ""),
            "top_time": record.get("top_time", ""),
            "bottom_panel": record.get("bottom_panel", ""),
            "bottom_time": record.get("bottom_time", "")
        } for record in records]

        
        attempt = 0
        while attempt < retries:
            try:
                if parent_name:
                    # If parent exists, fetch the existing child records and append new data
                    url = f"{erp_url}/{parent_name}"
                    response = requests.get(url, headers=headers)  # Fetch existing data to avoid overwriting
                    response.raise_for_status()

                    existing_data = response.json()
                    existing_laser_marking = existing_data.get("data", {}).get("laser_marking", [])

                    # Append new data to existing child records
                    existing_laser_marking.extend(child_data)

                    # Now update the parent document with the new combined child data
                    payload = {
                        "laser_marking": existing_laser_marking
                    }
                    response = requests.put(url, headers=headers, data=json.dumps(payload), timeout=timeout)
                else:
                    # If parent doesn't exist, create a new parent document (POST request)
                    url = erp_url
                    payload = {
                        "model_id": model_id,
                        "serial_no": records[0]["serial_no"],
                        "laser_marking": child_data,
                        "docstatus": 0
                    }
                    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
                
                response.raise_for_status()

                if response.status_code == 200:
                    created_doc = response.json()
                    doc_name = created_doc.get("data", {}).get("name", None)

                    if doc_name:
                        print(f"Successfully submitted: {doc_name}")
                        logging.info(f"Successfully submitted: {doc_name}")
                    else:
                        print("Document creation failed, no name returned.")
                        all_successful = False
                else:
                    logging.error(f"Error {response.status_code}: {response.text}")
                    print(f"Error {response.status_code}: {response.text}")
                    all_successful = False
                break  # Exit retry loop if successful

            except requests.exceptions.HTTPError as err:
                # Handle 409 Conflict error for existing data
                if err.response.status_code == 409:
                    logging.warning(f"Conflict (409) for record with model_id {model_id}. Skipping this record.")
                    print(f"Conflict Error 409. Record for model_id {model_id} already exists, skipping.")
                    break  # Exit retry loop as conflict is non-critical and can be skipped
                
                logging.error(f"API request failed on attempt {attempt + 1}/{retries}: {err}")
                print(f"API request failed: {err}")
                attempt += 1
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries reached, giving up.")
                    all_successful = False
                    break

            except requests.RequestException as e:
                logging.error(f"API request failed on attempt {attempt + 1}/{retries}: {e}")
                print(f"API request failed: {e}")
                attempt += 1
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries reached, giving up.")
                    all_successful = False
                    break

    return all_successful

# When JSON File successfully processed, move to Done Folder
def move_to_done_folder(json_file):
    try:
        if os.path.exists(json_file):  # Check if the file exists
            done_folder = folders["Done_Folder"]
            shutil.move(json_file, os.path.join(done_folder, os.path.basename(json_file)))
            logging.info(f"Moved {json_file} to Done Folder.")
            print(f"Moved {json_file} to Done Folder.")
        else:
            logging.error(f"File not found: {json_file}")
            print(f"File not found: {json_file}")
    except Exception as e:
        logging.error(f"Error moving file to Done Folder: {e}")
        print(f"Error moving {json_file} file to Done Folder: {e}")
        

# Main task workflow with user-specified schedule frequency - CGC-2 - cmd_12.py additions for existing json file handling
def task_workflow(api_key, api_secret, erp_url, machine_data_folder):
    # 1. Process pending JSON files from JSON_Data_Folder first
    process_pending_json_files(api_key, api_secret, erp_url)

    # 2. mvf.py: Copy new files from machine_data_folder to Scan_Folder
    copy_log_file = get_log_file_path("Copy_Logs", datetime.now().strftime('%Y-%m-%d'))
    copy_new_files(machine_data_folder, folders["Scan_Folder"], copy_log_file)

    # 3. psr.py: Parse CSV files to JSON in Scan_Folder
    log_file = get_log_file_path("Parser_Logs", datetime.now().strftime('%Y-%m-%d'))
    json_file = os.path.join(folders["JSON_Data_Folder"], f"data_{datetime.now().strftime('%Y-%m-%d_%H_%M')}.json")
    csv_files = [file for file in os.listdir(folders["Scan_Folder"]) if file.endswith('.csv')]
    
    for csv_file in csv_files:
        parse_csv_to_json(os.path.join(folders["Scan_Folder"], csv_file), json_file, log_file)
        logging.info(f"JSON file created {json_file}")

    # 4. Process the newly created JSON file
    process_json_file(json_file, api_key, api_secret, erp_url)

    # 5. Backup: Move files to Backup_Folder
    backup_log_file = get_log_file_path("Backup_Logs", datetime.now().strftime('%Y-%m-%d'))
    move_files_to_backup(folders["Scan_Folder"], folders["Backup_Folder"], backup_log_file)


# Process pending JSON files first before new ones
def process_pending_json_files(api_key, api_secret, erp_url):
    pending_json_files = [file for file in os.listdir(folders["JSON_Data_Folder"]) if file.endswith('.json')]
    for json_file in sorted(pending_json_files):  # Ensuring oldest files are processed first
        process_json_file(os.path.join(folders["JSON_Data_Folder"], json_file), api_key, api_secret, erp_url)

# Process each JSON file by loading its content, sending data to ERP, and moving it to Done folder
def process_json_file(json_file, api_key, api_secret, erp_url):
    existing_data, last_pd_no = load_existing_json_2(json_file)
    
    # Debugging: Print the type and contents of existing_data to verify its format
    # print("Type of existing_data:", type(existing_data))
    # print("Contents of existing_data:", existing_data)

    if existing_data:  # Only proceed if data exists
        all_successful = True

        # Adjust iteration based on the format of existing_data
        if isinstance(existing_data, dict) and "laser_marking" in existing_data:
            # When existing_data is a dictionary with a laser_marking key
            for record in existing_data["laser_marking"]:
                success = send_to_erpnext([record], api_key, api_secret, erp_url)
                if not success:
                    all_successful = False
                    break
        elif isinstance(existing_data, list):
            # If it's a list, directly process all records
            success = send_to_erpnext(existing_data, api_key, api_secret, erp_url)
            if not success:
                all_successful = False

        # If processing was successful, move the file to the 'Done' folder
        if all_successful:
            move_to_done_folder(json_file)
            # print("moved to done!")

        return all_successful
    else:
        print("No data found to process in the JSON file.")
        return False


# Helper function to get log file path for different operations
def get_log_file_path(log_type, date_str):
    return os.path.join(log_folders[log_type], f"{log_type.lower()}_{date_str}.log")

# Helper function to log parsed CSVs
def log_parsed_file(log_file, csv_file):
    with open(log_file, 'a') as log:
        # log.write(f"Parsed {csv_file} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Parsed {csv_file} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Helper function to load existing JSON data - Parser
def load_existing_json(json_file):
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Ensure data is a dictionary and has the structure we expect
        if not isinstance(data, dict):
            data = {"model_id": "", "laser_marking": []}
        
        # Access the 'laser_marking' list from the loaded data
        laser_marking_data = data.get('laser_marking', [])
        
        if laser_marking_data:
            last_pd_no = laser_marking_data[-1].get('pd_no', "PD0000")
        else:
            last_pd_no = "PD0000"  # Default value if there is no data in laser_marking
        
        return data, last_pd_no
    else:
        return {"model_id": "", "laser_marking": []}, "PD0000"  # Return empty data with laser_marking list


# Helper function to load existing JSON data - API
def load_existing_json_2(json_file):
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Access the 'laser_marking' list from the loaded data
        laser_marking_data = data.get('laser_marking', [])
        
        if laser_marking_data:
            last_pd_no = laser_marking_data[-1]['pd_no']
        else:
            last_pd_no = "PD0000"  # Default value if there is no data in laser_marking
        
        return laser_marking_data, last_pd_no
    else:
        return [], "PD0000"  # Return empty list and default PD0000 if file does not exist


# Helper function to generate the next PD number
def generate_pd_no(last_pd_no):
    number = int(last_pd_no[2:]) + 1
    return f"PD{number:04d}"

# Function to reset config data for API key, API secret, ERP URL, and machine data folder
def reset_config_file():
    # Ask the user for a password
    entered_password = input("Enter password to reset configuration: ")

    if entered_password == RESET_PASSWORD:
        print("Password accepted. Resetting configuration...")
        
        # Prompt for new inputs
        api_key = input("Enter new API Key (api.py): ")
        api_secret = input("Enter new API Secret (api.py): ")
        erp_url = input("Enter new ERP URL (api.py): ")
        machine_data_folder = input("Enter new Machine Target DATA folder Path (mvf.py): ")
        logging.info("User Input Registered. Config.json file changed")
        
        # Load the existing config file
        config_file = os.path.join(current_directory, "config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # Update only the necessary fields
            config_data["API_Key"] = api_key
            config_data["API_Secret"] = api_secret
            config_data["ERP_URL"] = erp_url
            config_data["Machine_Data_Folder"] = machine_data_folder

            # Write the updated config back to the file
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=4)

            print("Configuration reset successfully!")
            logging.info("RESET Successfull.")
        else:
            print("Error: Config file not found. Unable to reset.")
            logging.info("RESET Unsuccessfull.")
    else:
        print("Incorrect password. Returning to normal operation...")
        logging.info("RESET Unsuccessfull. Incorrect Password.")

# Function to check for 'STOP' or 'RESET' input in a separate thread
def control_program():
    while True:
        user_input = input("Program Started Successfully... \nType 'STOP' to exit or 'RESET' to reset configuration: ").strip().upper()

        if user_input == 'STOP':
            print("Stopping program...")
            logging.info("Program Stopped.")
            os._exit(0)

        elif user_input == 'RESET':
            print("Resetting configuration...")
            logging.info("Reset Called.")
            reset_config_file()

# Function to create and start the control thread
def start_control_thread():
    control_thread = threading.Thread(target=control_program)
    control_thread.daemon = True  # Daemon thread will not block program exit
    control_thread.start()

# Main execution logic
def main():
    logging.info("Program started by the user.")
    create_folders()

    # Load inputs from config file if it exists, otherwise prompt user
    config = load_inputs_from_file()
    if config:
        api_key = config["API_Key"]
        api_secret = config["API_Secret"]
        erp_url = config["ERP_URL"]
        machine_data_folder = config["Machine_Data_Folder"]
    else:
        api_key, api_secret, erp_url, machine_data_folder = get_inputs()
        write_folder_paths_to_file(api_key, api_secret, erp_url, machine_data_folder)

    # Scheduling frequency as user input
    schedule_freq = input("Enter the scheduling frequency in minutes: ")
    try:
        schedule_freq = int(schedule_freq)
    except ValueError:
        print("Invalid input. Setting default scheduling frequency to 10 minutes.")
        schedule_freq = 10

    # Schedule the task workflow at the user-defined interval
    schedule.every(schedule_freq).minutes.do(task_workflow, api_key, api_secret, erp_url, machine_data_folder)

    # Start a separate thread to monitor the STOP and RESET commands
    start_control_thread()

    # Keeps script running to execute the scheduled tasks. Catching ISR calls
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program stopped by the user.")
        logging.info("Program stopped by the user using Keyboard Interrupt.")


if __name__ == "__main__":
    main()
