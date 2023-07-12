""" Metric calculating bias corrected forecast maps """
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
        self.plottext = f'wrt {self.verif_name}'
        self.legendtext = 'bias-corrected'
        self.levels = np.arange(0, 1.1, .1)
        self.clip = True


    def compute(self):
        """ Compute metric """

        da_verdata_calib = self.load_verif_data('calib').mean(dim=('member', 'date'))

        da_fc_verif = self.load_verif_fc('verif').mean(dim=('member','date'))
        da_fc_calib = self.load_verif_fc('calib').mean(dim=('member','date'))

        bias_calib = da_fc_calib - da_verdata_calib
        fc_verif_bc = da_fc_verif - bias_calib
        fc_verif_bc_mean = fc_verif_bc.mean(dim='inidate')

        self.result = xr.merge([fc_verif_bc_mean.rename('sic')])
