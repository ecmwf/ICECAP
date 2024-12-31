""" Metric calculating forecast plumes """
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

        if self.area_statistic is None:
            raise ValueError('area_statistic needs to be set (with region_extent if desired)'
                             ' to plot plumes')
        if len(self.verif_dates) !=1 or self.verif_fromyear != self.verif_toyear:
            raise ValueError('only one verification date (verif_dates) can be specified'
                             ' to plot plumes')

    def compute(self):
        """ Compute metric """

        average_dims = ['inidate']
        persistence = False
        sic_threshold = None

        processed_data_dict = self.process_data_for_metric(average_dims, persistence, sic_threshold)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        data_plot.append(processed_data_dict['lsm'])

        if self.calib:
            da_fc_verif= processed_data_dict['da_fc_verif_bc'].squeeze()
        else:
            da_fc_verif = processed_data_dict['da_fc_verif'].squeeze()

        data_plot.append(da_fc_verif.rename(f'{self.title_fcname}'))

        if self.add_verdata == "yes":
            da_verdata_verif = processed_data_dict['da_verdata_verif'].squeeze()
            data_plot.append(da_verdata_verif.rename(self.verif_name))


        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)

        data_xr = data_xr.assign_attrs({f'{self.verif_name}-linecolor': 'k'})
        data_xr = data_xr.assign_attrs({f'{self.title_fcname}-linecolor': 'blue'})


        self.result = data_xr
