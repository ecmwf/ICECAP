# ICECAP Notebook to derive the distance to the sea ice edge frmo an open water location

#### This notebook produces a line plot indicating the predicted distance of the chosen location to the sea ice edge based on the specified TOPAZ5 medium-range forecast.


<div class="alert alert-block alert-danger"> 
    
#### No changes are necessary in the first cell. 
</div>

```python
""" DON'T CHANGE ANYTHING HERE"""

""" Load ICECAP """
# this seems necessary as otehrwise ESMFMKFILE is not defined 
# https://github.com/conda-forge/esmf-feedstock/issues/91
import os
from pathlib import Path
os.environ['ESMFMKFILE'] = str(Path(os.__file__).parent.parent / 'esmf.mk')
import sys
sys.path.append(f'../icecap')
from jupyter_interface import Icecap

""" Wipe all previous ICECAP calulations"""
_ = Icecap('ice_distance_topaz5.conf', wipe=3)
```

<div class="alert alert-block alert-info"> <b>Quick start guide </b> 
<ol>
<li>Execute the jupyter notebook cell</li>
<li>Adjust settings using the dropdown menu</li>
<li>press <i>Run ICECAP</i> </li> 
<li>After the calculation is finished execute the next cell to plot the result </li> 
</ol>

</div>

<div class="alert alert-block alert-success"> <b>1st Example: TOPAZ5 medium-range forecast </b><br>

<br>
The user can select: 
<ol>
<li>the forecast model from the dropdown menu</li>
<li>the forecast start date</li>
<li>the location from which to derive the distance to the ice edge (format: longitude, latitude) </li>
</ol>

OSI-408 is used as reference
</div>

```python
"""Executing this cell will show the dropdown menu"""
topaz = Icecap('ice_distance_topaz5.conf')
```

```python
"""Execute this cell to plot result"""
topaz.plot(figsize=(10,10))
```

```python

```
