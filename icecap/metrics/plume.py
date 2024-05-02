""" Metric calculating forecast plumes """
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
        self.ylabel = 'sic'
        self.levels = np.arange(0, 1.1, .1)
        self.use_dask = True


        if self.area_statistic is None:
            raise ValueError('area_statistic needs to be set (with region_extent if desired)'
                             'to plot plumes')
        if len(self.verif_dates) !=1:
            raise ValueError('only one verification date (verif_dates) can be specified'
                             'to plot plumes')



    def compute(self):
        """ Compute metric """
        da_fc_verif = self.load_fc_data('verif')
        da_fc_verif = da_fc_verif.isel(inidate=0, date=0)
        data = [da_fc_verif.rename(f'{self.verif_expname[0]}')]


        # we need to load reference data to calculate lsm
        da_verdata_verif = self.load_verif_data('verif')
        da_verdata_verif = da_verdata_verif.isel(inidate=0, date=0, member=0)
        data.append(da_verdata_verif.rename('obs'))

        if self.calib:
            da_fc_calib = self.load_fc_data('calib', average_dim=['member','date','inidate'])
            da_verdata_calib = self.load_verif_data('calib',average_dim=['member','date','inidate'])
            bias_calib = da_fc_calib - da_verdata_calib
            fc_verif_bc = da_fc_verif - bias_calib
            #fc_verif_bc = da_fc_verif - da_fc_calib
            data[0] = fc_verif_bc.rename(f'{self.verif_expname[0]}')



        data, lsm_full = self.mask_lsm(data)

        if self.area_statistic_kind is not None:
            data, lsm = self.calc_area_statistics(data,lsm_full,
                                             minimum_value=self.area_statistic_minvalue,
                                             statistic=self.area_statistic_function)

            # add lsm to metric netcdf file
            data.append(lsm)

            # if reference data is not desired remove it here from the dataset list
            if self.add_verdata == "no":
                data.pop(1)


        data.append(lsm_full)
        data_xr = xr.merge(data)
        data_xr = data_xr.assign_attrs({'obs-linecolor': 'k'})
        data_xr = data_xr.assign_attrs({f'{self.verif_expname[0]}-linecolor': 'blue'})

        self.result = data_xr
