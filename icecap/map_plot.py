""" Create 2-D filled contour plots """

import os
import numpy as np
from matplotlib import pyplot as plt
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.util import add_cyclic_point
import xarray as xr
import matplotlib.path as mpath

import utils


class MapPlot:
    """ Plotting object for 2D maps """
    def __init__(self, conf, metric):
        self.data = None
        self.plotdir = conf.plotdir
        self.metric = metric
        self.format = 'png'
        self.mapview = {}
        self.mapview['proj'] = 'LambertAzimuthalEqualArea'
        self.load(metric)



    def load(self, metric):
        """ load metric file """
        fname = metric.get_filename_metric()
        ds_file = xr.open_dataset(fname)
        self.xr_file = ds_file


    def plot(self):
        """ plot all steps in file """
        _ds_file = self.xr_file
        var_list = [i for i in _ds_file.data_vars]
        for _var in var_list:
            _steps = utils.convert_to_list(_ds_file[_var]['time'].values)

            for _step in _steps:
                _data = _ds_file[_var].sel(time=_step)


                thisfig = plt.figure(figsize=(11.69, 8.27))  # A4 figure size
                # set up map axes
                proj = getattr(ccrs, self.mapview['proj'])(central_latitude=90)

                ax = plt.axes(projection=proj)
                ax.set_extent([-180,180,50,90], ccrs.PlateCarree())



                ps_circle_border = True
                polar_projs = ['LambertAzimuthalEqualArea']
                if ps_circle_border and self.mapview['proj'] in polar_projs:

                    theta = np.linspace(0, 2 * np.pi, 100)
                    center, radius = [0.5, 0.5], 0.5
                    verts = np.vstack([np.sin(theta), np.cos(theta)]).T
                    circle = mpath.Path(verts * radius + center)
                    ax.set_boundary(circle, transform=ax.transAxes)


                if 'yc' in _data.dims:
                    trans_grid = proj
                    x_dim = _data['xc']*1000
                    y_dim = _data['yc']*1000

                elif 'latitude' in _data.dims:
                    trans_grid = ccrs.PlateCarree()
                    x_dim = _data['longitude']
                    y_dim = _data['latitude']
                    _data, x_dim = add_cyclic_point(_data.values, coord=x_dim.values)

                levels = np.arange(0,1.1,.1)
                cmap = 'cubehelix'
                plot = ax.contourf(x_dim, y_dim, _data, levels, transform=trans_grid,
                                   cmap=cmap)



                gl = ax.gridlines(draw_labels=True,
                                  ylocs=range(-80,91,10))
                gl.top_labels = False
                gl.right_labels = False
                gl.xformatter = LONGITUDE_FORMATTER
                gl.yformatter = LATITUDE_FORMATTER

                # add coast lines
                ax.coastlines(color='grey')
                cb = plt.colorbar(plot)
                cb.set_ticks(levels)

                ofile = self.get_filename_plot(varname=_var, time=_step,
                                       plotformat=self.format)
                print(ofile)
                thisfig.savefig(ofile)


    def get_filename_plot(self, **kwargs):
        """
        Create plotting directory and define output filename
        :param kwargs: Necessary keywords
        varname : variable name
        time: timestep
        plotformat: png/pdf/...
        :return: output filename as string
        """
        _ofile = f'{self.plotdir}/{self.metric.metricname}/' \
                   f'{kwargs["varname"]}_{kwargs["time"]}.' \
                   f'{kwargs["plotformat"]}'
        utils.make_dir(os.path.dirname(_ofile))
        return _ofile
