""" Metric calculating ensemble mean """
import os
import numpy as np
import xarray as xr
from .metric import BaseMetric

xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.plottext = 'sic'
        self.legendtext = ''
        self.levels = np.arange(0, 1.1, .1)


    def compute(self):
        """ Compute metric """
        fc_list = self.load_verif_fc()
        fc = xr.merge(fc_list)
        fc_ensmean = fc.mean(dim=('member','date'))

        self.result = xr.merge([fc_ensmean])
