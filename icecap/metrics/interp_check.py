""" Metric to check if interpolation was succesful """

import xarray as xr
from .metric import BaseMetric

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True


    def compute(self):
        """ Compute metric """

        fc_regrid = self.load_forecasts()
        fc_native = self.load_forecasts(grid='native')

        fc_regrid_select = fc_regrid.isel(date=0, member=0, time=[-1]).rename('regrid')
        fc_native_select = fc_native.isel(date=0, member=0, time=[-1]).rename('native')
        self.result = xr.merge([fc_regrid_select,fc_native_select])
