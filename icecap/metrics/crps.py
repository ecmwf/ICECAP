""" Metric calculating CRPS (skill) score """
import os
import numpy as np
import xarray as xr
import xskillscore as xs
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
        self.legendtext = 'CRPSS'
        self.ylabel = 'CRPSS'
        self.levels = np.arange(-1.05, 1.1, .1)
        self.default_cmap = 'bwr'
        self.use_dask = True

    def compute(self):
        """ Compute metric """

        average_dims = None
        persistence = True

        processed_data_dict = self.process_data_for_metric(average_dims, persistence)

        if self.calib:
            da_fc_verif = processed_data_dict['da_fc_verif_bc']
        else:
            da_fc_verif = processed_data_dict['da_fc_verif']

        da_verdata_verif = processed_data_dict['da_verdata_verif'].isel(member=0)
        da_persistence = processed_data_dict['da_verdata_persistence']

        da_fc_verif_crps = xs.crps_ensemble(da_verdata_verif, da_fc_verif.chunk({"member": -1}),
                                            dim=['inidate', 'date'])
        da_persistence_crps = xs.crps_ensemble(da_verdata_verif, da_persistence.expand_dims('member'),
                                               dim=['inidate', 'date'])

        #  set zeros to very small values to allow division
        da_persistence_crps = xr.where(da_persistence_crps == 0, 1e-11, da_persistence_crps)
        da_fc_verif_crps = xr.where(da_fc_verif_crps == 0, 1e-11, da_fc_verif_crps)
        da_fc_crpss = 1 - da_fc_verif_crps / da_persistence_crps
        # clip crpss to -1 to 1
        da_fc_crpss = da_fc_crpss.clip(-1, 1)
        # restore zero values before saving
        da_persistence_crps = xr.where(da_persistence_crps == 1e-11, 0, da_persistence_crps)
        da_fc_verif_crps = xr.where(da_fc_verif_crps == 1e-11, 0, da_fc_verif_crps)

        if self.area_statistic_kind == 'score':
            data = [da_fc_verif_crps,
                    da_persistence_crps,
                    da_fc_crpss]

            data, lsm = self.calc_area_statistics(data, processed_data_dict['lsm_full'],
                                                  statistic=self.area_statistic_function)
            da_fc_verif_crps = data[0]
            da_persistence_crps = data[1]
            da_fc_crpss = data[2]
            processed_data_dict['lsm'] = lsm

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])


        data_plot += [
            da_fc_verif_crps.rename('noplot_fc_crps'),
            da_persistence_crps.rename('noplot_pers_crps'),
            da_fc_crpss.rename('fc_crpss'),
        ]

        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                                 params=['projection', 'central_longitude', 'central_latitude',
                                                         'true_scale_latitude'])

        data_xr = xr.merge(data_plot)


        self.result = data_xr
