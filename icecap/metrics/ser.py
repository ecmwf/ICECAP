""" Metric calculating spread error ratio (reliability) """
import os
import numpy as np
import xarray as xr
import matplotlib.colors as mcolors
import utils
from .metric import BaseMetric


xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

# computation is very slow as there are many grid cells/timesteps
        # to make teh computation faster we do the following
        # 1. stack array along xc and yc
        # 2. drop all cells for which standard deviation is 0

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.plottext = ''
        self.legendtext = ''
        self.ylabel = 'SER'
        self.levels = np.arange(0., 2.1, .1)
        self.default_cmap = 'bwr'

        colors = ('0d06ff', '0d06ff', '0875e5', '87a3ff', '7dbdff', 'addeff', 'b3feff', 'ffffff',
                  'ffff02', 'ffd900', 'ffb000', 'ff7f01', 'ff0000', '7f002b', '7f002b')
        colors_rsr = [f'#{c}' for c in colors]
        self.levels = [0.3, 0.5, .6, .7, .8, .9, .95, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7]
        self.default_cmap, self.norm = mcolors.from_levels_and_colors(self.levels, colors_rsr, extend='both')

        self.use_dask = False
        self.use_dask = True

    def compute(self):
        """ Compute metric """

        if self.calib:
            raise NotImplementedError('Calibration not supported yet for this metric')

        da_fc_verif = self.load_fc_data('verif')
        da_verdata_verif = self.load_verif_data('verif')
        data, lsm_full = self.mask_lsm([da_fc_verif, da_verdata_verif])

        if self.area_statistic_kind == 'data':
            data, lsm = self.calc_area_statistics(data, lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
        da_fc_verif = data[0]
        da_verdata_verif = data[1].isel(member=0)

        da_rmse = np.sqrt(((da_fc_verif.mean(dim='member') - da_verdata_verif)**2).mean(dim=('inidate','date')))
        da_spread = np.sqrt(da_fc_verif.var(dim='member').mean(dim=('inidate','date')))

        # set zero values to 1e-11 to avoid division by 0
        da_rmse = xr.where(da_rmse == 0, 1e-11, da_rmse)
        da_spread = xr.where(da_spread == 0, 1e-11, da_spread)
        da_ser = da_spread/da_rmse

        # restore zero values before saving
        da_rmse = xr.where(da_rmse == 1e-11, 0, da_rmse)
        da_spread = xr.where(da_spread == 1e-11, 0, da_spread)

        if self.area_statistic_kind == 'score':
            data, lsm = self.calc_area_statistics([da_rmse, da_spread, da_ser], lsm_full,
                                                  minimum_value=self.area_statistic_minvalue,
                                                  statistic=self.area_statistic_function)
            da_rmse = data[0]
            da_spread = data[1]
            da_ser = data[2]

        # set projection attributes
        data = utils.set_xarray_attribute([da_rmse, da_spread, da_ser], da_verdata_verif,
                                          params=['projection', 'central_longitude', 'central_latitude',
                                                  'true_scale_latitude'])


        data = [
            data[0].rename('fc_rmse'),
            data[1].rename('fc_spread'),
            data[2].rename('fc_ser'),
        ]

        if self.area_statistic_kind is not None:
            data.append(lsm)

        data.append(lsm_full)

        data_xr = xr.merge(data)

        # set xarray DataArray attributes to set variable specific labels, colors,...
        for var in ['fc_rmse','fc_spread']:
            data_xr = data_xr.assign_attrs({f'{var}-cmap': 'hot_r',
                                            f'{var}-levels': f'{np.arange(0.05,1.05,.1)}',
                                            f'{var}-norm': 'None'})

        for var in ['fc_ser','fc_rmse', 'fc_spread']:
            data_xr = data_xr.assign_attrs({f'{var}-linecolor': 'k'})
            cmd_all = [{"attr_type" : 'cb.set_label', "label" : var.replace('fc_','').upper()}]
            for i, cmd in enumerate(cmd_all):
                cmd_list = [f"{key}=\"{value}\"" if isinstance(value, str) else f"{key}={value}" for key, value in
                            cmd.items()]
                data_xr = data_xr.assign_attrs({f'{var}-{i}': cmd_list})

        data_xr = data_xr.assign_attrs({'fc_ser-linestyle': 'solid',
                              'fc_rmse-linestyle': 'dashed',
                              'fc_spread-linestyle': 'dotted'})
        var_list = list(data_xr.data_vars)
        var_list_ser = [var for var in var_list if var not in ['fc_rmse','fc_spread']]
        var_list_rest = [var for var in var_list if var not in ['fc_ser']]

        self.result = [data_xr[var_list_rest], data_xr[var_list_ser]]
