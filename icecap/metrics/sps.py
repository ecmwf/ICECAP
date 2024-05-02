""" Metric calculating Spatial Probability Score (SPS) """

import os
import xarray as xr
from .metric import BaseMetric

xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.plottext = ''
        self.legendtext = ''
        self.ylabel = 'SPS'
        self.levels = None
        self.use_dask = False
        #self.use_dask = True

    def compute(self):
        """ Compute metric """

        if self.calib:
            raise NotImplementedError('Calibration not supported yet for this metric')
        self.area_statistic_function = 'sum'

        da_fc_verif = self.load_fc_data('verif')
        da_verdata_verif = self.load_verif_data('verif')
        data, lsm_full = self.mask_lsm([da_fc_verif, da_verdata_verif])

        da_fc_verif = (xr.where(data[0] > 0.15, 1, 0)).mean(dim='member')
        da_verdata_verif = xr.where(data[1].isel(member=0) > 0.15, 1, 0)


        da_mse = ((da_verdata_verif-da_fc_verif)**2).mean(dim=('inidate','date'))
        data, lsm = self.calc_area_statistics([da_mse], lsm_full,
                                              minimum_value=None,
                                              statistic='sum')
        data[0] = data[0]
        data = [data[0].rename('fc_sps')]

        data.append(lsm)
        data.append(lsm_full)

        data_xr = xr.merge(data)
        self.result = data_xr
