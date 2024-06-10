""" Metric calculating sea ice distance to point/set of points """
import os
import numpy as np
import xarray as xr
import cartopy.crs as ccrs
from scipy import ndimage
from dask.distributed import Client
from .metric import BaseMetric

client=Client(threads_per_worker=1)
xr.set_options(keep_attrs=True)
os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

def _distance_haversine(lonlat1, lonlat2):
    """
    Calculates distance between set of points on globe
    https://gis.stackexchange.com/questions/372035/find-closest-point-to-shapefile-coastline-in-python
    :param lonlat1: "ice edge points" as array with [lon,lat] points
    :param lonlat2: 2nd input array with [lon,lat] points
    :return: closest distance of lonlat2 to any within lonlat1
    """
    avg_earth_radius = 6371. # Earth radius in meter

    # Get array data; convert to radians to simulate 'map(radians,...)' part
    coords_arr = np.deg2rad(lonlat1)
    a = np.deg2rad(lonlat2)

    # Get the differentiations
    lat = coords_arr[:,1] - a[:,1,None]
    lng = coords_arr[:,0] - a[:,0,None]

    # Compute the "cos(lat1) * cos(lat2) * sin(lng * 0.5) ** 2" part.
    # Add into "sin(lat * 0.5) ** 2" part.
    add0 = np.cos(a[:,1,None])*np.cos(coords_arr[:,1])* np.sin(lng * 0.5) ** 2
    d = np.sin(lat * 0.5) ** 2 +  add0

    # Get h and assign into dataframe
    h = 2 * avg_earth_radius * np.arcsin(np.sqrt(d))
    #return {'dist_to_coastline': h.min(1), 'lonlat':lonlat2, 'where':h.argmin()}
    return h.min(1)

class Metric(BaseMetric):
    """ Metric object """
    def __init__(self, name, conf):
        super().__init__(name, conf)
        self.use_metric_name = True
        self.levels = [0,None]
        self.clip = True
        self.use_dask = True

    @staticmethod
    def _remove_small_cluster(da, min_size=None):
        out_array = np.empty_like(da.values)

        for mi, member in enumerate(da['member'].values):
            for ti, ts in enumerate(da['time'].values):
                array = da.sel(time=ts, member=member).values
                labelling, label_count = ndimage.label(array)

                for l in range(1, label_count + 1):
                    if (labelling == l).sum() < min_size:
                        labelling[labelling == l] = 0

                labelling[labelling > 0] = 1
                out_array[mi, ti, :, :] = labelling

        ds_out = da.copy(deep=True, data=out_array)
        return ds_out


    def _compute_distance(self, da, min_size=None):
        """
        Compute minimum distance between self.points and ice edge
        :param da: datarray with ice concentrations
        :param min_size: minimum size of ice fields to be considered
        :return: minimum distance of point to ice edge for each member/time in da
        """
        points = self.points.copy()
        if len(self.points) == 1:
            points = self.points * len(da.time)
        elif len(self.points) != len(da.time):
            raise ValueError(f'distance can only be calculated either for 1 point'
                             f'or for points being the same length as the target time'
                             f' {len(self.points)} != {len(da.time)}')


        out_dist = np.zeros([len(da.member), len(da.time)], dtype="float32")

        for tsi, ts in enumerate(da.time.values):
            current_point = points[tsi]

            _projection = getattr(da, 'projection')
            _proj_options = {}
            for proj_param in ['central_longitude', 'central_latitude',
                               'true_scale_latitude']:
                if proj_param in da.attrs:
                    _proj_options[proj_param] = getattr(da, proj_param)

            data_crs = getattr(ccrs, _projection)(**_proj_options)
            x, y = data_crs.transform_point(current_point[0],
                                            current_point[1],
                                            src_crs=ccrs.PlateCarree())


            for m in da.member.values:
                da_tmp = da.sel(member=[m], time=[ts])
                ds_bool_tmp = xr.where(da_tmp > .15, 1, 0)

                if min_size is not None:
                    ds_bool_tmp = self._remove_small_cluster(ds_bool_tmp, min_size=min_size)

                ds_bool_tmp = ds_bool_tmp.sel(member=m, time=ts)
                if ds_bool_tmp.sel(xc=x, yc=y, method="nearest").values == 1:
                    out_dist[m, tsi] = 0
                else:

                    ds_center = ds_bool_tmp.isel(xc=slice(1, -1), yc=slice(1, -1))
                    ds_left_center = ds_bool_tmp.isel(xc=slice(None, -2), yc=slice(1, -1))
                    ds_right_center = ds_bool_tmp.isel(xc=slice(2, None), yc=slice(1, -1))
                    ds_up_center = ds_bool_tmp.isel(xc=slice(1, -1), yc=slice(None, -2))
                    ds_down_center = ds_bool_tmp.isel(xc=slice(1, -1), yc=slice(2, None))

                    # create stacked shifted grids
                    ds_merged = np.stack((ds_left_center.values,
                                          ds_right_center.values,
                                          ds_up_center.values,
                                          ds_down_center.values), axis=0)

                    # calculate minimum over shifted grids
                    ds_merged_min = ds_merged.min(axis=0)
                    ds_merged_min = xr.where(np.isnan(ds_merged_min), 0, ds_merged_min)

                    # edge grid cells are define as those with ice
                    # and with one surrounding cell with no ice
                    edge_arr = np.logical_and(ds_merged_min == 0, ds_center > 0)
                    ds_edge = ds_center.copy(deep=True, data=edge_arr)

                    tind = np.where(ds_edge.values)




                    if 'lon' in da.coords:
                        tind_lon = ds_edge.lon.values[tind].flatten()
                        tind_lat = ds_edge.lat.values[tind].flatten()
                    else:
                        tind_lon = ds_edge.longitude.values[tind].flatten()
                        tind_lat = ds_edge.latitude.values[tind].flatten()
                    edge_points = (np.column_stack((tind_lon, tind_lat))).tolist()

                    out_dist[m, tsi] = _distance_haversine(edge_points, [current_point])

        ds_out = xr.DataArray(out_dist,
                              coords={'member': da['member'],
                                      'time': da['time']},
                              dims=['member', 'time'])
        return ds_out


    def compute(self):
        """ Compute metric """
        # ice-regions with less than min_size grid cells will be removed
        # (to avoid distance being calculated to small ice areas, e.g. at the coasts)
        min_size = 255
        #min_size = 15
        min_size = None
        datalist = []
        data_names = []


        da_fc_verif = self.load_fc_data('verif')
        da_obs_verif = self.load_verif_data('verif')
        data = [da_fc_verif, da_obs_verif]

        if self.calib:
            da_fc_calib = self.load_fc_data('calib')
            da_verdata_calib = self.load_verif_data('calib')
            data.extend([da_fc_calib,da_verdata_calib])


        data, _ = self.mask_lsm(data)

        if self.calib:
            da_fc_verif, da_obs_verif, da_fc_calib, da_verdata_calib = data
            da_fc_verif = da_fc_verif.load()
            da_obs_verif = da_obs_verif.load()
            da_fc_calib = da_fc_calib.load()
            da_verdata_calib = da_verdata_calib.load()

        else:
            da_fc_verif, da_obs_verif = data
            da_fc_verif = da_fc_verif.load()
            da_obs_verif = da_obs_verif.load()
        print('done')


        list_fc_verif = []
        for idate in da_fc_verif['date'].values:
            da_fc_verif_tmp = da_fc_verif.isel(inidate=0).sel(date=idate)
            da_fc_verif_dist_tmp = self._compute_distance(da_fc_verif_tmp, min_size=min_size)
            list_fc_verif.append(da_fc_verif_dist_tmp)
        da_fc_verif_dist = xr.concat(list_fc_verif, dim='newdim')
        da_fc_verif_dist = da_fc_verif_dist.mean(dim='newdim')



        if self.add_verdata == "yes":
            list_obs = []
            for idate in da_obs_verif['date'].values:
                da_obs_verif_tmp = da_obs_verif.sel(date=idate).isel(inidate=0)
                da_obs_verif_dist_tmp = self._compute_distance(da_obs_verif_tmp, min_size=min_size)
                list_obs.append(da_obs_verif_dist_tmp)
            da_obs_verif_dist = xr.concat(list_obs, dim='newdim')
            da_obs_verif_dist = da_obs_verif_dist.mean(dim='newdim')

            datalist.append(da_obs_verif_dist.isel(member=0))
            data_names.append('obs')

        if self.calib:
            print('calibrating')
            bias_list = []
            verdata_list = []
            for idate in da_fc_calib['date'].values:
                print(idate)
                tmp_fc = da_fc_calib.sel(date=idate).isel(inidate=0)
                tmp_verdata = da_verdata_calib.sel(date=idate).isel(inidate=0)
                tmp_fc_dist = self._compute_distance(tmp_fc, min_size=min_size)
                tmp_verdata_dist = self._compute_distance(tmp_verdata, min_size=min_size)
                bias_list.append(tmp_fc_dist.mean(dim='member')-tmp_verdata_dist.mean(dim='member'))
                verdata_list.append(tmp_verdata_dist)

            bias_dist_calib = xr.concat(bias_list, dim='newdim')
            bias_dist_calib = bias_dist_calib.mean(dim='newdim')
            verdata_dist_calib = xr.concat(verdata_list, dim='date')

            datalist.append(verdata_dist_calib.mean(dim='date').dropna(dim='member').isel(member=0))
            data_names.append('obs-hc')
            da_fc_verif_dist = da_fc_verif_dist - bias_dist_calib

        datalist.append(da_fc_verif_dist)
        data_names.append('model')

        data_xr = xr.merge([data.rename(data_names[di]) for di, data in enumerate(datalist)])

        data_xr = data_xr.assign_attrs({'obs-linecolor': 'k',
                                        'obs-hc-linecolor': 'red',
                                        'model-linecolor': 'blue'})

        self.result = data_xr
