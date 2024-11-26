""" Metric calculating Brier Skill Score """
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
        self.legendtext = 'BSS'
        self.ylabel = 'BSS'
        self.levels = np.arange(-1, 1.1, .1)
        self.default_cmap = 'bwr'
        self.use_dask = True

    def compute(self):
        """ Compute metric """

        # everything beyond 15% is assumed ice
        sice_threshold = 0.15

        average_dims = None
        persistence = True

        processed_data_dict = self.process_data_for_metric(average_dims, persistence,
                                                           sice_threshold)

        if self.calib:
            da_fc_verif_ice = processed_data_dict['da_fc_verif_bc'].mean(dim='member')
        else:
            da_fc_verif_ice = processed_data_dict['da_fc_verif'].mean(dim='member')

        da_verdata_verif_ice = processed_data_dict['da_verdata_verif'].isel(member=0)
        da_persistence_ice = processed_data_dict['da_verdata_persistence']

        # brier score
        da_fc_verif_bs = ((da_fc_verif_ice - da_verdata_verif_ice) ** 2).mean(dim=('date', 'inidate'))
        da_persistence_bs = ((da_persistence_ice - da_verdata_verif_ice) ** 2).mean(dim=('date', 'inidate'))
        # set zeros to very small values to allow division
        da_persistence_bs = xr.where(da_persistence_bs == 0, 1e-11, da_persistence_bs)
        da_fc_verif_bs = xr.where(da_fc_verif_bs == 0, 1e-11, da_fc_verif_bs)
        da_fc_verif_bss = 1 - da_fc_verif_bs / da_persistence_bs
        # clip bss to -1 to 1
        da_fc_verif_bss = da_fc_verif_bss.clip(-1, 1)
        # restore zero values before saving
        da_persistence_bs = xr.where(da_persistence_bs == 1e-11, 0, da_persistence_bs)
        da_fc_verif_bs = xr.where(da_fc_verif_bs == 1e-11, 0, da_fc_verif_bs)

        if self.area_statistic_kind == 'score':
            data = [da_fc_verif_bs,
                    da_persistence_bs,
                    da_fc_verif_bss]

            data, lsm = self.calc_area_statistics(data, processed_data_dict['lsm_full'],
                                                  statistic=self.area_statistic_function)
            da_fc_verif_bs = data[0]
            da_persistence_bs = data[1]
            da_fc_verif_bss = data[2]
            processed_data_dict['lsm'] = lsm

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])


        data_plot += [
            da_fc_verif_bs.rename('noplot_fc_bs'),
            da_persistence_bs.rename('noplot_pers_bs'),
            da_fc_verif_bss.rename('fc_bss')
        ]

        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                                 params=['projection', 'central_longitude', 'central_latitude',
                                                         'true_scale_latitude'])

        data_xr = xr.merge(data_plot)
        data_xr = data_xr.assign_attrs({'fc_bss-map_plot': 'pcolormesh'})


        self.result = data_xr
