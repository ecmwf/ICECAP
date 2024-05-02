""" Metric calculating CRPS (skill) score """

import os
import numpy as np
import xarray as xr
import xskillscore as xs
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
        self.ylabel = 'CRPSS'
        self.levels = np.arange(-1.05, 1.1, .1)
        self.default_cmap = 'bwr'
        self.use_dask = False

    def compute(self):
        """ Compute metric """

        if self.calib:
            raise NotImplementedError('Calibration not supported yet for this metric')



        da_fc_verif = self.load_fc_data('verif')
        da_verdata_verif = self.load_verif_data('verif')
        da_persistence = self.load_verif_data('verif', target='i:0').isel(member=0, time=0)
        data, lsm_full = self.mask_lsm([da_fc_verif, da_verdata_verif, da_persistence])

        if self.area_statistic_kind == 'data':
            data, lsm = self.calc_area_statistics(data, lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
        da_fc_verif = data[0]
        da_verdata_verif = data[1].isel(member=0)
        da_persistence = data[2]


        da_fc_verif_crps = xs.crps_ensemble(da_verdata_verif, da_fc_verif.chunk({"member": -1}), dim=['inidate','date'])
        da_persistence_crps = xs.crps_ensemble(da_verdata_verif, da_persistence.expand_dims('member'),
                                        dim=['inidate','date'])

        #  set zeros to very small values to allow division
        da_persistence_crps = xr.where(da_persistence_crps == 0, 1e-11, da_persistence_crps)
        da_fc_verif_crps = xr.where(da_fc_verif_crps == 0, 1e-11, da_fc_verif_crps)
        da_fc_crpss = 1-da_fc_verif_crps/da_persistence_crps
        # clip crpss to -1 to 1
        da_fc_crpss = da_fc_crpss.clip(-1, 1)
        # restore zero values before saving
        da_persistence_crps = xr.where(da_persistence_crps == 1e-11, 0, da_persistence_crps)
        da_fc_verif_crps = xr.where(da_fc_verif_crps == 1e-11, 0, da_fc_verif_crps)

        if self.area_statistic_kind == 'score':
            data = [da_fc_verif_crps,
                    da_persistence_crps,
                    da_fc_crpss]

            data, lsm = self.calc_area_statistics(data, lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
            da_fc_verif_crps = data[0]
            da_persistence_crps = data[1]
            da_fc_crpss = data[2]

        # copy projection information if needed
        for proj_param in ['projection', 'central_longitude', 'central_latitude',
                           'true_scale_latitude']:
            if proj_param in da_verdata_verif.attrs:
                da_persistence_crps.attrs[proj_param] = getattr(da_verdata_verif, proj_param)
                da_fc_verif_crps.attrs[proj_param] = getattr(da_verdata_verif, proj_param)
                da_fc_crpss.attrs[proj_param] = getattr(da_verdata_verif, proj_param)


        data = [
            da_fc_verif_crps.rename('noplot_fc_crps'),
            da_persistence_crps.rename('noplot_pers_crps'),
            da_fc_crpss.rename('fc_crpss'),
        ]


        if self.area_statistic_kind is not None:
            data.append(lsm)

        data.append(lsm_full)

        data_xr = xr.merge(data)
        self.result = data_xr
