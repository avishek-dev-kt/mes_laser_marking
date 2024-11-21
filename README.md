# General SMT MES
- All four programs are developed to capture data from their respective target machine folder and convert it into a standard structured json file according to doctype structure in ERP. Before sending via REST API calls.

- All programs generate there respective program execution logs in the same folder as the program. Ex:- LM_app.log 

- pd_no is used to remember where to input new data in an existing json file by the program. It is not sent to ERP.

- All files are created with date and time extension just to avoid naming collision, overwritting and proper file structure. this includes all logs. 

- All program creates required folder automatically in the same directory as the program. Laser marking does not create any Skipped_Logs folders or file as there is no NG data in LM.

- LM Programs creates Doctype in ERP with WO number. its the starting of all the programs but yet is independent like all others.

- The parsed JSON file created by the LM program when moved to Done_Fodler is required by other programs for checking the serial_no presence and if present then grabbing the model_id no. from that file.

# LM File Sending to SPI, PAOI & AOI
- This parsed JSON file of LM is supposed to be sent to other MES machine via LAN FTP with Task Scheduler as all the SMT lines machine runs on Windows. (Automation program in development along with required pyhton module installation and monitoring)
    > Folder 1 - Contains 24 Hours Old Data
    > Folder 2 - Contains 48 Hours Old Data

- This is being done to reduce the no. of API calls on the server. All processing done on local system and then push to ERP.

# ERP
- Say SMT Traceability is the doctype name in which lists are created using Work Order number name, then LM will create a List using the Work order Number present in its file for each serial number and push the respective laser marking data to that lists child table named laser_marking.

- Similarly SPI will check the presence of the following WO number in ERP and when its found in the ERP it will push the data to that list.

- Program Copies the data from Machine Data Folder to Scan_Folder. From there the files are picked up one by one and parsed to JSON format from CSV or XML with filtering. After that, the JSON files data are sent to ERP respective documents. When Succes, the JSON file is then moved from JSON_Data_Folder to Done_folder.

- The successfully parsed file from Scan_Folder is then moved to Backup_folder.

- All of these file movements is recorded in log files for reference. These log filesa are kept in Logs_Folder.

# Backup, Skip & Serial_no
- In SPI, PAOI & AOI Program, There's addition of 2 more logics- 
    > Chek Serial No & Skipped Files - The files from Scan_Folder is first checked in Laser Marking JSON data's via serial_no. Once Found Then Work order no. is grabbed from that file for that serial_no and then the file is parsed or else that file is skipped for the time being and an entry is made in the Skipped_Logs.

    > The backup logic works upon checking file names present in Parsed_Logs and NOT present in Skipped_Logs. If YES, Copy else Don't.

- Programs needs to be kept in Windows Task Scheduler to Automatically start when system starts. The Frquency still needs to be given as input by a user. no default value given due to synchronization issue and shift timing difference.

# Config
- LM Inputs - SAMPLE - LM_Sample_config.json
- SPI, PAOI & AOI Inputs - AOI_Sample_config.json

- Inputs Required - 
    > LM
    "API_Key": "4f4e2fd646a****",
    "API_Secret": "2ffc9a0f6a1****",
    "ERP_URL": "http://0.0.0.0:8001/api/resource/SMT%20Traceability",
    "Machine_Data_Folder": "/home/kaynes/MES_Project/Machine_Data_Folder/Laser_Marking",
    Enter the scheduling frequency in minutes : 60

    > SPI, PAOI & AOI
    "API_Key": "4f4e2fd646a****",
    "API_Secret": "2ffc9a0f6a1****",
    "ERP_URL": "http://0.0.0.0:8001/api/resource/SMT%20Traceability",
    "Machine_Data_Folder": "/home/kaynes/MES_Project/Machine_Data_Folder/AOI",
    "LM_JSON_FOLDER": "/home/kaynes/Desktop/AOI/Z_LM_data/New",
    "LM_BKP_JSON_FOLDER": "/home/kaynes/Desktop/AOI/Z_LM_data/Old",
    Enter the scheduling frequency in minutes : 60 

    - For Invalid scheduling frequency, the time is set to 10 mins. (For Testing Edge Cases)
    - API Key & API Secret is taken from Account - Settings - API Access
    - ERP_URl is ERP Document URL.
    - Machine_Data_Folder - Target folder from where program will capture only new files for processing.
    - LM Folders - For Verifying Serial No. Existence and grabbing WO no. as it is only present consistently in LM data. 
    - All this data is stored inside a config.json file so when the next time program starts, the inputs are loaded from this file
    - to reset this entry, just type RESET. (Password needs to be set on each system inside an environmrnt variable for security. Default password is also present.)

# Extras
- Still in development.
- Testing going on, Codes Commented in respective programs.
