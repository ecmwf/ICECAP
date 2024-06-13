""" Metric calculating Integrated Ice Edge Error (IIEE) """
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
        self.ylabel = 'IIEE'
        self.levels = None
        self.use_dask = False

    def compute(self):
        """ Compute metric """

        # IEE is always spatially aggregated over score
        self.area_statistic_kind = 'score'
        self.area_statistic_function = 'sum'

        average_dims = ['member']
        persistence = False
        sice_threshold = 0.15

        processed_data_dict = self.process_data_for_metric(average_dims, persistence,
                                                           sice_threshold)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if self.calib:
            da_fc_verif= processed_data_dict['da_fc_verif_bc']
        else:
            da_fc_verif = processed_data_dict['da_fc_verif']

        da_verdata_verif = processed_data_dict['da_verdata_verif']
        da_mae = (np.abs(da_verdata_verif - da_fc_verif)).mean(dim=('inidate', 'date'))

        data, lsm = self.calc_area_statistics([da_mae], processed_data_dict['lsm_full'],
                                              statistic=self.area_statistic_function)
        data_plot.append(data[0].rename('fc_iiee'))
        data_plot.append(lsm)



        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)


        self.result = data_xr
