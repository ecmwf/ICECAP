""" Metric calculating RMSE """
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
        self.ylabel = 'RMSE'
        self.levels = np.arange(0.05, 1.05, .1)
        self.default_cmap = 'hot_r'
        self.use_dask = True


    def compute(self):
        """ Compute metric """

        average_dims = ['member']
        persistence = False

        processed_data_dict = self.process_data_for_metric(average_dims, persistence)


        if self.calib:
            da_fc_verif = processed_data_dict['da_fc_verif_bc']
        else:
            da_fc_verif = processed_data_dict['da_fc_verif']

        da_verdata_verif = processed_data_dict['da_verdata_verif']

        da_rmse = np.sqrt(((da_fc_verif - da_verdata_verif) ** 2).mean(dim=('inidate', 'date')))

        if self.area_statistic_kind == 'score':
            data, lsm = self.calc_area_statistics([da_rmse], processed_data_dict['lsm_full'],
                                                  statistic=self.area_statistic_function)
            da_rmse = data[0]
            processed_data_dict['lsm'] = lsm

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])

        data_plot += [
            da_rmse.rename('fc_rmse'),
        ]

        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)

        data_xr = data_xr.assign_attrs({'obs-linecolor': 'k'})
        data_xr = data_xr.assign_attrs({f'{self.verif_expname[0]}-linecolor': 'blue'})


        self.result = data_xr
