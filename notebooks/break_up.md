<!-- #region -->
# ICECAP Notebook to derive seasonal outlooks of early/late sea ice break up probabiliites


#### This notebook produces spatial maps of predicted sea ice break up probabiliites from ECMWF and DWD seasonal forecasts
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
_ = Icecap('break_up_cds.conf', wipe=3)

```

<div class="alert alert-block alert-success"> <b>1st Example: Seasonal forecasts retrieved from the Climate Data Store (CDS) </b><br>

<br>
The user can select: 
<ol>
<li>the forecast model from the dropdown menu</li>
<li>the forecast start date</li>
</ol>


```python
cds = Icecap('break_up_cds.conf')
```

```python
cds.plot()
```
