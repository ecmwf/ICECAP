""" Metric calculating trends """
import os
import numpy as np
import xarray as xr
import utils
import metrics.metric_utils as mutils
from .metric import BaseMetric


xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.plottext = ''
        self.legendtext = 'linear trend in % per decade'
        self.ylabel = 'sic'
        self.default_cmap = 'seismic_r'
        self.levels = np.arange(-31.5, 33, 3)
        self.use_dask = False

    def compute(self):
        """ Compute metric """


        average_dims = ['member','inidate']
        persistence = False

        processed_data_dict = self.process_data_for_metric(average_dims, persistence)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])
        if 'lsm' in processed_data_dict:
            data_plot.append(processed_data_dict['lsm'])

        if self.calib:
            da_fc_verif= processed_data_dict['da_fc_verif_bc']
        else:
            da_fc_verif = processed_data_dict['da_fc_verif']

        da_verdata_verif = processed_data_dict['da_verdata_verif']

        data = [da_verdata_verif, da_fc_verif]
        for di in range(len(data)):
            if 'xc' not in data[di].dims:
                data[di] = data[di].expand_dims(['xc', 'yc'])

        if self.add_verdata == "yes":
            da_slope_verdata, da_intercept_verdata, da_pvalue_verdata = mutils.compute_linreg(data[0])
            data_plot.append(da_slope_verdata.rename('verdata-verif-value').squeeze()*1000)
            data_plot.append(da_pvalue_verdata.rename('verdata-verif-pvalue').squeeze())

        da_slope_fc, da_intercept_fc, da_pvalue_fc = mutils.compute_linreg(data[1])
        data_plot.append(da_slope_fc.rename('fc-verif-value').squeeze()*1000)
        data_plot.append(da_pvalue_fc.rename('fc-verif-pvalue').squeeze())



        # set projection attributes
        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])



        data_xr = xr.merge(data_plot)


        self.result = data_xr
