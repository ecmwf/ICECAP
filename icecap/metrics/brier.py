""" Metric calculating briar (skill) score """
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
        self.plottext = ''
        self.legendtext = ''
        self.ylabel = 'BSS'
        self.levels = np.arange(-1.05, 1.1, .1)
        self.default_cmap = 'bwr'
        self.use_dask = False
        self.use_dask = True
        # if self.area_statistic_kind is None or self.area_statistic_function == 'mean':
        #     self.clip = True

    def compute(self):
        """ Compute metric """

        if self.calib:
            raise NotImplementedError('Calibration not supported yet for this metric')

        # everything beyond 15% is assumed ice
        sice_threshold = 0.15

        da_fc_verif = self.load_fc_data('verif')
        da_fc_verif_ice = (xr.where(da_fc_verif > sice_threshold, 1, 0)).mean(dim='member')
        da_fc_verif_mask = da_fc_verif.isel(member=0, time=[0], inidate=0, date=0)
        del da_fc_verif
        da_verdata_verif = self.load_verif_data('verif')
        da_verdata_verif_ice = xr.where(da_verdata_verif > sice_threshold, 1, 0)
        da_verdata_verif_mask = da_verdata_verif.isel(member=0, time=[0], inidate=0, date=0)
        del da_verdata_verif
        da_persistence = self.load_verif_data('verif', target='i:0').isel(member=0, time=0)
        da_persistence_ice = xr.where(da_persistence > sice_threshold, 1, 0)
        da_persistence_mask = da_persistence.isel(inidate=0, date=0)
        del da_persistence



        _, lsm_full = self.mask_lsm([da_fc_verif_mask, da_verdata_verif_mask, da_persistence_mask])
        datalist = [da_fc_verif_ice, da_verdata_verif_ice, da_persistence_ice]

        data = [d.where(~np.isnan(lsm_full)) for d in datalist]
        if self.area_statistic_kind == 'data':
            data, lsm = self.calc_area_statistics(data, lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)

        da_fc_verif_ice = data[0]
        da_verdata_verif_ice = data[1].isel(member=0)
        da_persistence_ice = data[2]


        # brier score
        da_fc_verif_bs = ((da_fc_verif_ice-da_verdata_verif_ice)**2).mean(dim=('date','inidate'))
        da_persistence_bs = ((da_persistence_ice-da_verdata_verif_ice)**2).mean(dim=('date','inidate'))
        # set zeros to very small values to allow division
        da_persistence_bs = xr.where(da_persistence_bs==0,1e-11,da_persistence_bs)
        da_fc_verif_bs = xr.where(da_fc_verif_bs==0,1e-11,da_fc_verif_bs)
        da_fc_verif_bss = 1-da_fc_verif_bs/da_persistence_bs
        # clip bss to -1 to 1
        da_fc_verif_bss = da_fc_verif_bss.clip(-1,1)
        # restore zero values before saving
        da_persistence_bs = xr.where(da_persistence_bs == 1e-11, 0, da_persistence_bs)
        da_fc_verif_bs = xr.where(da_fc_verif_bs == 1e-11, 0, da_fc_verif_bs)


        if self.area_statistic_kind == 'score':
            data = [da_fc_verif_bs,
                    da_persistence_bs,
                    da_fc_verif_bss]

            data, lsm = self.calc_area_statistics(data, lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
            da_fc_verif_bs = data[0]
            da_persistence_bs = data[1]
            da_fc_verif_bss = data[2]


        # copy projection information if needed
        for proj_param in ['projection', 'central_longitude', 'central_latitude',
                           'true_scale_latitude']:
            if proj_param in da_verdata_verif_mask.attrs:
                da_fc_verif_bs.attrs[proj_param] = getattr(da_verdata_verif_mask, proj_param)
                da_persistence_bs.attrs[proj_param] = getattr(da_verdata_verif_mask, proj_param)
                da_fc_verif_bss.attrs[proj_param] = getattr(da_verdata_verif_mask, proj_param)



        data = [
            da_fc_verif_bs.rename('noplot_fc_bs'),
            da_persistence_bs.rename('noplot_pers_bs'),
            da_fc_verif_bss.rename('fc_bss')
        ]

        if self.area_statistic_kind is not None:
            data.append(lsm)

        data.append(lsm_full)

        data_xr = xr.merge(data)
        self.result = data_xr
