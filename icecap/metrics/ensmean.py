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
        self.use_dask = True
        if self.area_statistic_kind is None or self.area_statistic_function == 'mean':
            self.clip = True

    def compute(self):
        """ Compute metric """
        average_dims = None
        persistence = False
        sice_threshold = None

        # averaging over data or score the same for ensmean. data is faster
        if self.area_statistic_kind is not None:
            self.area_statistic_kind = 'data'

        processed_data_dict = self.process_data_for_metric(average_dims, persistence, sice_threshold)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])
        if self.calib:
            da_fc_verif_plot = processed_data_dict['da_fc_verif_bc'].mean(dim=('date','member','inidate'))
        else:
            da_fc_verif_plot = processed_data_dict['da_fc_verif'].mean(dim=('date','member','inidate'))


        data_plot.append(da_fc_verif_plot.rename(f'{self.title_fcname}'))

        if persistence:
            da_persistence = processed_data_dict['da_verdata_persistence']
            data_plot.append(da_persistence.rename('persistence'))


        if self.add_verdata == "yes":
            da_verdata_verif = processed_data_dict['da_verdata_verif'].mean(dim=('date','member','inidate'))
            data_plot.append(da_verdata_verif.rename(f'{self.verif_name}'))


        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                                 params=['projection', 'central_longitude', 'central_latitude',
                                                         'true_scale_latitude'])


        data_xr = xr.merge(data_plot)
        data_xr = data_xr.assign_attrs({f'{self.verif_name}-linecolor': 'k'})
        data_xr = data_xr.assign_attrs({f'{self.title_fcname}-linecolor': 'blue'})

        self.result = data_xr
