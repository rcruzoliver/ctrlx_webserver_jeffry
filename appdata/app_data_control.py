# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT

import os
import platform
import datetime
import json
import time
import csv
from flask import Flask, request

#This is a function to check if the required headers are available
def check_headers(reader):
    required_headers = {"product name", "mainDiag No", "detailedDiagnostics No"}
    text_prefix = "text-"

    # Get the actual headers from the reader
    headers = reader.fieldnames

    # Check for "product name", "mainDiag No" and "detailedDiagnostics No"
    has_required_headers = required_headers.issubset(headers)

    # Check for headers that start with 'text-'
    has_text_headers = any(header.startswith(text_prefix) for header in headers)

    return has_required_headers and has_text_headers


# This method converts data from CSV format to JSON format
def convert_csv_to_json(csv_path):
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=';')
        rows = list(reader)
        product_name = str(rows[0]['product name'])
        
    languages = [header.split('-')[1] for header in reader.fieldnames if header.startswith('text-')]
    json_data_list = []   

    for i, lang in enumerate(languages): 

        main_diagnostics = {}
        current_main_diag_no = None

        for row in rows:
            main_diag_no = row['mainDiag No']
            detailed_diag_no = row['detailedDiagnostics No']
            text = row[f'text-{lang.upper()}']
            
            
            if main_diag_no:
                current_main_diag_no = main_diag_no
                main_diagnostics[str(current_main_diag_no)] = {
                    "text": text,
                    "version": 1
                }
                        
            if detailed_diag_no and current_main_diag_no:
                if 'detailedDiagnostics' not in main_diagnostics[str(current_main_diag_no)]:
                    main_diagnostics[str(current_main_diag_no)]['detailedDiagnostics'] = {}
                    
                main_diagnostics[str(current_main_diag_no)]['detailedDiagnostics'][str(detailed_diag_no)] = {
                    "text": text
                    }
        
            json_data = {
                "product": product_name,
                "mainDiagnostics": main_diagnostics
            }

        json_data_list.append(json_data)        
    
    return json_data_list, languages


#This class manages methods that manipulates the file system of the ctrlX CORE 
class AppDataControl():
    """AppDataControl
    """
    def __init__(self, storage_folder_name="diagnostics", storage_file_name="Diag.csv"):
        """__init__
        """
        # The name of the application storage folder
        # MUST be same as specified in your *.package-manifest.json file
        self.storage_folder_name = storage_folder_name

        # The name of the storage file
        self.storage_file_name = storage_file_name

        # Gets the base storage location for all applications
        if 'SNAP' in os.environ:
            self.common_path = os.getenv("SNAP_COMMON")
        else:
            self.common_path = os.getcwd()
        self.base_storage_location = os.path.join(
            self.common_path, "solutions", "activeConfiguration")

        # Gets the application data storage location
        self.storage_location = os.path.join(
            self.base_storage_location, self.storage_folder_name)

        # Gets the application data storage file
        self.storage_file = os.path.join(
            self.storage_location, self.storage_file_name)


    #The following method uploads a file in the file system
    def upload(self, file):
        result = AppDataControl.ensure_storage_location(self)

        if result is True:
            if file.filename == "Diag.csv":
                filepath = os.path.join(self.storage_location, file.filename)
                file.save(filepath) 
                return True      
            else:
                return False                    


    #In the following method JSON files will be created and saved in the file system
    def save(self):
        """save
        """
        print("INFO Starting save routine", flush=True)

        # Check if storage location exists
        result = AppDataControl.ensure_storage_location(self)

        # If storage location ensured, save appdata to file
        if result is True:
            path = self.storage_file     
            csv_path = self.storage_file
            json_list, language_list = convert_csv_to_json(csv_path)

            for i, language in enumerate(language_list):   
                json_path = os.path.join(self.storage_location, f'Diag{language.upper()}.json')

                # Ensure the directory exists
                os.makedirs(os.path.dirname(json_path), exist_ok=True)

                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(json_list[i], json_file, ensure_ascii=False, indent=2)
                    
            print("INFO Saved application data to file: '", path, flush=True)
            return True     
            
        print("ERROR Saving application data not possible", flush=True)
        return False


    #This method ensures the storage location
    def ensure_storage_location(self):
        """ensure_storage_location
        """
        # Check if storage location exist
        path = self.storage_location

        # If app is running as snap, check if content interface was mounted successfully
        if 'SNAP' in os.environ:
            solutions_path = os.path.join(self.common_path, "solutions")
            for i in range(4):
                print("INFO Check if content interface is mounted", flush=True)
                if os.path.isdir(solutions_path) is False:
                    print("ERROR Content interface is not mounted: Attempt", i+1, flush=True)
                    time.sleep(1.0)
                    if i >= 4:
                        return False
                else:
                    print("INFO Content interface is mounted", flush=True)

        if os.path.isdir(path) is False:
            try:
                print("INFO Creating storage location: ", path, flush=True)
                os.makedirs(path)
            except OSError:
                print("ERROR Creating storage location", path, "failed!", flush=True)
                return False

        return True


    #This method lists all JSON files in the file system that starts with 'Diag' and ends with '.json'
    def list_json_files(self):
        directory_path = self.storage_location
        try:
            # Check if the directory exists
            if not os.path.isdir(directory_path):
                print(f"The directory {directory_path} does not exist.")
                return []

            # List all files in the directory
            files = os.listdir(directory_path)

            # Filter out only JSON files
            json_files = [file for file in files if file.endswith('.json') and file.startswith('Diag')]

            # Return the list of JSON files
            return json_files

        except Exception as e:
            print(f"An error occurred: {e}")
            return []        


    #The following method creates a copy of a json file. Note that the copy will have a different name that starts with 'AfterReboot' and ends with '.json'
    def copy_json_file(self, FileName):
        if FileName is not None:
            source_path = os.path.join(
                self.storage_location, FileName)            
            with open(source_path, 'r', encoding='utf-8') as source_file:
                data = json.load(source_file) 
            copy_path = os.path.join(
                self.storage_location, f"AfterReboot-{FileName}")
            with open(copy_path, 'w', encoding='utf-8') as destination_file:
                json.dump(data, destination_file, ensure_ascii=False, indent=2)
                 

    #The following method searches and deletes the file in the file system that starts with 'AfterReboot' and ends with '.json'
    def delete_after_reboot_json(self):        
        files = os.listdir(self.storage_location)
        if files is not None:            
            for file in files:                
                if file.startswith('AfterReboot') and file.endswith('.json'):
                    file_path = os.path.join(self.storage_location, file)
                    try:                        
                        os.remove(file_path)
                        print(f"Deleted file: {file}")
                    except OSError as e:
                        print(f"Error deleting file {file}: {e}")
        
    
    #This Method searches a file in the file system that starts with 'AfterReboot' and ends with '.json'
    def search_file_after_reboot(self):
        directory_path = self.storage_location         
        if not os.path.isdir(directory_path):
            print(f"The directory {directory_path} does not exist.")
            return None         
        files = os.listdir(directory_path)
        after_reboot_file = None
        for file in files:
            if file.startswith('AfterReboot') and file.endswith('.json'):
                after_reboot_file = file
                break  # Exit the loop once the file is found
        return after_reboot_file  


    #This method searches for errors in the CSV file 
    def search_for_error(self):      
        message = {}
        languages = None 
        csv_path = self.storage_file     
        with open(csv_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=';')
            rows = list(reader)
            languages = [header.split('-')[1] for header in reader.fieldnames if header.startswith('text-')]  

            print("INFO check headers correctness: ", check_headers(reader), flush=True)
            if not check_headers(reader):
                message['Error in headers'] = "Please make sure all required headers are available"
                return message

        print("INFO languages: ", languages, flush=True)

        product_name = str(rows[0]['product name'])
        if not product_name:
            message['No product name'] = "Please enter product name in row 2"
            return message
            
        previous_detailed_no = None  
        previous_main_no = None   
        for i, row in enumerate(rows):
            excel_row = i + 2

            if not row['mainDiag No'] and not row['detailedDiagnostics No']:
                if not all(not value for value in row.values()): #if row in excel is not empty
                    message[f'No main diagnostic number in row {excel_row}'] = "Please enter main diagnostic number"

            if row['detailedDiagnostics No']:
                if previous_detailed_no is not None and previous_main_no is not None:
                    if not previous_detailed_no and not previous_main_no:                       
                        message[f'No main diagnostic No. for detailed diagnostic No. in row {excel_row}'] = "Please make sure that every detailed diagnostic No. has a corresponding main diagnostic No."                 
             
            if row['mainDiag No'] and row['detailedDiagnostics No']:
                message[f'Error in handling diagnostic No. in row {excel_row}'] = "Please make sure that either main or detailed diagnostic No. is described"
                
            empty_languages = []
            for j, lang in enumerate(languages): 

                if row['mainDiag No']:

                    DiagCopyString = str(row['mainDiag No'])   

                    if len(DiagCopyString) != 8:
                        message[f'size of main diagnostic number not correct in row {excel_row}'] = "Check documentation" 
                        return message                              
                    
                    if DiagCopyString[0] in '0123456789ABCDEF' and DiagCopyString[1] in '0123456789ABCDEF':
                        if (int(DiagCopyString[:2], 16) != 0x0E) and (int(DiagCopyString[:2], 16) != 0x0F) and not (0x30 <= int(DiagCopyString[:2], 16) <= 0x37):
                            message[f'Invalid main diagnostic number (first two digits) in row {excel_row}'] = "Check documentation"    
                    else:
                        message[f'Invalid main diagnostic number (first two digits) in row {excel_row}'] = "Check documentation"            

                    if DiagCopyString[2] in '01':
                        if (int(DiagCopyString[2], 2) != 0b0) and (int(DiagCopyString[2], 2) != 0b1):
                            message[f'Invalid main diagnostic number (third digit) in row {excel_row}'] = "Check documentation"                    
                    else:
                        message[f'Invalid main diagnostic number (third digit) in row {excel_row}'] = "Check documentation"

                    if DiagCopyString[3] in '0123456789ABCDEF':
                        if (int(DiagCopyString[3], 16) != 0xA) and (int(DiagCopyString[3], 16) != 0xE)  and (int(DiagCopyString[3], 16) != 0xF):
                            message[f'Invalid main diagnostic number (4th digit) in row {excel_row}'] = "Check documentation"                    

                        if DiagCopyString[4] in '0123456789' and DiagCopyString[5] in '0123456789ABCDEF' and DiagCopyString[6] in '0123456789ABCDEF' and DiagCopyString[7] in '0123456789ABCDEF':
                            if (int(DiagCopyString[3], 16) == 0xA):
                                if not (0x0000 <= int(DiagCopyString[-4:], 16) <= 0x0FFF):    
                                    message[f'Invalid main diagnostic number (last four digits) in row {excel_row}'] = "Check documentation"

                            if (int(DiagCopyString[3], 16) == 0xE):
                                if not (0x0000 <= int(DiagCopyString[-4:], 16) <= 0x0FFF):    
                                    message[f'Invalid main diagnostic number (last four digits) in row {excel_row}'] = "Check documentation"

                            if (int(DiagCopyString[3], 16) == 0xF):
                                if (int(DiagCopyString[4]) != 0) and (int(DiagCopyString[4]) != 2) and (int(DiagCopyString[4]) != 6) and (int(DiagCopyString[4]) != 8) and (int(DiagCopyString[4]) != 9):
                                    message[f'Invalid main diagnostic number (5th digit) in row {excel_row}'] = "Check documentation"

                                if not (0x000 <= int(DiagCopyString[-3:], 16) <= 0xFFF):    
                                    message[f'Invalid main diagnostic number (last three digits) in row {excel_row}'] = "Check documentation"                    
                        else:
                            message[f'Invalid main diagnostic number (last four digits) in row {excel_row}'] = "Check documentation"
                    else:
                        message[f'Invalid main diagnostic number (4th digit) in row {excel_row}'] = "Check documentation"  

                    utf8_length = len(str(row[f'text-{lang.upper()}']).encode('utf-8'))
                    if utf8_length > 60:
                        message[f'text-{lang.upper()} too long in row {excel_row}'] = "Please shorten the text" 

                elif row['detailedDiagnostics No']:
                    utf8_length = len(str(row[f'text-{lang.upper()}']).encode('utf-8')) 
                    if utf8_length > 250:
                        message[f'text-{lang.upper()} too long in row {excel_row}'] = "Please shorten the text" 

                if not row[f'text-{lang.upper()}']:
                    empty_languages.append(lang.upper())
                    print(f"In row {excel_row}", f'text-{lang.upper()}', "is empty") 

            if empty_languages:
                if not all(not value for value in row.values()): #if row in excel is not empty
                    message[f'Empty text in row {excel_row}'] = empty_languages 

            previous_detailed_no = row['detailedDiagnostics No']   
            previous_main_no = row['mainDiag No']    
        
        return message  



