# ICECAP - sea-Ice Calibration, vErifiCAtion and Products

ICECAP  is a python-based software tool developed within the EU Horizon 2020 project ACCIBERG. ICECAP is developed to handle validation and calibration of Northern-hemisphere sea-ice forecasts provided by the project partners, CMEMS and C3S.

**DISCLAIMER**
This project is **BETA** and will be **Experimental** for the foreseeable future.
Interfaces and functionality are likely to change, and the project itself may be scrapped.
**DO NOT** use this software in any project/software that is operational.

### Installation
Clone source code repository

    $ git clone https://github.com/ecmwf/ICECAP 

To install ICECAP in a Linux environment with its full capabilities execute the following command:
    
    $ make

If you are unable to execute the Makefile you can follow the steps below to install ICECAP. Create conda environment and install necessary packages

    $ cd ICECAP
    $ conda remove --name icecap --all  # delete icecap env if it exists
    $ conda config --set channel_priority flexible
    $ conda env create -f environment.yml 

Installation has been tested successfully linux x86-64 (ATOS HPC). 
Installation might also work on osx-arm64 (Macbook M2) using the environment.yaml file in /etc.

### Usage
Please follow the section 1.2 in the user guide how to set up your machine. 
An example how to run ICECAP is provided Section 3.1.

The user guide is located in the doc/ directory. Compile it using the Makefile

    $ cd doc
    $ make



### License

Copyright 2024 European Centre for Medium-Range Weather Forecasts (ECMWF)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

In applying this licence, ECMWF does not waive the privileges and immunities
granted to it by virtue of its status as an intergovernmental organisation nor
does it submit to any jurisdiction.

