""" Generic plot class (used for timeseries and map-plots) """

import os
import ast
import xarray as xr
import matplotlib


import utils

def attrsList_to_dict(attrs_list):
    """
    Convert list used to store plotting options to dictionary
    :param attrs_list: list of plotting options
    :return: dict of those options
    """
    attrs_dict = dict()
    for v in attrs_list:
        attrs_dict[v.split('=')[0]] = v.split('=')[1]

    for k, v in attrs_dict.items():
        attrs_dict[k] = ast.literal_eval(v)

    return attrs_dict
class GenericPlot:
    """" Generic plot class """
    def __init__(self, conf, metric):
        self.load(metric)
        matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        self.verif_name = metric.verif_name
        self.metric = metric
        self.ofile = metric.ofile
        self.clip = metric.clip
        self.levels = metric.levels
        self.ticks = metric.ticks
        self.ticklabels = metric.ticklabels
        self.norm = metric.norm
        self.format = 'png'
        self.plotdir = conf.plotdir
        self.verif_source = metric.verif_source[0]
        self.verif_modelname = metric.verif_modelname[0]
        self.verif_fcsystem = metric.verif_fcsystem[0]
        self.verif_expname = metric.verif_expname[0]
        self.verif_enssize = metric.verif_enssize[0]
        self.verif_mode = metric.verif_mode[0]
        self.verif_fromyear = metric.verif_fromyear
        self.verif_toyear = metric.verif_toyear
        self.verif_name = metric.verif_name
        self.verif_dates = metric.verif_dates
        self.conf_verif_dates = metric.conf_verif_dates
        self.plottype = metric.plottype

        self.calib = metric.calib
        if self.calib:
            self.calib = True
            self.conf_calib_dates = metric.conf_calib_dates
            self.calib_fromyear = metric.calib_fromyear
            self.calib_toyear = metric.calib_toyear
            self.calib_enssize = metric.calib_enssize[0]

    def get_filename_plot(self, **kwargs):
        """
        Create plotting directory and define output filename
        :param kwargs: Necessary keywords
        varname : variable name
        time: timestep
        plotformat: png/pdf/...
        :return: output filename as string
        """
        if kwargs["time"] is not None:
            time_name = f'_{kwargs["time"]:03d}'
        else:
            time_name = ''
        _ofile = f'{self.plotdir}/{self.metric.metricname}/' \
                   f'{kwargs["varname"]}{time_name}.' \
                   f'{kwargs["plotformat"]}'
        utils.make_dir(os.path.dirname(_ofile))
        return _ofile

    def load(self, metric):
        """ load metric file
        :param metric: metric object
        """
        fname = metric.get_filename_metric()
        if os.path.isfile(fname):
            output = xr.open_dataset(fname)
        else:
            fdir = os.path.dirname(fname)+'/'
            files = [f for f in os.listdir(fdir) if os.path.isfile(fdir+f)]
            files = [f for f in files if '.nc' in f]
            files = sorted(files)
            output = []
            for f in files:
                output.append(xr.open_dataset(fdir+f))

        self.xr_file = output
