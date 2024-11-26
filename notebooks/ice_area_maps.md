<!-- #region -->
# ICECAP Notebook to derive maps of sea ice concentrations


#### This notebook produces spatial maps of predicted sea ice concentrations from TOPAZ5 medium-range and ECMWF and DWD seasonal forecasts
<!-- #endregion -->

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
_ = Icecap('ice_area_maps_topaz5.conf', wipe=3)

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
<li>the forecast start date</li>
</ol>

For medium-range (up to 15 days) only TOPAZ5 is available currently. OSI-CDR is used as reference
</div>

```python
"""Executing this cell will show the dropdown menu"""
topaz = Icecap('ice_area_maps_topaz5.conf')
```

```python
"""Execute this cell to plot result"""
topaz.plot(maxcols=3, figsize=(16, 8))
```

<div class="alert alert-block alert-success"> <b>2nd Example: Seasonal forecasts retrieved from the Climate Data Store (CDS) </b><br>

<br>
The user can select: 
<ol>
<li>the forecast model from the dropdown menu</li>
<li>the forecast start date</li>
</ol>


```python
cds = Icecap('ice_area_maps_cds.conf')
```

```python
cds.plot()
```

```python

```
