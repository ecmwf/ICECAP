""" Create 2-D filled contour plots """

import os
import datetime as dt
from matplotlib import pyplot as plt
import matplotlib
from mpl_toolkits.axes_grid1.inset_locator import InsetPosition
import numpy as np
import cartopy
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.util import add_cyclic_point
import xarray as xr
import cmocean


import utils

class GenericPlot:
    """" Generic plot class """
    def __init__(self, conf, metric):
        self.load(metric)
        self.verif_name = metric.verif_name
        self.metric = metric
        self.ofile = metric.ofile
        self.clip = metric.clip
        self.levels = None
        self.levels = metric.levels
        self.format = 'png'
        self.plotdir = conf.plotdir

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
        ds_file = xr.open_dataset(fname)
        self.xr_file = ds_file


class TsPlot(GenericPlot):
    """ Timeseries plot class """
    def __init__(self, conf, metric):
        super().__init__(conf, metric)
        self.points = metric.points

    def plot(self, metric, verbose=False):
        """ plot timeseries
        :param verbose: verbosity on or off
        """
        ofile = self.ofile
        if self.ofile is None:
            ofile = self.get_filename_plot(varname='model', time=None,
                                           plotformat=self.format)
        _ds_file = self.xr_file
        var_list = list(_ds_file.data_vars)

        thisfig = plt.figure(figsize=(8, 6))
        ax = plt.axes()
        for _var in var_list:
            _ds_file = self.xr_file[_var].dropna(dim='member').copy()
            if self.clip:
                _ds_file = _ds_file.clip(self.levels[0], self.levels[-1])
            if len(_ds_file['member']) > 1:
                perc = [5, 25, 33]  # ,1/3*100]
                shading = (np.linspace(0.2,1,len(perc)+1)**3)[1:]
                for pi, p in enumerate(perc):
                    ax.fill_between(_ds_file.time, _ds_file.quantile(p/100, dim='member'),
                                     _ds_file.quantile(1-p/100, dim='member'),
                                     color='teal', alpha=shading[pi],
                                    label=f'probability: {p}-{100 - p}%')
            for m in _ds_file['member'].values:
                if _var == 'obs':
                    ax.plot(_ds_file.time, _ds_file.sel(member=m).values,
                            color='k', alpha=1, linewidth=2, label=self.verif_name)
                elif _var == 'obs-hc':
                    ax.plot(_ds_file.time, _ds_file.sel(member=m).mean(dim='date').values,
                            color='red', alpha=1, linewidth=2,
                            zorder=200)
                else:
                    ax.plot(_ds_file.time, _ds_file.sel(member=m).values, alpha=.1, linewidth=1,
                             color='blue')

        if self.points is not None:
            ax2 = plt.axes([0, 0, 1, 1],
                           projection=ccrs.NorthPolarStereo())
            ip = InsetPosition(ax, [0.72, 0.67, 0.3, 0.3])
            ax2.set_axes_locator(ip)
            ax2.set_extent([-180, 180, 60, 90], ccrs.PlateCarree())

            theta = np.linspace(0, 2 * np.pi, 100)
            center, radius = [0.5, 0.5], 0.5
            verts = np.vstack([np.sin(theta), np.cos(theta)]).T
            circle = matplotlib.path.Path(verts * radius + center)

            ax2.set_boundary(circle, transform=ax2.transAxes)

            # plt.plot(ds_clim_pmax_am.lon.values, ds_clim_pmax_am.lat.values, marker='*')
            ax2.coastlines(color='grey')

            if len(self.points) == 1:
                ax2.scatter(self.points[0][0],self.points[0][1], color='red',s=15,
                            transform=ccrs.PlateCarree())
            else:
                norm = matplotlib.colors.Normalize(vmin=0, vmax=len(self.points))

                for pi, point in enumerate(self.points):
                    rgba_color = matplotlib.cm.jet(norm(pi))
                    ax2.scatter(point[0], point[1], color=rgba_color, s=15,
                                transform=ccrs.PlateCarree())
                    ax.scatter(_ds_file.time[pi], -15,
                               color=rgba_color, s=25, clip_on=False)

        11

        handles, labels = ax.get_legend_handles_labels()
        handle_list, label_list = [], []
        for handle, label in zip(handles, labels):
            if label not in label_list:
                handle_list.append(handle)
                label_list.append(label)
        plt.legend(handle_list, label_list)
#        ax.legend(loc='lower right', ncol=1,
#                  bbox_to_anchor=(.95,.1)) #loc='lower left')
        ax.set_ylabel('distance to ice edge [km]')

        ax.set_xlim([0, _ds_file.time.max() + 1])
        ax.set_xlabel('forecast time [days]')
        thisfig.savefig(ofile)
        print(ofile)



class MapPlot(GenericPlot):
    """ Plotting object for 2D maps """
    def __init__(self, conf, secname, metric):
        super().__init__(conf, metric)
        self.param = conf.params
        self.verif_name = metric.verif_name
        self.verif_expname = metric.verif_expname[0]
        self.verif_enssize = metric.verif_enssize[0]
        self.verif_dates = metric.verif_dates
        self.conf_verif_dates = metric.conf_verif_dates
        self.verif_fromyear = metric.verif_fromyear
        self.verif_toyear = metric.verif_toyear
        self.verif_mode = metric.verif_mode[0]
        self.verif_source = metric.verif_source[0]
        self.verif_fcsystem = metric.verif_fcsystem[0]
        self.metric_plottext = metric.plottext
        self.projection = conf.plotsets[secname].projection
        self.proj_options = conf.plotsets[secname].proj_options
        self.circle_border = conf.plotsets[secname].circle_border
        self.plot_extent = conf.plotsets[secname].plot_extent
        self.cmap = conf.plotsets[secname].cmap
        self.units = ''
        self.shortname = ''
        self.calib = metric.calib
        if self.calib:
            self.calib = True
            self.conf_calib_dates = metric.conf_calib_dates
            self.calib_fromyear = metric.calib_fromyear
            self.calib_toyear = metric.calib_toyear




        if self.cmap is None:
            if metric.default_cmap is None:
                self.cmap = 'cmo.ice'
            else:
                self.cmap = metric.default_cmap

        self._init_proj()


        if self.plot_extent is None:
            self.plot_global = True
        else:
            self.plot_extent = utils.csv_to_list(self.plot_extent)
            self.plot_extent = list(map(int, self.plot_extent))
            self.plot_global = False



        for i, k in utils.plot_params[self.param].items():
            setattr(self, i, k)


    def _init_proj(self):
        allowed_projections = ['LambertAzimuthalEqualArea', 'LambertConformal']
        if self.projection is None:
            self.projection = 'LambertAzimuthalEqualArea'


        if self.projection not in allowed_projections:
            raise ValueError(f'Projection {self.projection} is not implemented \n' \
                  f'Please use one of the following {allowed_projections}')

        if self.proj_options is None:
            if self.projection == 'LambertAzimuthalEqualArea':
                self.proj_options = {'central_latitude': 90}
            else:
                self.proj_options = {}
        else:
            proj_options_list = utils.csv_to_list(self.proj_options)
            proj_options_dict = {}
            for opt in proj_options_list:
                _opt_tmp = utils.csv_to_list(opt, sep="=")
                proj_options_dict[_opt_tmp[0]] = float(_opt_tmp[1])
            self.proj_options = proj_options_dict







    def plot(self, metric, verbose=False):
        """ plot all steps in file """
        _ds_file = self.xr_file
        var_list = [i for i in _ds_file.data_vars]
        for _vi, _var in enumerate(var_list):
            _steps = utils.convert_to_list(_ds_file[_var]['time'].values)

            for _step in _steps:
                _data = _ds_file[_var].sel(time=_step)
                if 'member' in _data.dims:
                    _data = _data.mean(dim='member')


                thisfig = plt.figure(figsize=(11.69, 8.27))  # A4 figure size
                # set up map axes
                proj = getattr(ccrs, self.projection)(**self.proj_options)
                if verbose:
                    utils.print_info(f'Target projection of plot {proj.proj4_init}')

                ax = plt.axes(projection=proj)

                if self.plot_global:
                    ax.set_global()

                polar_projs = ['LambertAzimuthalEqualArea']
                if self.circle_border == "yes" and self.projection in polar_projs:
                    lat_end = 90-60
                    ax.set_extent([-lat_end * 111000,
                                   lat_end * 111000,
                                   -lat_end * 111000,
                                   lat_end * 111000],
                                  crs=proj)

                    r_limit = 1 * (lat_end) * 111 * 1000
                    circle_path = matplotlib.path.Path.unit_circle()
                    circle_path = matplotlib.path.Path(circle_path.vertices.copy() * r_limit,
                                             circle_path.codes.copy())
                    ax.set_boundary(circle_path)

                if not self.plot_global:
                    ax.set_extent(self.plot_extent)

                if 'yc' in _data.dims:
                    _projection =  getattr(_ds_file[_var],'projection')
                    _proj_options = {}
                    for proj_param in ['central_longitude', 'central_latitude',
                                       'true_scale_latitude']:
                        if proj_param in _ds_file[_var].attrs:
                            _proj_options[proj_param] = getattr(_ds_file[_var],proj_param)
                    trans_grid = getattr(ccrs, _projection)(**_proj_options)

                    x_dim = _data['xc']
                    y_dim = _data['yc']

                elif f'yc_{_var}' in _data.dims:
                    _projection = getattr(_ds_file[_var], 'projection')
                    _proj_options = {}
                    for proj_param in ['central_longitude', 'central_latitude',
                                       'true_scale_latitude']:
                        if proj_param in _ds_file[_var].attrs:
                            _proj_options[proj_param] = getattr(_ds_file[_var], proj_param)
                    trans_grid = getattr(ccrs, _projection)(**_proj_options)

                    x_dim = _data[f'xc_{_var}']
                    y_dim = _data[f'yc_{_var}']

                elif 'latitude' in _data.dims:
                    trans_grid = ccrs.PlateCarree()
                    x_dim = _data['longitude']
                    y_dim = _data['latitude']
                    _data, x_dim = add_cyclic_point(_data.values, coord=x_dim.values)

                if verbose:
                    utils.print_info(f'Input projection of file {trans_grid.proj4_init}')

                levels = self.levels
                cmap = plt.get_cmap(self.cmap)

                extend = 'both'
                if self.clip:
                    _data = _data.clip(levels[0], levels[-1])
                    extend = 'neither'


                plot = ax.contourf(x_dim, y_dim, _data, levels, transform=trans_grid,
                                   cmap=cmap, extend=extend, vmin=levels[0])


                # only GA (needs to be removed or made more flexible)
                #plot_contour = ax.contour(x_dim, y_dim, _data, levels=[0.15], transform=trans_grid,
                #                          colors='cyan', linewidths=2)
                #ax.scatter(146.5, 76.8, color='red', s=20, transform=ccrs.PlateCarree())

                ax.add_feature(cartopy.feature.LAND,
                               zorder=1, edgecolor='k',
                               facecolor='slategray')


                gl = ax.gridlines(draw_labels=True,
                                  ylocs=range(-80,91,10),
                                  x_inline=False, y_inline=False,)
                #gl.top_labels = False
                #gl.right_labels = False
                gl.xformatter = LONGITUDE_FORMATTER
                gl.yformatter = LATITUDE_FORMATTER

                # add coast lines
                ax.coastlines(color='grey')
                cb = plt.colorbar(plot)
                cb.set_ticks(levels)
                cblabelstr = f'{self.shortname} {metric.legendtext} in {self.units}'
                cb.set_label(cblabelstr, labelpad=10)

                ax.set_title(self._create_title(_step, _var))
                if self.ofile is None:
                    ofile = self.get_filename_plot(varname=_var, time=_step,
                                           plotformat=self.format)
                else:
                    ofile = utils.csv_to_list(self.ofile)[_vi]
                print(ofile)
                thisfig.savefig(ofile)
                plt.close(thisfig)


    def _create_title(self, _step, _var):
        if _var == 'obs':
            _title = f'{self.verif_name} \n'
        else:
            _title = f'{self.verif_source} {self.verif_fcsystem} ' \
                     f'{self.verif_expname} {self.verif_mode} (enssize = {self.verif_enssize}) \n'



        if len(self.verif_dates) == 1 and self.verif_fromyear == self.verif_toyear:
            _fcdate = utils.string_to_datetime(self.verif_fromyear+self.verif_dates[0]) \
                      + dt.timedelta(days=int(_step))
            _title += f' {utils.datetime_to_string(_fcdate, "%Y-%m-%d")}'
        elif len(self.verif_dates) == 1 and self.verif_fromyear != self.verif_toyear:
            _title += f' {self.verif_dates[0]} averaged from ' \
                      f'{self.verif_fromyear} to {self.verif_toyear}'
        elif len(self.verif_dates) != 1:
            _title += f' combined dates {self.conf_verif_dates} averaged from ' \
                     f'{self.verif_fromyear} to {self.verif_toyear}'
        else:
            raise ValueError('create title function failed')

        if _var != 'obs':
            _title += f' (leadtime: {_step+1} days)'

        if self.calib:
            _title += f'\n calibrated using {self.conf_calib_dates} averaged from ' \
                     f'{self.calib_fromyear} to {self.calib_toyear}'

        _title += f' {self.metric_plottext}'

        return _title
