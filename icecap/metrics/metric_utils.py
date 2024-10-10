""" Utils needed specifically in metric routines """

import numpy as np
import xarray as xr
from scipy import stats
import utils

def np_arange_include_upper(start, end, step):
    """
    Function calculating range of values including upper end
    from https://stackoverflow.com/questions/50299172/range-or-numpy-arange-with-end-limit-include
    :param start: start value
    :param end: end value
    :param step: step
    :return: numpy array
    """
    end += (lambda x: step*max(0.1, x) if x < 0.5 else 0)((lambda n: n-int(n))((end - start)/step+1))
    return np.arange(start, end, step).astype(int)
def score_averaging(data, temporal_average_timescale, temporal_average_value):
    """
    Function to derive temporal average of score
    :param data: list of xarray dataArrays
    :param temporal_average_timescale: timescale over which to average, e.g. days
    :param temporal_average_value: number of units used to derive average
    :return: list of averaged xr DataArrays
    """
    utils.print_info('Temporal averaging of scores')
    data_out = []
    for _da_file in data:
        if temporal_average_timescale == 'days':
            _date_da = np.arange(_da_file.time.values[0],
                                 _da_file.time.values[-1] + 1)


            start = 0
            if _date_da[0] > 0:
                start = int(temporal_average_value)

            time_bounds = np_arange_include_upper(start, _date_da[-1] + 1, int(temporal_average_value))
            _da_file = _da_file.sel(time=slice(time_bounds[0], time_bounds[-1]))
            _da_file = _da_file.rolling(time=int(temporal_average_value)).mean().sel(time=slice(int(temporal_average_value) + _da_file.time.values[0] - 1,
                                                                                                None, int(temporal_average_value)))
        else:
            init_mon = _da_file.time.dt.month.values[0]
            _da_file = _da_file.groupby('time.month').mean()
            _da_file['month'] = (_da_file.month - init_mon) % 12 + 1
            _da_file = _da_file.sortby('month')
            _da_file =_da_file.rename({'month':'time'})
            _da_file['time'] = temporal_average_value

        data_out.append(_da_file)

    return data_out
def xr_regression_vector(y):
    """
    Derive linear regression slope and pvalue for a single vector and return as DataArray
    :param y: xr/np vector to calculate regression slope/pvalue for
    :return: slope/pvalue as xr DataArray
    """

    x = np.arange(len(y))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    data_xr = xr.DataArray([slope, intercept, p_value], dims=['slope/intercept/pvalue'])
    return data_xr


def xr_regression_3d(ds):
    """
    Apply linear regression to each grid cell and timestep
    :param ds: xr DataArray with sic data
    :return: DataArray with linear regression slope and pvalue
    """

    ds_out = xr.apply_ufunc(xr_regression_vector,
                            ds.chunk(dict(date=-1)),
                            exclude_dims=set(('date',)),
                            input_core_dims=[["date"]],
                            output_core_dims=[['slope_intercept_pvalue']],
                            vectorize=True,
                            dask="parallelized",
                            output_dtypes=[ds.dtype],
                            dask_gufunc_kwargs={'output_sizes':{"slope_intercept_pvalue": 3}}
                            )


    return ds_out

def compute_linreg(da):
    """
    Compute linear regression
    :param da: input sic dataset
    :return: linear regression slope and pvalue as dataarrays
    """

    # computation is very slow as there are many grid cells/timesteps
    # to make the computation faster we do the following
    # 1. stack array along xc and yc
    # 2. drop all cells for which standard deviation is 0 (no ice/ice for every year)
    # 3. calculate linear regression
    # 4. merge output from 3 with dummy dataset to get dropped grid cells back
    # 5. split slope/pvalue to different xr DataArrays

    # with dask.config.set(**{'array.slicing.split_large_chunks': True}):
    da_std = da.std(dim='date')
    da_tmp = xr.where(da_std == 0, np.nan, da)
    da_stack = da_tmp.stack(z=("yc", "xc"))
    da_stack_miss = da_stack.dropna(dim='z', how='all')

    da_linreg_stack = xr_regression_3d(da_stack_miss)

    da_linreg = (xr.merge([xr.zeros_like(da_stack).rename('dummy'),
                                         da_linreg_stack.rename('linreg')])).unstack()
    da_linreg = da_linreg['linreg']

    da_slope = xr.where(da_std == 0, 0, da_linreg.isel(slope_intercept_pvalue=0))
    da_intercept = xr.where(da_std == 0, 1, da_linreg.isel(slope_intercept_pvalue=1))
    da_pvalue = xr.where(da_std == 0, 1, da_linreg.isel(slope_intercept_pvalue=2))


    return da_slope, da_intercept, da_pvalue
def create_combined_mask(_ds_verif, _ds_fc):
    """
    Create a mask for cells which are set to NaN in verification or forecast data
    :param _ds_verif: verification xarray dataarray
    :param _ds_fc: forecast xarray dataarray
    :return: combined mask as xarray (boolean array)
    """

    for dim in ['inidate', 'date']:
        if dim in _ds_fc.dims:
            _ds_fc = _ds_fc.isel({dim: 0})
        if dim in _ds_verif.dims:
            _ds_verif = _ds_verif.isel({dim: 0})

    _ds_verif_tmp = xr.where(np.isnan(_ds_verif), 1, 0)

    if 'member' in _ds_verif_tmp.dims:
        _ds_verif_tmp = _ds_verif_tmp.sum(dim='member')
    _ds_verif_mask = xr.where(_ds_verif_tmp.sum(dim='time') == 0, True, False)

    _ds_fc_tmp = xr.where(np.isnan(_ds_fc), 1, 0)
    if 'member' in _ds_fc_tmp.dims:
        _ds_fc_tmp = _ds_fc_tmp.sum(dim='member')
    _ds_fc_mask = xr.where(_ds_fc_tmp.sum(dim='time') == 0, True, False)

    combined_mask = np.logical_and(_ds_verif_mask == 1, _ds_fc_mask == 1)
    combined_mask = xr.where(combined_mask, 1, float('nan'))

    return combined_mask

def area_cut(ds, lon1, lon2, lat1, lat2):
    """
    Set values outside lon/lat regions specified here to NaN values
    :param ds: input xarray DataArray
    :param lon1: east longitude
    :param lon2: west longitude
    :param lat1: south latitude
    :param lat2: north latitude
    :return: maksed dataArray
    """

    if 'longitude' in ds.coords:
        lon_name = 'longitude'
        lat_name = 'latitude'
    else:
        lon_name = 'lon'
        lat_name = 'lat'

    if lon1 > lon2:
        data_masked1 = ds.where((ds[lat_name] > lat1) & (ds[lat_name] <= lat2)
                                & (ds[lon_name] > lon1) & (ds[lon_name] < 180))
        data_masked2 = ds.where((ds[lat_name] > lat1) & (ds[lat_name] <= lat2)
                                & (ds[lon_name] >= -180) & (ds[lon_name] < lon2))

        combined_mask = np.logical_or(~np.isnan(data_masked1), ~np.isnan(data_masked2))
        _data = xr.where(combined_mask, ds, float('nan'))
    else:
        _data = ds.where((ds[lat_name] >= lat1) & (ds[lat_name] <= lat2)
                         & (ds[lon_name] >= lon1) & (ds[lon_name] <= lon2))


    return _data

def get_nsidc_region(ds, name):
    """
    Select NSIDC region with 'name' from xarray file 'ds'
    :param ds: xarray DataArray containing NSIDC regions
    :param name: name of region
    :return: integer given the region number in the netcdf file
    """
    region_full_names = np.asarray(ds.attrs['flag_meanings'])
    region_short_names = np.asarray(ds.attrs['flag_meanings_short'])
    region_number = np.asarray(ds.attrs['flag_values'])
    if name in region_full_names:
        return int(region_number[region_full_names==name])
    elif name.upper() in region_short_names:
        return int(region_number[region_short_names==name.upper()])
    else:
        raise NotImplementedError

def detect_edge(ds, threshold=0.15):
    """
    Detect ice edge in xarray DataArray
    :param ds: xr DataArray containing sea ice data
    :param threshold: sea ice threshold for which sic is set to 1 (set to None is already calculated before)
    :return: xr DataArray with position of sea ice edge
    """
    if threshold is None:
        ds_bool = ds
    else:
        ds_bool = xr.where(ds > threshold, 1, 0)


    for dim in ('inidate', 'date', 'member','time'):
        if dim not in ds_bool.dims:
            ds_bool = ds_bool.expand_dims(dim)



    ds_center = ds_bool.isel(xc=slice(1, -1), yc=slice(1, -1))
    ds_left_center = ds_bool.isel(xc=slice(None, -2), yc=slice(1, -1))
    ds_right_center = ds_bool.isel(xc=slice(2, None), yc=slice(1, -1))
    ds_up_center = ds_bool.isel(xc=slice(1, -1), yc=slice(None, -2))
    ds_down_center = ds_bool.isel(xc=slice(1, -1), yc=slice(2, None))

    # create stacked shifted grids
    ds_merged = np.stack((ds_left_center.values,
                          ds_right_center.values,
                          ds_up_center.values,
                          ds_down_center.values), axis=0)

    # calculate minimum over shifted grids
    ds_merged_min = ds_merged.min(axis=0)

    # edge grid cells are define as those with ice
    # and with one surrounding cell with no ice

    # set nan values (land) to zero to detect sea ice edge around land
    ds_merged_min = xr.where(np.isnan(ds_merged_min),0,ds_merged_min)

    edge_arr = np.logical_and(ds_merged_min == 0, ds_center > 0)
    ds_bool_np = np.zeros(ds_bool.shape)
    ds_bool_np[:,:,:,:, 1:-1, 1:-1] = edge_arr
    ds_edge = ds_bool.copy(deep=True, data=ds_bool_np)

    return ds_edge

def detect_extended_edge(ds_edge, max_extent=200):
    """
    Detect extended sea ice edge (all grid cells with distance <= max_extent
    :param ds_edge: sea ice edge xr DataArray object
    :param max_extent: maximum extent in km
    :return: xr DataArray with position of extended sea ice edge
    """

    utils.print_info('Extended Edge detection algorithm')

    # use grid spacing to derive number of cells using max_extent
    dx = np.diff(ds_edge.xc)[0]/1000
    cells_add = np.round((max_extent / dx)).astype(int)


    ds_new = ds_edge.values.copy()

    for xi in np.arange(-cells_add, cells_add + 1):
        for yi in np.arange(-cells_add, cells_add + 1):

            ds_tmp = np.zeros(ds_edge.shape)
            # derive distance and check it's not larger than cells_add
            if np.sqrt(np.abs(xi) ** 2 + np.abs(yi) ** 2) <= cells_add:
                if xi > 0 and yi > 0:
                    ds_tmp[:,:,:,:, :-yi, :-xi] = ds_edge.isel(xc=slice(xi, None), yc=slice(yi, None)).values
                elif xi > 0 and yi < 0:
                    ds_tmp[:,:,:,:, np.abs(yi):, :-xi] = ds_edge.isel(xc=slice(xi, None), yc=slice(None, yi)).values
                elif xi < 0 and yi < 0:
                    ds_tmp[:,:,:,:, np.abs(yi):, np.abs(xi):] = ds_edge.isel(xc=slice(None, xi), yc=slice(None, yi)).values
                elif xi < 0 and yi > 0:
                    ds_tmp[:,:,:,:, :-yi, np.abs(xi):] = ds_edge.isel(xc=slice(None, xi), yc=slice(yi, None)).values

                elif xi == 0 and yi > 0:
                    ds_tmp[:,:,:,:, :-yi, :] = ds_edge.isel(yc=slice(yi, None)).values
                elif xi == 0 and yi < 0:
                    ds_tmp[:,:,:,:, np.abs(yi):, :] = ds_edge.isel(yc=slice(None, yi)).values
                elif yi == 0 and xi > 0:
                    ds_tmp[:,:,:,:, :, :-xi] = ds_edge.isel(xc=slice(xi, None)).values
                elif yi == 0 and xi < 0:
                    ds_tmp[:,:,:,:, :, np.abs(xi):] = ds_edge.isel(xc=slice(None, xi)).values

                ds_new = ds_new + ds_tmp

    ds_extended_edge = ds_edge.copy(deep=True, data=ds_new)
    ds_extended_edge = xr.where(ds_extended_edge > 0, 1, 0)

    return ds_extended_edge
