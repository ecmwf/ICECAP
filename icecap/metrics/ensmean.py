""" Metric calculating ensemble mean """
import os
import numpy as np
import xarray as xr
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
        self.levels = np.arange(0, 1.1, .1)


    def compute(self):
        """ Compute metric """

        da_fc_verif = self.load_verif_fc('verif')
        da_fc_verif = da_fc_verif.mean(dim=('date','inidate'))
        data = [da_fc_verif.rename('model')]

        if self.add_verdata == "yes" or self.area_mean is not None:
            da_verdata_verif = self.load_verif_data('verif')
            da_verdata_verif = da_verdata_verif.mean(dim=('member', 'date','inidate'))
            data.append(da_verdata_verif.rename('obs'))


        if self.area_mean is not None:
            data = self.calc_area_statistics(data, minimum_value=0.15, statistic='sum')
            if self.add_verdata == "no":
                data = data[0]



        data_xr = xr.merge(data)
        if 'member' not in data_xr.dims:
            data_xr = data_xr.expand_dims(dim={"member": 1})

        self.result = data_xr
