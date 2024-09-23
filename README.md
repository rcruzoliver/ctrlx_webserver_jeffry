# ctrlx-webserver

May 2024, DCEM Bosch Rexroth

Contact: Jeffry Joseph (jeffry.joseph@boschrexroth.ch) 

## Introduction

This repository contains the source code to build your own custom user interface based on a Python Flask webserver. 

The custom webserver is available through the port 5000. 

For complementary, we are showing that the basic web interface provided by ctrlX OS is available in the port 8443.

### Platform notes

We assume the reader has access to the ctrlX SDK and all the dependencies to build the python examples from such SDK are installed in the system in which this project is going to be compiled, if you are working in an the App-Build enviroment, the dependencies will be most likely installed in the system already. 

Apart from having such dependencies installed in the system (basically the datalayer and zmq packages, and of course snapcraft), this project is self contained and this repository can be cloned in any directory in your system and the automatic build scripts must run without errors.

## Files description

### Project README and LICENSE
- **README.md**
- **LICENSE**

### Snap build 
- **snap/snapcraft.yalm** : it contains the instructions to build the snap package
- **build-snap-amd64.sh** : it builds automatically the snap for amd64 platforms using snapcraft.
- **build-snap-arm64.sh** : it builds automatically the snap for arm64 platforms using snapcraft.

### Webserver backend
- **main.py** : it constaint the backend implementation

###  Webserver frontend
- **static/\*** : it contains javascript and css files
- **templates/index.html** : it constains the frontend implementation, with embedded javascript code

### Compilation tools
- **bin/comm.datalayer/ubuntu22-gcc-x64/release/mddb_compiler** : tool to compile metadata files (.csv) into binary (.mddb)

### App manager and configuration
- **appdata/appdatacontrol.py** : functionalies to manage snap inside ctrlX OS
- **config/package-assets/ctrlx-webserver.package-manifest.json** : definitions to manage the snap inside ctrlX OS

### Documentation
- **docs/images\*** : images used in the README.md

### Python package setup files
- **setup.py**
- **setup.cfg**

### Other files
- **install-venv.sh** : automatically install the required packaged in virtual environment
- **requirements.txt** : dependenciies list that will be installed 
- **venv/\*** : it contains dependencies needed when working in a virtual environement
- **settings.py**


## Implementation information
This section contains practical information for custom implementations of datalayer nodes.

## Function Description

There will be an How To one can use to get an idea of the main functionalities of the app.

The main script will start with a delay of 10s and is structured in rough terms as follow:

- In a first step some settings and variables are initialized.

- In a second step an initial Registration of a JSON file is done if some criteria are satisfied (if a file is in the file system that starts 
  with 'AfterReboot' and ends with '.json').

- 'index.html' will be rendered.

- In the 'upload' route a function is defined which is associated with the 'Upload' button that is used to upload the CSV file. Note that 
  the variable 'message' indicates weather there are errors. If there are some errors, one can not proceed.

- In a 'update' route which is associated with the 'Create JSON File' button contains a method to create and save the JSON files from 
  information provided in the CSV File.

- In the 'register' route which is associated with the 'Register' button contains a method to register a JSON file. Note that once a JSON file 
  is registered the 'registered_json' variable will be updated. Also note that after registration a copy of the JSON file will be created
  (that starts with 'AfterReboot' and ends with '.json'). This is the same file mentioned above. In case of a reboot this file will be searched 
  and our software knows which file is to be registered initially.

- In the 'unregister' route which is associated with the 'Unregister' button contains a method to unregister a JSON file. Note that in case of an 
  initial unregistration after a reboot, the data layer needs to be written twice for some reason. Also note that the 'registered_json' variable mentioned above
  will be set to 'None' and the copy of the JSON file that was created during the registration will be deleted again.  
  