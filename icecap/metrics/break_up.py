""" Metric calculating ensemble mean """
import os
import numpy as np
import xarray as xr
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
import utils
from .metric import BaseMetric



xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.plottext = ''
        self.legendtext = 'percentage of members'
        self.ylabel = 'sic'


        self.levels = [-110,-100,-70,-60,-50,-40,40,50,60,70,100+1e-05,110]
        self.ticks = [-105,-85,-65,-55,-45,0,45,55,65,85,105]
        self.ticklabels = ['open water','70-100','60-70','50-60','40-50','other',
                           '40-50','50-60','60-70','70-100','ice']
        self.clip = True

        cmap = plt.get_cmap('coolwarm_r', len(self.levels) - 1)
        newcolors = cmap(np.linspace(0, 1, len(self.levels) - 1))
        newcolors[-1, :] = np.array([255, 255, 255, 1]) / np.array([256, 256, 256, 1])
        newcolors[0, :] = np.array([25, 25, 112, 1]) / np.array([256, 256, 256, 1])
        self.default_cmap = ListedColormap(newcolors)
        self.norm = matplotlib.colors.BoundaryNorm(self.levels, len(self.levels))
        self.use_dask = True


        if len(self.verif_dates[0]) == 4:
            self.startday = utils.string_to_datetime(f'2000{self.verif_dates[0]}').timetuple().tm_yday
        else:
            self.startday = utils.string_to_datetime(self.verif_dates[0]).timetuple().tm_yday

        if not self.calib:
            raise ValueError('Break-up only works with calibration data')
        if len(self.verif_dates) !=1 or self.verif_fromyear != self.verif_toyear:
            raise ValueError('only one verification date (verif_dates) can be specified'
                             'to plot break-up dates')


    def break_up(self, ds):
        """
        Calculate break-up dates (last date for which sea ice
        drops below threshold [pre-computed in ds]).
        Date undefined if cell is always water (set to 0), cell is always ice (set to nan or 1000),
        sic in cell is > threshold for at leats one day in the last week
        :param ds: dataarray ith sea ice forecast data
        :return: day of sea ice break up (sic<threshold)
        """
        # mask based on threshold (1 water, 0 ice)
        ds_water = xr.where(ds == 0, 1, 0)
        ds_water = xr.where(np.isnan(ds), np.nan, ds_water)

        # mask of all members having always water
        mask_water_member = xr.where(ds.max(dim='time') ==0, np.nan, 1)
        # mask of all members having always ice
        mask_ice_member = xr.where(ds.min(dim='time') == 1, np.nan, 1)
        # mask per member last 7 days (<1 if at least one ice day)
        mask_end_member = ds_water.isel(time=np.arange(-7, 0)).mean(dim='time')
        mask_end_member = xr.where(mask_end_member<1,np.nan,1)

        #mask ds_water usign all masks above
        ds_mask_all = mask_water_member * mask_ice_member * mask_end_member
        ds_water_masked = xr.where(ds_mask_all==1, ds_water, 0)

        # observations can have nan values. We put them back in here and assume that they are ice
        ds_water_masked = xr.where(~np.isnan(ds), ds_water_masked, np.nan)
        ds_water_masked = xr.where(xr.where(np.isnan(ds), 1, 0).mean(dim='time') == 1, 0, ds_water_masked)

        # change coordinate to increasing array and reverse xarray along time dim
        # this option preferred to reindex (https://github.com/pydata/xarray/discussions/6695)
        ds_water_masked_reverse = ds_water_masked.isel(time=slice(None, None, -1))


        # this finds the first instance where the field is 0 (meaning > threshold)
        # we have to subtract 1 to get the date of ice free conditions
        ds_fc_day = ds_water_masked_reverse.argmin(dim='time') - 1
        ds_fc_day = len(ds_water_masked_reverse.time.values) - ds_fc_day - 1

        # set ice mask entries to -300 and water entries to -200
        ds_fc_day = xr.where((mask_ice_member * mask_end_member)==1,ds_fc_day,180)
        ds_fc_day = xr.where(mask_water_member == 1, ds_fc_day, 0)

        # needed as xr.where does not preserve attributes
        ds_fc_day = ds_fc_day.assign_attrs(ds.attrs)


        return ds_fc_day, mask_water_member, (mask_ice_member * mask_end_member)

    def compute(self):
        """ Compute metric """

        average_dims = ['inidate']
        persistence = False
        sic_threshold = 0.15


        processed_data_dict = self.process_data_for_metric(average_dims, persistence, sic_threshold)

        data_plot = []
        data_plot.append(processed_data_dict['lsm_full'])

        lsm_full = processed_data_dict['lsm_full']

        da_fc_verif = processed_data_dict['da_fc_verif'].mean(dim='date')
        da_fc_verif_metric, mask_water, mask_ice = self.break_up(da_fc_verif)
        
        if self.add_verdata == 'yes':
            da_verdata_verif = processed_data_dict['da_verdata_verif'].mean(dim='date')
            da_verdata_verif_metric, mask_water_vardata, mask_ice_vardata = self.break_up(da_verdata_verif)

        if self.calib:
            if self.calib_exists == 'yes':
                ds_calib = self.get_save_calibration_file()

                da_fc_calib_metric_upper = ds_calib['da_fc_calib_metric_upper']
                da_fc_calib_metric_lower = ds_calib['da_fc_calib_metric_lower']
                da_verdata_calib_metric_upper = ds_calib['da_verdata_calib_metric_upper']
                da_verdata_calib_metric_lower = ds_calib['da_verdata_calib_metric_lower']
                da_fc_calib_early_bss = ds_calib['da_fc_calib_early_bss']
                da_fc_calib_late_bss = ds_calib['da_fc_calib_late_bss']

            else:
                da_fc_calib = processed_data_dict['da_fc_calib']
                da_verdata_calib = processed_data_dict['da_verdata_calib']

                da_fc_calib_metric, _, _ = self.break_up(da_fc_calib)
                da_fc_calib_metric = da_fc_calib_metric.chunk(dict(date=-1, member=-1))
                da_fc_calib_metric_upper = da_fc_calib_metric.quantile(2 / 3, dim=('member', 'date'))
                da_fc_calib_metric_lower = da_fc_calib_metric.quantile(1 / 3, dim=('member', 'date'))

                da_fc_calib_metric_upper = da_fc_calib_metric_upper.drop_vars('quantile')
                da_fc_calib_metric_lower = da_fc_calib_metric_lower.drop_vars('quantile')

                # verdata calib
                da_verdata_calib_metric, _, _ = self.break_up(da_verdata_calib)
                da_verdata_calib_metric = da_verdata_calib_metric.chunk(dict(date=-1))
                da_verdata_calib_metric_upper = da_verdata_calib_metric.quantile(2 / 3, dim=('date'))
                da_verdata_calib_metric_lower = da_verdata_calib_metric.quantile(1 / 3, dim=('date'))
                da_verdata_calib_metric_lower = da_verdata_calib_metric_lower.drop_vars('quantile')
                da_verdata_calib_metric_upper = da_verdata_calib_metric_upper.drop_vars('quantile')


                early_fc_calib = xr.where(da_fc_calib_metric < da_fc_calib_metric_lower, 1, 0).mean(dim='member')
                late_fc_calib = xr.where(da_fc_calib_metric > da_fc_calib_metric_upper, 1, 0).mean(dim='member')

                early_verdata_calib = xr.where(da_verdata_calib_metric < da_verdata_calib_metric_lower, 1, 0)
                late_verdata_calib = xr.where(da_verdata_calib_metric > da_verdata_calib_metric_upper, 1, 0)

                bs_fc_early = ((early_fc_calib - early_verdata_calib) ** 2).mean(dim='date')
                bs_fc_late = ((late_fc_calib - late_verdata_calib) ** 2).mean(dim='date')
                bs_clim_early = ((1 / 3 - early_verdata_calib) ** 2).mean(dim='date')
                bs_clim_late = ((1 / 3 - late_verdata_calib) ** 2).mean(dim='date')
                da_fc_calib_early_bss = 1 - bs_fc_early / bs_clim_early
                da_fc_calib_late_bss = 1 - bs_fc_late / bs_clim_late

                # save calibration file
                data_calib = []
                data_calib.append(da_fc_calib_metric_upper.rename('da_fc_calib_metric_upper'))
                data_calib.append(da_fc_calib_metric_lower.rename('da_fc_calib_metric_lower'))
                data_calib.append(
                    da_verdata_calib_metric_upper.rename('da_verdata_calib_metric_upper'))
                data_calib.append(
                    da_verdata_calib_metric_lower.rename('da_verdata_calib_metric_lower'))
                data_calib.append(da_fc_calib_early_bss.rename('da_fc_calib_early_bss'))
                data_calib.append(da_fc_calib_late_bss.rename('da_fc_calib_late_bss'))
                data_calib = utils.set_xarray_attribute(data_calib, processed_data_dict['da_coords'],
                                                        params=['projection', 'central_longitude', 'central_latitude',
                                                                'true_scale_latitude'])
                data_calib_xr = xr.merge(data_calib)
                self.get_save_calibration_file(ds=data_calib_xr)
                # end save calib file


            # derive probabilities using calib files
            early = xr.where(da_fc_verif_metric < da_fc_calib_metric_lower, 1, 0).mean(dim='member') * 100
            late = xr.where(da_fc_verif_metric > da_fc_calib_metric_upper, 1, 0).mean(dim='member') * 100

            mask_water_all = xr.where(mask_water==1,0,1)
            mask_water_all = xr.where(mask_water_all.min(dim='member')==1,True, False)
            mask_ice_all = xr.where(mask_ice == 1, 0, 1)
            mask_ice_all = xr.where(mask_ice_all.min(dim='member') == 1, True, False)

            combine = xr.where(late > early, late, early * -1)
            combine = xr.where(mask_water_all, -101, combine)
            combine = xr.where(mask_ice_all, 101, combine)
            combine = xr.where(np.isnan(lsm_full), np.nan, combine)
            combine = combine.assign_attrs(da_fc_verif.attrs)


             # derive probabilities using calib files for verdata
            if self.add_verdata == 'yes':
                early_verdata = xr.where(da_verdata_verif_metric < da_verdata_calib_metric_lower, 1, 0).mean(dim='member') * 100
                late_verdata = xr.where(da_verdata_verif_metric > da_verdata_calib_metric_upper, 1, 0).mean(dim='member') * 100


                mask_water_verdata_all = xr.where(mask_water_vardata == 1, 0, 1)
                mask_water_verdata_all = xr.where(mask_water_verdata_all.min(dim='member') == 1, True, False)
                mask_ice_verdata_all = xr.where(mask_ice_vardata == 1, 0, 1)
                mask_ice_verdata_all = xr.where(mask_ice_verdata_all.min(dim='member') == 1, True, False)

                combine_verdata = xr.where(late_verdata > early_verdata, late_verdata, early_verdata * -1)
                combine_verdata = xr.where(mask_water_verdata_all, -101, combine_verdata)
                combine_verdata = xr.where(mask_ice_verdata_all, 101, combine_verdata)
                combine_verdata = xr.where(np.isnan(lsm_full), np.nan, combine_verdata)
                combine_verdata = combine_verdata.assign_attrs(da_fc_verif.attrs).squeeze()
                data_plot.append(combine_verdata.expand_dims(dim={"time": 1}).rename(f'{self.verif_name}'))
                data_plot.append(da_verdata_verif_metric.rename('da_verdata_verif_dates_noplot'))

            fc_name = self.verif_expname[0]
            if self.verif_modelname[0] is not None:
                fc_name = f'{self.verif_modelname[0]} {fc_name}'

            data_plot.append(combine.expand_dims(dim={"time": 1}).rename(f'{fc_name}'))
            data_plot.append(da_fc_calib_metric_upper.rename('upper_q_calib_noplot'))
            data_plot.append(da_fc_calib_metric_lower.rename('lower_q_calib_noplot'))

            # these are masked BSS fileds (using fc_verif mask for plotting)
            da_fc_calib_early_bss = xr.where(mask_water_all, -101, da_fc_calib_early_bss)
            da_fc_calib_early_bss = xr.where(mask_ice_all, 101, da_fc_calib_early_bss)
            da_fc_calib_early_bss = xr.where(np.isnan(lsm_full), np.nan, da_fc_calib_early_bss)

            da_fc_calib_late_bss = xr.where(mask_water_all, -101, da_fc_calib_late_bss)
            da_fc_calib_late_bss = xr.where(mask_ice_all, 101, da_fc_calib_late_bss)
            da_fc_calib_late_bss = xr.where(np.isnan(lsm_full), np.nan, da_fc_calib_late_bss)

            data_plot.append(da_fc_calib_early_bss.rename('bss_fc_early_noplot'))
            data_plot.append(da_fc_calib_late_bss.rename('bss_fc_late_noplot'))


        data_plot = utils.set_xarray_attribute(data_plot, processed_data_dict['da_coords'],
                                               params=['projection', 'central_longitude', 'central_latitude',
                                                       'true_scale_latitude'])
        data_xr = xr.merge(data_plot)

        ## keywords for plotting
        cmd_all = []

        cmd_all.append(dict(attr_type='ax.text',
                            x=1.3, y=.75, s='Prob (within upper tercile)',
                  transform='True', fontsize=12,
                  verticalalignment='center', rotation=90))
        cmd_all.append(dict(attr_type='ax.text',
                            x=1.3, y=.25, s='Prob (within lower tercile)',
                            transform='True', fontsize=12,
                            verticalalignment='center', rotation=90))
        cmd_all.append(dict(attr_type='cb.set_label', label=self.legendtext))

        for i, cmd in enumerate(cmd_all):
            cmd_list = [f"{key}=\"{value}\"" if isinstance(value, str) else f"{key}={value}" for key, value in
                          cmd.items()]

            data_xr = data_xr.assign_attrs({f'{fc_name}-{i}': cmd_list})

        self.result = data_xr
