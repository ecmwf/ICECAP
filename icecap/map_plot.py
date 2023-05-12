""" Create 2-D filled contour plots """

import os
from matplotlib import pyplot as plt
import cartopy
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.util import add_cyclic_point
import xarray as xr
import matplotlib.path as mpath
import cmocean


import utils


class MapPlot:
    """ Plotting object for 2D maps """
    def __init__(self, conf, secname, metric):
        self.data = None
        self.plotdir = conf.plotdir
        self.param = conf.params
        self.metric = metric
        self.format = 'png'
        self.verif_expname = metric.verif_expname[0]
        self.verif_enssize = metric.verif_enssize[0]
        self.verif_fromdate = metric.verif_fromdate[0]
        self.verif_todate = metric.verif_todate[0]
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


        if self.cmap is None:
            if metric.default_cmap is None:
                self.cmap = 'cmo.ice'
            else:
                self.cmap = metric.default_cmap

        # levels will probably be a config entry at some point
        self.levels = None
        if self.levels is None:
            self.levels = metric.levels

        self._init_proj()
        self.load(metric)


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
            proj_options_dict = dict()
            for opt in proj_options_list:
                _opt_tmp = utils.csv_to_list(opt, sep="=")
                proj_options_dict[_opt_tmp[0]] = float(_opt_tmp[1])
            self.proj_options = proj_options_dict







    def load(self, metric):
        """ load metric file """
        fname = metric.get_filename_metric()
        ds_file = xr.open_dataset(fname)
        self.xr_file = ds_file


    def plot(self, metric, verbose=False):
        """ plot all steps in file """
        _ds_file = self.xr_file
        var_list = [i for i in _ds_file.data_vars]
        for _var in var_list:
            _steps = utils.convert_to_list(_ds_file[_var]['time'].values)

            for _step in _steps:
                _data = _ds_file[_var].sel(time=_step)


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
                    lat_end = 90-30
                    ax.set_extent([-lat_end * 111000,
                                   lat_end * 111000,
                                   -lat_end * 111000,
                                   lat_end * 111000],
                                  crs=proj)

                    r_limit = 1 * (lat_end) * 111 * 1000
                    circle_path = mpath.Path.unit_circle()
                    circle_path = mpath.Path(circle_path.vertices.copy() * r_limit,
                                             circle_path.codes.copy())
                    ax.set_boundary(circle_path)

                if not self.plot_global:
                    ax.set_extent(self.plot_extent)

                if 'yc' in _data.dims:
                    _projection =  getattr(_ds_file[_var],'projection')
                    _proj_options = dict()
                    for proj_param in ['central_longitude', 'central_latitude',
                                       'true_scale_latitude']:
                        if proj_param in _ds_file[_var].attrs:
                            _proj_options[proj_param] = getattr(_ds_file[_var],proj_param)
                    trans_grid = getattr(ccrs, _projection)(**_proj_options)

                    x_dim = _data['xc']
                    y_dim = _data['yc']

                elif f'yc_{_var}' in _data.dims:
                    _projection = getattr(_ds_file[_var], 'projection')
                    _proj_options = dict()
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



                plot = ax.contourf(x_dim, y_dim, _data, levels, transform=trans_grid,
                                   cmap=cmap, extend='both')

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
                cblabelstr = '{} {} in {}'.format(self.shortname,
                                                  metric.legendtext, self.units)
                cb.set_label(cblabelstr, labelpad=10)

                ax.set_title(self._create_title(_step))
                ofile = self.get_filename_plot(varname=_var, time=_step,
                                       plotformat=self.format)
                print(ofile)
                thisfig.savefig(ofile)


    def _create_title(self, _step):
        _title = f'{self.metric_plottext} {self.param} \n {self.verif_source} ' \
                 f'{self.verif_fcsystem} {self.verif_expname} ({self.verif_enssize})'

        #if self.verif_mode == 'fc':
        #    _fcdate = utils.string_to_datetime(self.verif_refdate)+ dt.timedelta(days=int(_step))
        #    _title += f' {utils.datetime_to_string(_fcdate, "%Y-%m-%d")}'

        return _title
        #sic ecmwf extended-range 0001 date enssize

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
