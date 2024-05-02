""" Metric calculating mean error """
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
        self.levels = [-.25,-.2,-.15,-.1,-.05,.05,.1,.15,.2,.25]
        self.default_cmap = 'RdBu_r'
        self.ylabel = 'sic'


    def compute(self):
        """ Compute metric """
        da_verdata_verif = self.load_verif_data('verif', average_dim=['date','member','inidate'])
        da_fc_verif = self.load_fc_data('verif',average_dim=['date','member','inidate'])

        if self.calib:
            da_fc_calib = self.load_fc_data('calib', average_dim=['member','date','inidate'])
            da_verdata_calib = self.load_verif_data('calib',average_dim=['member','date','inidate'])
            bias_calib = da_fc_calib - da_verdata_calib
            fc_verif_bc = da_fc_verif - bias_calib
            da_fc_verif = fc_verif_bc.rename(f'{self.verif_expname[0]}')

        data, lsm_full = self.mask_lsm([da_verdata_verif, da_fc_verif])
        bias = (data[1] - data[0]).rename(f'{self.verif_expname[0]}-bias')
        data = [bias]

        if self.area_statistic_kind is not None:
            data, lsm = self.calc_area_statistics(data, lsm_full,
                                             minimum_value=self.area_statistic_minvalue,
                                             statistic=self.area_statistic_function)

            # add lsm to metric netcdf file
            data.append(lsm)
        data.append(lsm_full)
        self.result = xr.merge(data)
