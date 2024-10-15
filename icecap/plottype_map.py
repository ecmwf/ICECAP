""" Create 2-D filled contour plots"""


import numpy as np
import cartopy
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.util import add_cyclic_point
from matplotlib import pyplot as plt
import matplotlib
from dateutil.relativedelta import relativedelta
import cmocean

import plottypes
import utils

class MapPlot(plottypes.GenericPlot):
    """ Plotting object for 2D maps """
    def __init__(self, conf, secname, metric):
        super().__init__(conf, metric)
        self.param = conf.params

        self.metric_plottext = metric.plottext
        self.projection = conf.plotsets[secname].projection
        self.proj_options = conf.plotsets[secname].proj_options
        self.circle_border = conf.plotsets[secname].circle_border
        self.region_extent = metric.region_extent
        self.cmap = conf.plotsets[secname].cmap
        self.units = ''
        self.shortname = ''
        self.points = metric.points


        if self.cmap is None:
            if metric.default_cmap is None:
                self.cmap = 'cmo.ice'
            else:
                self.cmap = metric.default_cmap

        self._init_proj()


        if self.region_extent is not None:
            self.region_extent = utils.csv_to_list(self.region_extent)
            self.region_extent = list(map(float, self.region_extent))
            self.plot_global = False
        else:
            self.plot_global = True







        for i, k in utils.plot_params[self.param].items():
            setattr(self, i, k)


    def _init_proj(self):
        allowed_projections = ['LambertAzimuthalEqualArea', 'LambertConformal',
                               'Stereographic']
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
        xr_file_list = self.xr_file
        ofiles_return = []
        if not isinstance(self.xr_file, list):
            xr_file_list = [self.xr_file]

        for _ds_file in xr_file_list:
            if 'time' not in _ds_file.dims:
                _ds_file = _ds_file.expand_dims('time')

            var_list = list(_ds_file.data_vars)

            # remove lsm and noplot variables from metric
            var_list = [d for d in var_list if ('lsm' not in d and 'noplot' not in d)]

            #check if pvalue variable exists (this is significance and will be hatched)
            _var_list_new = []
            sig_list = []
            for _var in var_list:
                _var_strip = _var.replace('-value', '').replace('-pvalue', '')
                if _var_strip + '-value' not in _var_list_new:
                    if _var_strip + '-value' in var_list and _var_strip + '-pvalue' in var_list:
                        _var_list_new.append(_var_strip + '-value')
                        sig_list.append(1)
                    else:
                        _var_list_new.append(_var_strip)
                        sig_list.append(0)

            var_list = _var_list_new

            for _vi, _var in enumerate(var_list):
                _steps = utils.convert_to_list(_ds_file[_var]['time'].values)


                levels = self.levels
                norm = self.norm
                if isinstance(self.cmap, str):
                    cmap = plt.get_cmap(self.cmap)
                else:
                    cmap = self.cmap



                # check if attributes specifying label etc are passed with xarray DataArray
                if f'{_var}-cmap' in _ds_file.attrs:
                    cmap = plt.get_cmap(_ds_file.attrs[f'{_var}-cmap'])
                # if norm is given it must be None
                if f'{_var}-norm' in _ds_file.attrs:
                    norm = None
                if f'{_var}-levels' in _ds_file.attrs:
                    tmp_level = _ds_file.attrs[f'{_var}-levels'].replace('[','').replace(']','').split(' ')
                    levels = [float(lev) for lev in tmp_level if lev != '']


                for _step in _steps:
                    _data = _ds_file[_var].sel(time=_step)



                    if 'member' in _data.dims:
                        _data = _data.mean(dim='member')



                    thisfig = plt.figure(figsize=(11.69, 8.27))  # A4 figure size
                    # set up map axes
                    proj = getattr(ccrs, self.projection)(**self.proj_options)

                    # first check for yc/xc coordinates; then for longitude/latitude
                    if 'yc' in _data.dims:
                        _projection = getattr(_ds_file[_var], 'projection')
                        _proj_options = {}
                        for proj_param in ['central_longitude', 'central_latitude',
                                           'true_scale_latitude']:
                            if proj_param in _ds_file[_var].attrs:
                                _proj_options[proj_param] = getattr(_ds_file[_var], proj_param)
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
                        utils.print_info(f'Target projection of plot {proj.proj4_init}')


                    ax = plt.axes(projection=proj)

                    if self.plot_global:
                        ax.set_global()

                    polar_projs = ['LambertAzimuthalEqualArea', 'Stereographic']
                    if self.circle_border == "yes" and self.projection in polar_projs:
                        lat_end = 90-50 #60
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
                        ax.set_extent(self.region_extent,
                                      crs=ccrs.PlateCarree())





                    if self.clip:
                        _data = _data.clip(levels[0], levels[-1])
                        extend = 'neither'
                    else:
                        extend = 'both'
                        # if levels[0] is zero and trans_grid != proj
                        # missing values are drawn as lowest color
                        # this workaround ensures that this is not the case
                        levels[0] -= 1e-05



                    if f'{_var}-map_plot' in _ds_file.attrs:
                        if _ds_file.attrs[f'{_var}-map_plot'] == 'pcolormesh':
                            plot = ax.pcolormesh(x_dim, y_dim, _data, transform=trans_grid,
                                                 cmap=cmap, norm=norm)
                    else:
                        plot = ax.contourf(x_dim, y_dim, _data, levels, transform=trans_grid,
                                                                cmap=cmap, extend=extend, norm=norm)

                    if sig_list[_vi] == 1:
                        _data_sig = _ds_file[_var.replace('value','pvalue')].sel(time=_step)
                        ax.contourf(x_dim, y_dim, _data_sig< 0.05, levels=[0.5, 1.5],
                                    hatches=['.....'], alpha=0.25,transform=trans_grid)


                    ax.add_feature(cartopy.feature.LAND,
                                   zorder=1, edgecolor='k',
                                   facecolor='darkgray')
                    plt.gca().set_facecolor("darkgray")



                    gl = ax.gridlines(draw_labels=True,
                                      ylocs=range(-80,91,10),
                                      x_inline=False, y_inline=False,)
                    #gl.top_labels = False
                    #gl.right_labels = False
                    gl.xformatter = LONGITUDE_FORMATTER
                    gl.yformatter = LATITUDE_FORMATTER

                    # add coast lines
                    ax.coastlines(color='grey')
                    cb = plt.colorbar(plot)#, location='left')

                    # revert level changes to ensure NaN are plotted with background color
                    if extend == 'both':
                        levels[0] += 1e-05

                    if self.ticks is None:
                        cb.set_ticks(levels)
                    if self.ticklabels is not None:
                        cb.set_ticks(self.ticks)
                        cb.set_ticklabels(self.ticklabels)


                    cblabelstr = f'{self.shortname} {metric.legendtext} in {self.units}'

                    if self.plottype in ['brier', 'crps']:
                        cblabelstr = f'{metric.legendtext} (reference: persistence)'


                    cb.set_label(cblabelstr, labelpad=10)

                    for i in _ds_file.attrs:
                        if _var in i and any(f'-{str(param)}' in i for param in np.arange(10)):
                            kw = plottypes.attrsList_to_dict(_ds_file.attrs[i])

                            atype = kw['attr_type']
                            kw.pop('attr_type', None)

                            if atype == 'ax.text':
                                if 'transform' in kw:
                                    kw.pop('transform', None)
                                    ax.text(**kw, transform=ax.transAxes)
                                else:
                                    ax.text(**kw)
                            elif atype == 'cb.set_label':
                                cb.set_label(**kw, labelpad=5)



                    ax.set_title(self._create_title(_step, _var))

                    if self.points is not None:
                        if len(self.points) == 1:
                            ax.scatter(self.points[0][0], self.points[0][1], color='red', s=15,
                                        transform=ccrs.PlateCarree())

                    ax.text(0.03, .97, self.plottype, style='italic',
                            horizontalalignment='left',
                            verticalalignment='top', transform=ax.transAxes,
                            fontsize=14, bbox=dict(facecolor='blue', alpha=0.1))

                    if self.ofile is None:
                        ofile = self.get_filename_plot(varname=_var, time=_step,
                                               plotformat=self.format)
                    else:
                        ofile = utils.csv_to_list(self.ofile)[_vi]
                    ofiles_return.append(ofile)
                    print(ofile)
                    thisfig.savefig(ofile)
                    plt.close(thisfig)
        return ofiles_return

    def _create_title(self, _step, _var):
        if 'obs' in _var or 'verdata' in _var:
            _title = f'{self.verif_name} \n'
        elif 'persistence' in _var:
            _title = 'persistence \n'
        elif self.verif_modelname is not None:
            _title = f'{self.verif_source} {self.verif_fcsystem} {self.verif_modelname} ' \
                     f'{self.verif_expname} {self.verif_mode} (enssize = {self.verif_enssize}) \n'
        else:
            _title = f'{self.verif_source} {self.verif_fcsystem} ' \
                     f'{self.verif_expname} {self.verif_mode} (enssize = {self.verif_enssize}) \n'

        # calc target date
        # check if only one date
        if self.verif_fromyear != [None]:
            _verif_fromyear = int(self.verif_fromyear[0])
            _verif_toyear = int(self.verif_toyear[0])


        if len(self.verif_dates) == 1:
            _tmp_date = self.verif_dates[0]
            if len(self.verif_dates[0]) == 4:
                _tmp_date = f'2000{self.verif_dates[0]}'
            _target_time = utils.string_to_datetime(_tmp_date)

            _target_time += relativedelta(days=int(_step))
            if len(self.verif_dates[0]) == 4:
                _target_time = utils.datetime_to_string(_target_time, '%m-%d')
            else:
                _target_time = utils.datetime_to_string(_target_time, '%Y-%m-%d')

        elif 'to' in self.conf_verif_dates:
            if '/by/' in self.conf_verif_dates:
                by_tmp = self.conf_verif_dates.split('/by/')[1]
                _dates = self.conf_verif_dates.split('/by/')[0]
                _dates = _dates.split('/to/')
            if '/only/' in self.conf_verif_dates:
                by_tmp = self.conf_verif_dates.split('/only/')[1]
                _dates = self.conf_verif_dates.split('/only/')[0]
                _dates = _dates.split('/to/')


            yymm_format = False
            if len(_dates[0]) == 4:
                yymm_format = True


            if yymm_format:
                _dates = [f'2000{d}' for d in _dates]
            _dates_dt = [utils.string_to_datetime(d) for d in _dates]
            _dates_dt_target = [d+relativedelta(days=int(_step)) for d in _dates_dt]

            if yymm_format:
                _next_year = [1 if d.year > 2000 else 0 for d in _dates_dt_target]
                _verif_fromyear += _next_year[0]
                _verif_toyear += _next_year[1]
                _target_time = [utils.datetime_to_string(d, '%m-%d') for d in _dates_dt_target]
            else:
                _target_time = [utils.datetime_to_string(d, '%Y-%m-%d') for d in _dates_dt_target]
            _target_time = '/to/'.join(_target_time)
            _target_time += f'/by/{by_tmp}'


        if self.plottype in ['freeze-up']:
            _init_time = self.conf_verif_dates
            _title += f' init-time {_init_time}'

            if self.verif_fromyear[0] is not None:
                _title += f' ({_verif_fromyear[0]} - {_verif_toyear[0]})'

        elif self.verif_fromyear[0] is None:
            if len(self.verif_dates) == 1:
                _title += f' valid-time {_target_time}'
            else:
                _title += f' combined dates valid-time {_target_time}'
        else:
            _title += f' combined dates valid-time {_target_time}' \
                      f' ({_verif_fromyear} - {_verif_toyear})'

        if _var != 'obs' and self.plottype not in ['freeze_up']:
            _title += f' (leadtime: {_step+1} days)'





        if self.calib:
            _title += f'\n calibrated using {self.conf_calib_dates}'
            if self.calib_fromyear:
                _title += f' from {self.calib_fromyear[0]} to {self.calib_toyear[0]} ' \
                          f'(enssize = {self.calib_enssize})'



        _title += f' {self.metric_plottext}'

        return _title
