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
        self.use_dask = True

    def compute(self):
        """ Compute metric """

        # IIEE is always spatially aggregated over score
        self.area_statistic_kind = 'score'
        self.area_statistic_function = 'sum'

        average_dims = None
        persistence = True
        sice_threshold = None # IIEE uses 15% threshold but averaging over members first

        processed_data_dict = self.process_data_for_metric(average_dims, persistence,
                                                           sice_threshold)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if self.calib:
            da_fc_verif= processed_data_dict['da_fc_verif_bc'].mean(dim='member')
        else:
            da_fc_verif = processed_data_dict['da_fc_verif'].mean(dim='member')


        da_verdata_verif = processed_data_dict['da_verdata_verif'].mean(dim='member')
        da_persistence = processed_data_dict['da_verdata_persistence']

        # set sic>0.15 to 1 else 0
        da_fc_verif = xr.where(da_fc_verif>0.15,1,0)
        da_verdata_verif = xr.where(da_verdata_verif>0.15,1,0)
        da_persistence = xr.where(da_persistence>0.15,1,0)

        ensmean_over_fc = xr.ones_like(da_verdata_verif).where(da_fc_verif - da_verdata_verif == 1, 0)
        ensmean_under_fc = xr.ones_like(da_verdata_verif).where(da_fc_verif - da_verdata_verif == -1, 0)

        ensmean_over_pers = xr.ones_like(da_verdata_verif).where(da_persistence - da_verdata_verif == 1, 0)
        ensmean_under_pers = xr.ones_like(da_verdata_verif).where(da_persistence - da_verdata_verif == -1, 0)



        data, lsm = self.calc_area_statistics([ensmean_over_fc, ensmean_under_fc,
                                               ensmean_over_pers, ensmean_under_pers],
                                              processed_data_dict['lsm_full'],
                                              statistic=self.area_statistic_function)
        ensmean_over_fc = data[0]
        ensmean_under_fc = data[1]
        ensmean_over_pers = data[2]
        ensmean_under_pers = data[3]


        iiee_fc = ensmean_over_fc + ensmean_under_fc
        aee_fc = np.fabs(ensmean_over_fc - ensmean_under_fc)
        me_fc = 2 * np.minimum(ensmean_over_fc, ensmean_under_fc)



        iiee_pers = ensmean_over_pers + ensmean_under_pers
        aee_pers = np.fabs(ensmean_over_pers - ensmean_under_pers)
        me_pers = 2 * np.minimum(ensmean_over_pers, ensmean_under_pers)

        data_plot.append(iiee_fc.rename(f'{self.title_fcname}').mean(dim=('inidate', 'date')))
        data_plot.append(aee_fc.rename('noplot_fc_aee').mean(dim=('inidate', 'date')))
        data_plot.append(me_fc.rename('noplot_fc_me').mean(dim=('inidate', 'date')))
        data_plot.append(iiee_pers.rename('persistence').mean(dim=('inidate', 'date')))
        data_plot.append(aee_pers.rename('noplot_persistence_aee').mean(dim=('inidate', 'date')))
        data_plot.append(me_pers.rename('noplot_persistence_me').mean(dim=('inidate', 'date')))
        data_plot.append(lsm)



        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)


        self.result = data_xr
