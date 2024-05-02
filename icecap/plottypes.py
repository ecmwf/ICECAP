""" Create 2-D filled contour plots """

import os
import ast
from matplotlib import pyplot as plt
import matplotlib
from mpl_toolkits.axes_grid1.inset_locator import InsetPosition
import numpy as np
import cartopy
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from cartopy.util import add_cyclic_point
import xarray as xr
from dateutil.relativedelta import relativedelta
import cmocean
import random


import utils

def attrsList_to_dict(attrs_list):
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
            output = []
            for f in files:
                output.append(xr.open_dataset(fdir+f))


        self.xr_file = output


class TsPlot(GenericPlot):
    """ Timeseries plot class """
    def __init__(self, conf, metric):
        super().__init__(conf, metric)
        self.points = metric.points
        self.mul_factor = 1


        if self.plottype == 'ice_distance':
            self.ylabel = 'distance to ice-edge [km]'
        if metric.area_statistic_unit == 'total' or \
                metric.area_statistic_function == 'sum':
            self.ylabel = f'{metric.ylabel} [$km^2$]'
        elif metric.area_statistic_unit == 'fraction':
            self.ylabel = f'{metric.ylabel} [fraction]'
        elif metric.area_statistic_unit == 'percent':
            self.ylabel = f'{metric.ylabel} [%]'
            self.mul_factor = 100

        if self.plottype in ['brier', 'crps']:
            self.ylabel = f'{metric.ylabel} (reference: persistence)'

        self.area_statistic_minvalue = None
        if metric.area_statistic_minvalue is not None:
            self.area_statistic_minvalue = metric.area_statistic_minvalue


        self.plot_shading = metric.plot_shading
        if self.plot_shading:
            self.plot_shading = list(map(int, utils.csv_to_list(metric.plot_shading)))

        self.inset_position = None
        if metric.inset_position:
            self.inset_position = metric.inset_position



    def plot(self, metric):
        """ plot timeseries
        :param verbose: verbosity on or off
        """

        xr_file_list = self.xr_file
        if not isinstance(self.xr_file, list):
            xr_file_list = [self.xr_file]

        for oi, _ds_file in enumerate(xr_file_list):

            var_list = list(_ds_file.data_vars)

            lsm = False
            for _var in var_list[:]:
                if 'noplot' in _var:
                    var_list.remove(_var)
                elif 'lsm' in _var:
                    lsm = True
                    var_list.remove(_var)


            thisfig = plt.figure(figsize=(8, 6))
            ax = plt.axes()

            ovar = self.plottype
            if len(xr_file_list) > 1:
                ovar += f'_{oi}'
            ofile = self.get_filename_plot(varname=ovar, time=None,
                                           plotformat=self.format)

            colors = ["#" + ''.join([random.choice('0123456789ABCDEF') for j in range(6)])
                     for i in range(50)]
            colors[0] = 'k'

            for _vi, _var in enumerate(var_list):
                _ds_file_var = _ds_file[_var]

                color = colors[_vi]
                linestyle = 'solid'

                # check if attributes for colors are set
                if f'{_var}-linecolor' in _ds_file.attrs:
                    color = _ds_file.attrs[f'{_var}-linecolor']
                if f'{_var}-linestyle' in _ds_file.attrs:
                    linestyle = _ds_file.attrs[f'{_var}-linestyle']

                if 'member' in _ds_file_var.dims:
                    _ds_file_var = _ds_file_var.dropna(dim='member').copy()
                    multi_member = True
                else:
                    multi_member = False

                if self.clip:
                    _ds_file_var = _ds_file_var.clip(self.levels[0], self.levels[-1])

                # multiply to get percentage if desired
                _ds_file_var = _ds_file_var*self.mul_factor

                label = _var

                if not multi_member:
                    ax.plot(_ds_file_var.time+1, _ds_file_var.values,
                            color=color, alpha=1, linewidth=2,
                            label=label, linestyle=linestyle)

                else:
                    print(_ds_file_var)
                    ax.plot(_ds_file_var.time+1, _ds_file_var.mean(dim='member').values,
                            color=color, alpha=1, linewidth=2,
                            label=label, linestyle=linestyle)


                    if self.plot_shading:
                        perc = self.plot_shading  # ,1/3*100]
                        shading = (np.linspace(0.2,1,len(perc)+1)**3)[1:]
                        for pi, p in enumerate(perc):
                            ax.fill_between(_ds_file_var.time+1, _ds_file_var.quantile(p/100, dim='member'),
                                             _ds_file_var.quantile(1-p/100, dim='member'),
                                             color='teal', alpha=shading[pi],
                                            label=f'probability: {p}-{100 - p}%')
                    else:
                        for m in _ds_file_var['member'].values:
                            ax.plot(_ds_file_var.time+1, _ds_file_var.sel(member=m).values,
                                    color=color, alpha=.1, linewidth=1,
                                    linestyle = linestyle)
                    for m in _ds_file_var['member'].values:
                        ax.plot(_ds_file_var.time + 1, _ds_file_var.sel(member=m).values,
                                color=color, alpha=.1, linewidth=1,
                                linestyle=linestyle)

            if self.points is not None or metric.region_extent:
                _ylim = ax.get_ylim()

                ax.set_ylim([_ylim[0],_ylim[1]+.3*(_ylim[1]-_ylim[0])])
                #ax.set_ylim([0,260])


                ax2 = plt.axes([0, 0, 1, 1],
                               projection=ccrs.NorthPolarStereo())
                if self.inset_position == '1':
                    ip = InsetPosition(ax, [0.05, 0.68, 0.25, 0.25])
                elif self.inset_position == '2':
                    ip = InsetPosition(ax, [0.72, 0.68, 0.25, 0.25])

                ax2.set_axes_locator(ip)

                self.region_extent = None
                if metric.region_extent:
                    self.region_extent = metric.region_extent
                    if self.region_extent:
                        self.region_extent = utils.csv_to_list(self.region_extent)
                        self.region_extent = list(map(float, self.region_extent))
                        region_extent_large = [-180,180,0,0]
                        region_extent_large[2] = self.region_extent[2] - 5
                        region_extent_large[3] = np.min([90, self.region_extent[3]])
                else:
                    region_extent_large = [-180,180,60,90]


                lat_end = 90 - region_extent_large[2]
                proj = ccrs.NorthPolarStereo()

                ax2.set_extent([-lat_end * 111000,
                               lat_end * 111000,
                               -lat_end * 111000,
                               lat_end * 111000],
                              crs=proj)

                r_limit = 1 * (lat_end) * 111 * 1000
                circle_path = matplotlib.path.Path.unit_circle()
                circle_path = matplotlib.path.Path(circle_path.vertices.copy() * r_limit,
                                                   circle_path.codes.copy())
                ax2.set_boundary(circle_path)




                ax2.set_extent(region_extent_large, ccrs.PlateCarree())
                if self.region_extent:
                    region_test =  '/'.join(utils.csv_to_list(metric.region_extent))
                    if lsm:
                        lsm_nan = (~np.isnan(_ds_file['lsm'].values)).sum()
                        region_test = f'{region_test} (#:{lsm_nan})'

                    ttl = ax2.set_title(region_test,
                              fontsize=10)
                    ttl.set_position([.5, 0.99])

                # plt.plot(ds_clim_pmax_am.lon.values, ds_clim_pmax_am.lat.values, marker='*')
                ax2.coastlines(color='grey')
                if lsm:
                    lsm_data = _ds_file['lsm']

                    lsm_data = xr.where(lsm_data==1,1,0)

                    lsm_data_1 = xr.where(lsm_data.longitude < 0, float('nan'), lsm_data)
                    lsm_data_2 = xr.where(lsm_data.longitude > 0, float('nan'), lsm_data)

                    ax2.contourf(lsm_data.longitude,
                                  lsm_data.latitude,
                                  lsm_data_1, hatches=['...'], levels=[0.5,1.5], alpha=0.5,
                                  colors='red', transform=ccrs.PlateCarree())

                    ax2.contourf(lsm_data.longitude,
                                 lsm_data.latitude,
                                 lsm_data_2, hatches=['...'], levels=[0.5, 1.5], alpha=0.5,
                                 colors='red', transform=ccrs.PlateCarree())



                if self.points is not None:
                    if len(self.points) == 1:
                        ax2.scatter(self.points[0][0],self.points[0][1], color='red',s=15,
                                    transform=ccrs.PlateCarree())
                    else:
                        norm = matplotlib.colors.Normalize(vmin=0, vmax=len(self.points))

                        for pi, point in enumerate(self.points):
                            rgba_color = matplotlib.cm.jet(norm(pi))
                            ax2.scatter(point[0], point[1], color=rgba_color, s=15,
                                        transform=ccrs.PlateCarree())
                            ax.scatter(_ds_file_var.time[pi]+1, -15,
                                       color=rgba_color, s=25, clip_on=False)


            handles, labels = ax.get_legend_handles_labels()
            handle_list, label_list = [], []
            for handle, label in zip(handles, labels):
                if label not in label_list:
                    handle_list.append(handle)
                    label_list.append(label)

            box = ax.get_position()
            ax.set_position([box.x0, box.y0 + box.height * 0.1,
                             box.width, box.height * 0.9])

            ax.legend(handle_list, label_list,
                      loc='upper center', bbox_to_anchor=(0.5, -.12),
                      ncol=np.min([len(handle_list),3]), fancybox=True, shadow=True)

            ax.set_ylabel(self.ylabel)
            _title = self._create_title()
            ax.set_title(_title)

            ax.set_xlim([0.5, _ds_file_var.time.max() + 1.5])
            ax.set_xlabel('forecast time [days]')
            thisfig.savefig(ofile)
            utils.print_info(f'output file: {ofile}')

    def plot_BAC(self, metric):
        """ plot timeseries
        :param verbose: verbosity on or off
        """

        plot_dict = {
            'obs': {
                'color':'k',
                'label' : self.verif_name,
            },
            'obs-hc': {
                'color':'red',
                'label' : f'{self.verif_name} hc period'
            },
            'model': {
                'color': 'blue',
                'label': f'{self.verif_expname}',
            },
            'model-topaz4' : {
                'color':'blue',
                'label':'forecast',
            },
            'model-topaz5': {
                'color': 'green',
                'label': 'forecast',
            }
        }


        _ds_file = self.xr_file
        var_list = list(_ds_file.data_vars)

        lsm = False
        for _var in var_list[:]:
            if 'noplot' in _var:
                var_list.remove(_var)
            elif 'lsm' in _var:
                lsm = True
                var_list.remove(_var)




        thisfig = plt.figure(figsize=(8, 6))
        ax = plt.axes()
        ofile = self.get_filename_plot(varname='model', time=None,
                                       plotformat=self.format)

        for _var in var_list:
            _ds_file = self.xr_file[_var]
            if _var == 'obs-hc':
                _ds_file = _ds_file.mean(dim='date').dropna(dim='member').isel(member=0)

            if 'member' in _ds_file.dims:
                _ds_file = _ds_file.dropna(dim='member').copy()
                multi_member = True
            else:
                multi_member = False



            if self.clip:
                _ds_file = _ds_file.clip(self.levels[0], self.levels[-1])

            # multiply to get percentage if desired
            _ds_file = _ds_file*self.mul_factor

            _var_dict = _var
            if 'obs' not in _var:
                _var_dict = 'model'

            if not multi_member:
                ax.plot(_ds_file.time+1, _ds_file.values,
                        color=plot_dict[_var_dict]['color'], alpha=1, linewidth=2,
                        label=plot_dict[_var_dict]['label'])

            else:
                if _var_dict =='model':
                    ax.plot(_ds_file.time+1, _ds_file.mean(dim='member').values,
                            color=plot_dict[_var_dict]['color'], alpha=1, linewidth=2,
                            label=plot_dict[_var_dict]['label'])


                if self.plot_shading:
                    perc = self.plot_shading  # ,1/3*100]
                    shading = (np.linspace(0.2,1,len(perc)+1)**3)[1:]
                    for pi, p in enumerate(perc):
                        ax.fill_between(_ds_file.time+1, _ds_file.quantile(p/100, dim='member'),
                                         _ds_file.quantile(1-p/100, dim='member'),
                                         color='teal', alpha=shading[pi],
                                        label=f'probability: {p}-{100 - p}%')
                else:
                    for m in _ds_file['member'].values:
                        ax.plot(_ds_file.time+1, _ds_file.sel(member=m).values,
                                color=plot_dict[_var_dict]['color'], alpha=.1, linewidth=1)
                for m in _ds_file['member'].values:
                    ax.plot(_ds_file.time + 1, _ds_file.sel(member=m).values,
                            color=plot_dict[_var_dict]['color'], alpha=.1, linewidth=1)

        if self.points is not None or metric.region_extent:
            _ylim = ax.get_ylim()

            ax.set_ylim([_ylim[0],_ylim[1]+.3*(_ylim[1]-_ylim[0])])
            #ax.set_ylim([0,260])


            ax2 = plt.axes([0, 0, 1, 1],
                           projection=ccrs.NorthPolarStereo())
            if self.inset_position == '1':
                ip = InsetPosition(ax, [0.05, 0.68, 0.25, 0.25])
            elif self.inset_position == '2':
                ip = InsetPosition(ax, [0.72, 0.68, 0.25, 0.25])

            ax2.set_axes_locator(ip)

            self.region_extent = None
            if metric.region_extent:
                self.region_extent = metric.region_extent
                if self.region_extent:
                    self.region_extent = utils.csv_to_list(self.region_extent)
                    self.region_extent = list(map(float, self.region_extent))
                    region_extent_large = [-180,180,0,0]
                    region_extent_large[2] = self.region_extent[2] - 5
                    region_extent_large[3] = np.min([90, self.region_extent[3]])
            else:
                region_extent_large = [-180,180,60,90]


            lat_end = 90 - region_extent_large[2]
            proj = ccrs.NorthPolarStereo()

            ax2.set_extent([-lat_end * 111000,
                           lat_end * 111000,
                           -lat_end * 111000,
                           lat_end * 111000],
                          crs=proj)

            r_limit = 1 * (lat_end) * 111 * 1000
            circle_path = matplotlib.path.Path.unit_circle()
            circle_path = matplotlib.path.Path(circle_path.vertices.copy() * r_limit,
                                               circle_path.codes.copy())
            ax2.set_boundary(circle_path)




            ax2.set_extent(region_extent_large, ccrs.PlateCarree())
            if self.region_extent:
                region_test =  '/'.join(utils.csv_to_list(metric.region_extent))
                if lsm:
                    lsm_nan = (~np.isnan(self.xr_file['lsm'].values)).sum()
                    region_test = f'{region_test} (#:{lsm_nan})'

                ttl = ax2.set_title(region_test,
                          fontsize=10)
                ttl.set_position([.5, 0.99])

            # plt.plot(ds_clim_pmax_am.lon.values, ds_clim_pmax_am.lat.values, marker='*')
            ax2.coastlines(color='grey')
            if lsm:
                lsm_data = self.xr_file['lsm']

                lsm_data = xr.where(lsm_data==1,1,0)

                lsm_data_1 = xr.where(self.xr_file['lsm'].longitude < 0, float('nan'), lsm_data)
                lsm_data_2 = xr.where(self.xr_file['lsm'].longitude > 0, float('nan'), lsm_data)

                ax2.contourf(self.xr_file['lsm'].longitude,
                              self.xr_file['lsm'].latitude,
                              lsm_data_1, hatches=['...'], levels=[0.5,1.5], alpha=0.5,
                              colors='red', transform=ccrs.PlateCarree())

                ax2.contourf(self.xr_file['lsm'].longitude,
                             self.xr_file['lsm'].latitude,
                             lsm_data_2, hatches=['...'], levels=[0.5, 1.5], alpha=0.5,
                             colors='red', transform=ccrs.PlateCarree())



            if self.points is not None:
                if len(self.points) == 1:
                    ax2.scatter(self.points[0][0],self.points[0][1], color='red',s=15,
                                transform=ccrs.PlateCarree())
                else:
                    norm = matplotlib.colors.Normalize(vmin=0, vmax=len(self.points))

                    for pi, point in enumerate(self.points):
                        rgba_color = matplotlib.cm.jet(norm(pi))
                        ax2.scatter(point[0], point[1], color=rgba_color, s=15,
                                    transform=ccrs.PlateCarree())
                        ax.scatter(_ds_file.time[pi]+1, -15,
                                   color=rgba_color, s=25, clip_on=False)


        handles, labels = ax.get_legend_handles_labels()
        handle_list, label_list = [], []
        for handle, label in zip(handles, labels):
            if label not in label_list:
                handle_list.append(handle)
                label_list.append(label)

        box = ax.get_position()
        ax.set_position([box.x0, box.y0 + box.height * 0.1,
                         box.width, box.height * 0.9])

        ax.legend(handle_list, label_list,
                  loc='upper center', bbox_to_anchor=(0.5, -.12),
                  ncol=np.min([len(handle_list),3]), fancybox=True, shadow=True)

        ax.set_ylabel(self.ylabel)
        _title = self._create_title()
        ax.set_title(_title)

        ax.set_xlim([0.5, _ds_file.time.max() + 1.5])
        ax.set_xlabel('forecast time [days]')
        thisfig.savefig(ofile)
        utils.print_info(f'output file: {ofile}')


    def _create_title(self):

        _title = f'{self.verif_source} {self.verif_fcsystem} ' \
                 f'{self.verif_expname} {self.verif_mode} (enssize = {self.verif_enssize}) \n'

        # calc target date
        # check if only one date
        if self.verif_fromyear:
            _verif_fromyear = int(self.verif_fromyear)
            _verif_toyear = int(self.verif_toyear)

        if len(self.verif_dates) == 1:
            _init_time = self.verif_dates[0]

        elif 'to' in self.conf_verif_dates:
            _init_time = self.conf_verif_dates

        if self.verif_fromyear is None:
            if len(self.verif_dates) == 1:
                _title += f' init-time {_init_time}'
            else:
                _title += f' combined dates init-time {_init_time}'
        else:
            _title += f' combined dates init-time {_init_time}' \
                      f' ({_verif_fromyear} - {_verif_toyear})'

        if self.area_statistic_minvalue is not None:
            _title += f'(cells wit sic>{self.area_statistic_minvalue} set to 1)'


        if self.calib:
            _title += f'\n calibrated using {self.conf_calib_dates}'
            if self.calib_fromyear:
                _title += f' averaged from {self.calib_fromyear} to {self.calib_toyear}'

        return _title



class MapPlot(GenericPlot):
    """ Plotting object for 2D maps """
    def __init__(self, conf, secname, metric):
        super().__init__(conf, metric)
        self.param = conf.params

        self.metric_plottext = metric.plottext
        self.projection = conf.plotsets[secname].projection
        self.proj_options = conf.plotsets[secname].proj_options
        self.circle_border = conf.plotsets[secname].circle_border
        self.region_extent = conf.plotsets[secname].region_extent
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


        if self.region_extent is None:
            self.plot_global = True
        else:
            self.region_extent = utils.csv_to_list(self.region_extent)
            self.region_extent = list(map(int, self.region_extent))
            self.plot_global = False




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
        if not isinstance(self.xr_file, list):
            xr_file_list = [self.xr_file]

        for _ds_file in xr_file_list:
            var_list = list(_ds_file.data_vars)

            # remove lsm and noplot variables from metric
            var_list = [d for d in var_list if ('lsm' not in d and 'noplot' not in d)]



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
                    cb.set_label(cblabelstr, labelpad=10)

                    for i in _ds_file.attrs:
                        if _var in i and any(str(param) in i for param in np.arange(10)):
                            kw = attrsList_to_dict(_ds_file.attrs[i])

                            atype = kw['attr_type']
                            kw.pop('attr_type', None)

                            if atype == 'ax.text':
                                if 'transform' in kw:
                                    kw.pop('transform', None)
                                    ax.text(**kw, transform=ax.transAxes)
                                else:
                                    ax.text(**kw)
                            elif atype == 'cb.set_label':
                                cb.set_label(**kw, labelpad=10)


                    ax.set_title(self._create_title(_step, _var))

                    if self.points is not None:
                        if len(self.points) == 1:
                            ax.scatter(self.points[0][0], self.points[0][1], color='red', s=15,
                                        transform=ccrs.PlateCarree())


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
        elif self.verif_modelname is not None:
            _title = f'{self.verif_source} {self.verif_fcsystem} {self.verif_modelname} ' \
                     f'{self.verif_expname} {self.verif_mode} (enssize = {self.verif_enssize}) \n'
        else:
            _title = f'{self.verif_source} {self.verif_fcsystem} ' \
                     f'{self.verif_expname} {self.verif_mode} (enssize = {self.verif_enssize}) \n'

        # calc target date
        # check if only one date
        if self.verif_fromyear:
            _verif_fromyear = int(self.verif_fromyear)
            _verif_toyear = int(self.verif_toyear)


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
            by_tmp = self.conf_verif_dates.split('/by/')[1]
            _dates = self.conf_verif_dates.split('/by/')[0]
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

        elif self.verif_fromyear is None:
            if len(self.verif_dates) == 1:
                _title += f' valid-time {_target_time}'
            else:
                _title += f' combined dates valid-time {_target_time}'
        else:
            _title += f' combined dates valid-time {_target_time}' \
                      f' ({_verif_fromyear} - {_verif_toyear})'

        if _var != 'obs' and self.plottype not in ['freeze-up']:
            _title += f' (leadtime: {_step+1} days)'





        if self.calib:
            _title += f'\n calibrated using {self.conf_calib_dates}'
            if self.calib_fromyear:
                _title += f' from {self.calib_fromyear} to {self.calib_toyear} ' \
                          f'(enssize = {self.calib_enssize})'



        _title += f' {self.metric_plottext}'

        return _title
