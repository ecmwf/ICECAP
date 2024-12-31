""" Metric calculating calibration file only (no plotting)"""
import os
import xarray as xr
from .metric import BaseMetric


xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True

    def compute(self):
        """ Compute metric """
        average_dims = ['member','inidate']
        persistence = False
        sice_threshold = None

        _ = self.process_data_for_metric(average_dims, persistence, sice_threshold)

        self.result = None