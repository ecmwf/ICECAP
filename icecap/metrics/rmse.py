""" Metric calculating RMSE """
import os
import numpy as np
import xarray as xr
import utils
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
        self.ylabel = 'RMSE'
        self.levels = np.arange(0.05, 1.05, .1)
        self.default_cmap = 'hot_r'
        self.use_dask = False
        # self.use_dask = True

    def compute(self):
        """ Compute metric """

        if self.calib:
            raise NotImplementedError('Calibration not supported yet for this metric')

        da_fc_verif = self.load_fc_data('verif', average_dim=['member'])
        da_verdata_verif = self.load_verif_data('verif')
        data, lsm_full = self.mask_lsm([da_fc_verif, da_verdata_verif])

        if self.area_statistic_kind == 'data':
            data, lsm = self.calc_area_statistics(data, lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
        da_fc_verif = data[0]
        da_verdata_verif = data[1].isel(member=0)

        da_rmse = np.sqrt(((da_fc_verif - da_verdata_verif)**2).mean(dim=('inidate','date')))

        if self.area_statistic_kind == 'score':
            data, lsm = self.calc_area_statistics([da_rmse], lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
            da_rmse = data[0]

        # set projection attributes
        data = utils.set_xarray_attribute([da_rmse], da_verdata_verif,
                                          params=['projection', 'central_longitude', 'central_latitude',
                                                  'true_scale_latitude'])
        data = [
            data[0].rename('fc_rmse'),
        ]

        if self.area_statistic_kind is not None:
            data.append(lsm)

        data.append(lsm_full)

        data_xr = xr.merge(data)
        self.result = data_xr
