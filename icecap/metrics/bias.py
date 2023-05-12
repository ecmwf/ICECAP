""" Metric calculating bias """
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
        self.plottext = f'bias to {self.verif_name}'
        self.legendtext = 'bias'
        self.default_cmap = 'bwr'
        self.levels = np.arange(-1.05, 1.15, .1)
        self.levels = np.arange(-0.22, 0.26, .04)
        self.default_cmap = 'RdBu_r'


    def compute(self):
        """ Compute metric """
        fc_list = self.load_verif_fc()
        verif_list = self.load_verif_data()

        fc_list = [fc.mean(dim=('member','date')) for fc in fc_list]
        verif_list = [verif.mean(dim=('member', 'date')) for verif in verif_list]

        bias_list = [fc_list[i] - verif_list[i] for i in range(len(fc_list))]

        bias_ltmean = xr.concat(bias_list, dim='date').mean(dim='date')


        self.result = xr.merge([bias_ltmean])
