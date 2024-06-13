""" Metric calculating ensemble mean """
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
        self.ylabel = 'sic'
        self.levels = np.arange(0, 1.1, .1)
        self.use_dask = False
        if self.area_statistic_kind is None or self.area_statistic_function == 'mean':
            self.clip = True

    def compute(self):
        """ Compute metric """

        # averaging over data or score the same for ensmean. data is faster
        if self.area_statistic_kind is not None:
            self.area_statistic_kind = 'data'

        average_dims = ['member', 'inidate']

        processed_data_dict = self.process_data_for_metric(average_dims)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])
        if self.calib:
            da_fc_verif_plot = processed_data_dict['da_fc_verif_bc']
        else:
            da_fc_verif_plot = processed_data_dict['da_fc_verif']

        # average over dates if present
        if 'date' in da_fc_verif_plot.dims:
            da_fc_verif_plot = da_fc_verif_plot.mean(dim='date')


        data_plot.append(da_fc_verif_plot.rename(f'{self.verif_expname[0]}'))

        if self.add_verdata == "yes":
            da_verdata_verif = processed_data_dict['da_verdata_verif']
            # average over dates if present
            if 'date' in da_verdata_verif.dims:
                da_verdata_verif = da_verdata_verif.mean(dim='date')
            data_plot.append(da_verdata_verif.rename('obs'))


        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                                 params=['projection', 'central_longitude', 'central_latitude',
                                                         'true_scale_latitude'])

        data_xr = xr.merge(data_plot)


        self.result = data_xr
