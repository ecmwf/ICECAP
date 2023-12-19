# ICECAP - sea-Ice Calibration, vErifiCAtion and Products

ICECAP  is a python-based software tool developed within the EU Horizon 2020 project ACCIBERG. \ice is developed to handle validation and calibration of Northern-hemisphere sea-ice forecasts provided by the project partners, CMEMS and C3S.

**DISCLAIMER**
This project is **BETA** and will be **Experimental** for the foreseeable future.
Interfaces and functionality are likely to change, and the project itself may be scrapped.
**DO NOT** use this software in any project/software that is operational.

### Installation
Clone source code repository

    $ git clone https://git.ecmwf.int/scm/~nedb/icecap.git

Create conda environment and install necessary packages

    $ conda remove --name icecap --all  # delete icecap env if it exists
    $ conda env create -f environment.yml 

### Usage
Please follow the section 1.2 in the user guide how to set up your machine. 
An example how to run ICECAP is provided Section 1.3.


### License

Copyright 2023 European Centre for Medium-Range Weather Forecasts (ECMWF)

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

