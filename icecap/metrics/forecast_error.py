""" Metric calculating mean error """
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
        self.plottext = f'bias to {self.verif_name}'
        self.legendtext = 'bias'
        self.default_cmap = 'bwr'
        self.levels = np.arange(-1.05, 1.15, .1)
        self.levels = [-.25, -.2, -.15, -.1, -.05, .05, .1, .15, .2, .25]
        self.default_cmap = 'RdBu_r'
        self.ylabel = 'sic'
        self.use_dask = True

    def compute(self):
        """ Compute metric """

        # averaging over data or score the same for forecast_error. data is faster
        if self.area_statistic_kind is not None:
            self.area_statistic_kind = 'data'

        if self.temporal_average_type is not None:
            self.temporal_average_type = 'data'

        average_dims = ['member','inidate']
        persistence = True

        processed_data_dict = self.process_data_for_metric(average_dims, persistence)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])
        if self.calib:
            da_fc_verif_plot = processed_data_dict['da_fc_verif_bc'].mean(dim='date')
        else:
            da_fc_verif_plot = processed_data_dict['da_fc_verif'].mean(dim='date')

        da_verdata_verif = processed_data_dict['da_verdata_verif'].mean(dim='date')
        bias = (da_fc_verif_plot - da_verdata_verif).rename(f'{self.verif_expname[0]}')

        if persistence:
            da_persistence = processed_data_dict['da_verdata_persistence'].mean(dim=('date','inidate'))
            bias_persistence = (da_persistence - da_verdata_verif).rename(f'{self.verif_expname[0]}')

        data_plot += [
            bias.rename('fc_bias'),
            bias_persistence.rename('persistence')
        ]

        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)


        self.result = data_xr
