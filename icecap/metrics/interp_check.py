""" Metric to check if interpolation was succesful """

import numpy as np
import xarray as xr
from .metric import BaseMetric

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.plottext = 'sic'
        self.legendtext = ''
        self.levels = np.arange(0, 1.1, .1)


    def compute(self):
        """ Compute metric """

        fc_regrid = self.load_verif_fc()[0]
        fc_native = self.load_verif_fc(grid='native')[0]

        fc_regrid_select = fc_regrid.isel(date=0, member=0, time=[-1]).rename('regrid')
        fc_regrid_select = fc_regrid_select.rename({'xc':'xc_regrid', 'yc':'yc_regrid'})
        fc_native_select = fc_native.isel(date=0, member=0, time=[-1]).rename('native')
        fc_native_select = fc_native_select.rename({'xc': 'xc_native', 'yc': 'yc_native'})
        self.result = xr.merge([fc_regrid_select,fc_native_select])
