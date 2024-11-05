""" Metric calculating Spatial Probability Score (SPS) """
import os
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
        self.ylabel = 'SPS'
        self.levels = None
        self.use_dask = False
        self.use_dask = True

    def compute(self):
        """ Compute metric """


        self.area_statistic_kind = 'score'
        self.area_statistic_function = 'sum'

        average_dims = None
        persistence = True
        sice_threshold = 0.15

        processed_data_dict = self.process_data_for_metric(average_dims, persistence,
                                                           sice_threshold)


        if self.calib:
            da_fc_verif= processed_data_dict['da_fc_verif_bc'].mean(dim='member')
        else:
            da_fc_verif = processed_data_dict['da_fc_verif'].mean(dim='member')

        da_persistence = processed_data_dict['da_verdata_persistence']
        da_verdata_verif = processed_data_dict['da_verdata_verif'].isel(member=0)


        da_mse = ((da_verdata_verif - da_fc_verif) ** 2).mean(dim=('inidate', 'date'))
        da_mse_pers = ((da_verdata_verif - da_persistence) ** 2).mean(dim=('inidate', 'date'))
        data, lsm = self.calc_area_statistics([da_mse, da_mse_pers], processed_data_dict['lsm_full'],
                                              statistic='sum')


        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        data_plot.append(lsm)
        data_plot.append(data[0].rename('fc_sps'))
        data_plot.append(data[1].rename('persistence_sps'))

        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)


        self.result = data_xr
