#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2021 Bosch Rexroth AG
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from flask import Flask, render_template, jsonify, request, Blueprint, redirect, url_for
import os

import faulthandler
import signal
import sys
import time

import ctrlxdatalayer
from ctrlxdatalayer.variant import Result, Variant, VariantType

from appdata.app_data_control import AppDataControl

time.sleep(10)

message = None
global_json_files = None 
registered_json = None
successfully_saved = None

if 'SNAP' in os.environ:
    root_path = os.getenv("SNAP")
    connection_string = "ipc://"
else:
    root_path = os.getcwd()
    connection_string = "tcp://boschrexroth:boschrexroth@10.0.2.2?sslport=8443"

template_path = root_path + '/templates'
static_path = root_path + '/static'

# Binary sampleSchema file
bfbs_file = root_path + "/bfbs/robotActualValues.bfbs"

# Binary metadata file
mddb_file = root_path + "/mddb/metadata.mddb"

# addresses of provided values
address_base = "webserver/"

bp = Blueprint('webserver',__name__, static_folder=static_path, template_folder=template_path)

datalayer_system = ctrlxdatalayer.system.System("")
datalayer_system.start(False)

datalayer_client = datalayer_system.factory().create_client(connection_string)

app_data_control = AppDataControl()

if datalayer_client is None:
    print("WARNING Connecting", connection_string, "failed.")
    datalayer_system.stop(False)
    sys.exit(1)


def has_non_empty_value(d):
    return any(d.values())


#Method for an (initial) registration
def initial_registration(file_name):
    global registered_json
    file_name_initial = str(file_name.split('-')[1])
    original_path = "/var/snap/rexroth-solutions/common/solutions/DefaultSolution/configurations/appdata/diagnostics"
    path_to_write = f"{original_path}/{file_name_initial}"
    with Variant() as data:
        data.set_string(path_to_write) 
        print("INFO Ready to write", flush=True)        
        result, variant = datalayer_client.write_sync("diagnosis/registration/register-file", data) 
        print("INFO result of writing:", result, flush=True)
        if (result != Result.OK):
            print("INFO Result not OK", flush=True)
            sys.exit(1)
        if (result == Result.OK):                 
            print("INFO Written", flush=True)
            registered_json = file_name_initial  
            

#Check if there are initial Files to register e.g. after a reboot
bInitial = None
InitialRegistration = app_data_control.search_file_after_reboot()
print("INFO Initial File: ", InitialRegistration, flush=True)
if InitialRegistration is not None:
    bInitial = True
    print("INFO Ready for initial registration", flush=True)
    initial_registration(InitialRegistration)


@bp.route('/')
def index():
    return render_template('index.html', json_files=global_json_files, registered_json=registered_json, message=message, successfully_saved=successfully_saved) 

#Upload file
@bp.route('/api/upload_file', methods=['POST'])
def upload_file():  
    global message
    global successfully_saved
    file = request.files['file']
    if file:
        successfully_saved = app_data_control.upload(file)
        time.sleep(1)
        if successfully_saved:
            message = app_data_control.search_for_error()
        elif successfully_saved is False:
            message = {"Upload failed": "Please upload the Diag.csv file."}
    return redirect(url_for('webserver.index'))


#API to update
@bp.route('/api/update', methods=['POST'])
def update_route():
    global global_json_files
    app_data_control.save() 
    global_json_files = app_data_control.list_json_files()
    print(global_json_files)
    
    return redirect(url_for('webserver.index'))


#API to register
@bp.route('/api/datalayer/register', methods=['POST'])
def register_route():
    global registered_json
    selected_file = request.form.get('selected_file')
    if selected_file:
        selected_file = str(selected_file) 
        original_path = "/var/snap/rexroth-solutions/common/solutions/DefaultSolution/configurations/appdata/diagnostics"
        path_to_write = f"{original_path}/{selected_file}"
        with Variant() as data:
            data.set_string(path_to_write) 
            result, variant = datalayer_client.write_sync("diagnosis/registration/register-file", data) 
            if (result == Result.OK):
                registered_json = selected_file  
                if registered_json is not None:
                    app_data_control.copy_json_file(registered_json)    
    
    return redirect(url_for('webserver.index'))


#API to unregister
@bp.route('/api/datalayer/unregister', methods=['POST'])
def unregister_route():
    global registered_json
    global bInitial
    if registered_json is not None:
        original_path = "/var/snap/rexroth-solutions/common/solutions/DefaultSolution/configurations/appdata/diagnostics"
        path_to_write = f"{original_path}/{registered_json}"
        print("INFO path to unregister: ", path_to_write, flush=True)
        with Variant() as data:
            data.set_string(path_to_write)
            print("INFO json path data to unregister: ", data, flush=True)
            result, variant = datalayer_client.write_sync("diagnosis/registration/unregister-file", data)
            print("INFO result of writing:", result, flush=True)
            if (result != Result.OK):
                print("INFO Result not OK", flush=True)
            if not bInitial and (result == Result.OK):
                app_data_control.delete_after_reboot_json()  
                registered_json = None  
            
            elif (bInitial == True) and (result == Result.OK):
                result2, variant2 = datalayer_client.write_sync("diagnosis/registration/unregister-file", data)
                print("INFO result of writing:", result2, flush=True)
                if (result2 != Result.OK):
                    print("INFO Result not OK", flush=True)
                if (result2 == Result.OK):
                    bInitial = False                
                    app_data_control.delete_after_reboot_json()  
                    registered_json = None       
    
    return redirect(url_for('webserver.index'))


app = Flask(__name__)
app.secret_key = 'Hello'
app.register_blueprint(bp, url_prefix='/webserver')

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0') 
