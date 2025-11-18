""" Create timeseries plots"""

import random
from collections import Counter
import cartopy
import cartopy.crs as ccrs
from matplotlib import pyplot as plt
import numpy as np
import matplotlib
import xarray as xr
import matplotlib as mpl

import plottypes
import utils


class TsPlot(plottypes.GenericPlot):
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
        ofiles_return = []
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


            # check if pvalue variable exists (this is significance and will be hatched)
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

            norm = matplotlib.colors.Normalize(vmin=0, vmax=1000)

            # colormap possible values = viridis, jet, spectral
            colors = matplotlib.cm.jet(norm(np.linspace(0,1,len(var_list))), bytes=False)


            for _vi, _var in enumerate(var_list):
                _ds_file_var = _ds_file[_var]


                if 'obs' in _var:
                    color='k'
                else:
                    color = colors[_vi]
                    color = 'blue'

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

                if 'time' in _ds_file_var.dims:
                    x_axis_values = _ds_file_var.time.values+1
                elif 'date' in _ds_file_var.dims:
                    x_axis_values = _ds_file_var.date.values


                if 'persistence' in _var:
                    color = 'grey'
                    linestyle = 'dotted'
                    if len(_ds_file_var.values) == 1:
                        ax.axhline(y=_ds_file_var.values, color=color,
                                   linestyle=linestyle, label='persistence')
                        continue

                if not multi_member:
                    ax.plot(x_axis_values, _ds_file_var.values,
                            color=color, alpha=1, linewidth=2,
                            label=label, linestyle=linestyle)

                    if sig_list[_vi] == 1:
                        _ds_file_var_sig = _ds_file[_var.replace('value', 'pvalue')]
                        vals_p = _ds_file_var_sig.values
                        alpha = 0.05
                        ax.scatter(x_axis_values, _ds_file_var.values, marker='o', facecolors='none',
                                   edgecolors=color)
                        ax.scatter((x_axis_values)[vals_p < alpha], _ds_file_var.values[vals_p < alpha],
                                   marker='o', color=color)

                else:
                    ax.plot(x_axis_values, _ds_file_var.mean(dim='member').values,
                            color=color, alpha=1, linewidth=2,
                            label=label, linestyle=linestyle)


                    if self.plot_shading:
                        perc = self.plot_shading  # ,1/3*100]
                        shading = (np.linspace(0.2,1,len(perc)+1)**3)[1:]
                        for pi, p in enumerate(perc):
                            ax.fill_between(x_axis_values, _ds_file_var.quantile(p/100, dim='member'),
                                             _ds_file_var.quantile(1-p/100, dim='member'),
                                             color='teal', alpha=shading[pi],
                                            label=f'probability: {p}-{100 - p}%')
                    else:
                        for m in _ds_file_var['member'].values:
                            ax.plot(x_axis_values, _ds_file_var.sel(member=m).values,
                                    color=color, alpha=.1, linewidth=1,
                                    linestyle = linestyle)

            if self.points is not None or metric.area_statistic_function is not None:
                #metric.region_extent or metric.nsidc_region:
                _ylim = ax.get_ylim()

                ax.set_ylim([_ylim[0],_ylim[1]+.3*(_ylim[1]-_ylim[0])])

                
                if self.inset_position == '1':
                    ax_pos = [0.05, 0.68, 0.25, 0.25]
                elif self.inset_position == '2':
                    ax_pos = [0.72, 0.68, 0.25, 0.25]
                ax2 = ax.inset_axes(ax_pos, projection=ccrs.NorthPolarStereo())
                
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
                if self.region_extent or metric.nsidc_region:
                    if self.region_extent:
                        region_test =  '/'.join(utils.csv_to_list(metric.region_extent))
                    elif metric.nsidc_region:
                        region_test = metric.nsidc_region

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




            ax.set_xlabel('forecast time [days]')

            x_idx_max = np.min([10,len(x_axis_values)])
            x_tick_idx = np.linspace(0,len(x_axis_values)-1,x_idx_max).astype(int)

            ax.set_xticks(x_axis_values[x_tick_idx])
            ax.set_xticklabels(x_axis_values[x_tick_idx])

            ax.text(0.03, .97, self.plottype, style='italic',
                    horizontalalignment='left',
                    verticalalignment='top', transform=ax.transAxes,
                    fontsize=14, bbox=dict(facecolor='blue', alpha=0.1))


            thisfig.savefig(ofile)
            ofiles_return.append(ofile)
            utils.print_info(f'output file: {ofile}')

        return ofiles_return

    def _create_title(self):
        """
        Create title string for plot
        :return: title string
        """

        if self.verif_modelname is not None:
            _title = f'{self.verif_modelname} {self.verif_expname}'
        elif self.verif_source == 'ecmwf' and self.verif_expname == '0001':
            _title = 'ecmwf oper'
        else:
            _title = f'{self.verif_expname}'

        _title += f' {self.verif_fcsystem} {self.verif_mode} (enssize = {self.verif_enssize}) \n'

        if len(self.verif_dates[0]) == 4:
            _num = len(self.verif_dates)

            if _num > 5:
                _init_time = f'{self.verif_dates[0]} ... {self.verif_dates[-1]} [total={_num}]'
            else:
                _init_time = ', '.join(self.verif_dates)

            _years = [f'{a_}-{b_}' for a_, b_ in zip(self.verif_fromyear, self.verif_toyear)]
            if len(list(set(_years))) == 1:
                _years = [_years[0]]
                addline = False
            else:
                _years_count = dict(Counter(_years))
                _years = [f'{key} [total={value}]' for key, value in _years_count.items()]
                addline= True

            _years = ', '.join(_years)

            if addline:
                _title += f' combined dates init-time {_init_time} \n' \
                          f' ({_years})'
            else:
                _title += f' combined dates init-time {_init_time} ' \
                          f' ({_years})'

            if self.calib:
                _title += f'\n calibrated using {self.conf_calib_dates}'
                if self.calib_fromyear[0] is not None:
                    _title += f' averaged from {self.calib_fromyear[0]} to {self.calib_toyear[0]}'

        else:
            if len(self.verif_dates) == 1:
                _init_time = self.verif_dates[0]
                _title += f' init-time {_init_time}'
            elif 'to' in self.conf_verif_dates:
                _init_time = self.conf_verif_dates
                _title += f' combined dates init-time {_init_time}'

            if self.calib:
                _title += f'\n calibrated using {self.conf_calib_dates}'
                if self.calib_fromyear[0] is not None:
                    _title += f' averaged from {self.calib_fromyear[0]} to {self.calib_toyear[0]}'

        return _title
