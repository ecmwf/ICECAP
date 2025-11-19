""" Script to generate NSIDC regions on OSI grid
you need to provide the NSIDC region file as input
NSIDC netcdf region files can be downloaded here; https://urs.earthdata.nasa.gov/ """

import os
import sys
import xarray as xr
import numpy as np
from scipy.interpolate import NearestNDInterpolator
import cartopy.crs as ccrs
from matplotlib.colors import BoundaryNorm
import matplotlib.pyplot as plt
import  matplotlib.colors as mcolors
import matplotlib


def _init_proj(ds):
    _projection = getattr(ds, 'projection')
    _proj_options = {}
    for proj_param in ['central_longitude', 'central_latitude',
                       'true_scale_latitude']:
        if proj_param in ds.attrs:
            _proj_options[proj_param] = getattr(ds, proj_param)

    return _projection, _proj_options

if len(sys.argv) != 3:
    raise ValueError('Exactly two arguments needed (grid and nsidc nc file)')

grid = sys.argv[1]
ifile_nsidc = sys.argv[2]
ofile = f'nsidc_{grid}.nc'

if os.path.exists(ofile):
    raise FileExistsError(f'Output file {ofile} already exists')

if not os.path.exists(ifile_nsidc):
    raise FileNotFoundError(f'NSIDC file {ifile_nsidc} not found')

ds_nsidc = xr.open_dataset(ifile_nsidc)

# Get OSI data from THREDDS server
if grid == 'osi-cdr':
    if os.path.basename(ifile_nsidc) != 'NSIDC-0780_SeaIceRegions_EASE2-N25km_v1.0.nc':
        print(
            f'WARNING: If possible use NSIDC-0780_SeaIceRegions_EASE2-N25km_v1.0.nc when generating {grid} region file')
    ifile_osi = 'https://thredds.met.no/thredds/dodsC/osisaf/met.no/reprocessed/ice/conc_cra_files/2022/10/ice_conc_nh_ease2-250_icdr-v3p0_202210191200.nc'
elif grid in ['osi-401-b', 'osi-408']:
    if os.path.basename(ifile_nsidc) != 'NSIDC-0780_SeaIceRegions_PS-N12.5km_v1.0.nc':
        print(
            f'WARNING: If possible use NSIDC-0780_SeaIceRegions_PS-N12.5km_v1.0.nc when generating {grid} region file')
    ifile_osi = 'https://thredds.met.no/thredds/dodsC/osisaf/met.no/ice/conc/2020/07/ice_conc_nh_polstere-100_multi_202007261200.nc'
else:
    raise NotImplementedError('Only osi-cdr or osi-401-b / osi-408 grids implemented')

ds_osi = xr.open_dataset(ifile_osi)['ice_conc']
ds_osi['xc'] = ds_osi['xc'] * 1000
ds_osi['yc'] = ds_osi['yc'] * 1000
mapping_grid = getattr(ds_osi, 'grid_mapping')
ds_osi_grid = xr.open_dataset(ifile_osi)[mapping_grid]


# Check that projection in NSIDC and OSI file are the same
projection_kwards = ['latitude_of_projection_origin', 'longitude_of_projection_origin', 'latitude_of_projection_origin',
                     'straight_vertical_longitude_from_pole', 'standard_parallel']

if getattr(ds_osi_grid, 'grid_mapping_name') != getattr(ds_nsidc.crs, 'grid_mapping_name'):
    raise ValueError(
        f"Grid projection is not the same in OSI ({getattr(ds_osi_grid, 'grid_mapping_name')}) and NSIDC file ({getattr(ds_nsidc.crs, 'grid_mapping_name')})")

for proj_option in projection_kwards:
    if proj_option in ds_osi_grid.attrs:
        if proj_option not in ds_nsidc.crs.attrs:
            raise ValueError(f'Projection option {proj_option} not present in NSIDC file')
        if getattr(ds_osi_grid, proj_option) != getattr(ds_nsidc.crs, proj_option):
            raise ValueError(
                f"Grid options not the same in OSI {getattr(ds_osi_grid, proj_option)} and NSIDC file {getattr(ds_nsidc.crs, proj_option)}")

# Generating region file on OSI grid
ds_osi_x_spacing = np.unique(np.diff(ds_osi.xc))
ds_osi_y_spacing = np.unique(np.diff(ds_osi.yc))
ds_nsidc_x_spacing = np.unique(np.diff(ds_nsidc.x))
ds_nsidc_y_spacing = np.unique(np.diff(ds_nsidc.y))

if len(ds_osi_x_spacing) == 1 and len(ds_osi_y_spacing) == 1 and len(ds_nsidc_x_spacing) == 1 and len(
        ds_nsidc_y_spacing) == 1:
    print('Equally space grids')

if ds_osi_x_spacing == ds_nsidc_x_spacing and ds_osi_y_spacing == ds_nsidc_y_spacing:
    print('Same grid spacing --> no interpolation needed')

    ds_regions_osi = ds_nsidc['sea_ice_region'].isel(x=ds_nsidc['sea_ice_region'].x.isin(ds_osi.xc),
                                                     y=ds_nsidc['sea_ice_region'].y.isin(ds_osi.yc))

else:
    print('Grid spacig is different --> interpolation needed')

    all_coords_regionfile = [(a, b) for a in ds_nsidc.y.values for b in ds_nsidc.x.values]
    interp = NearestNDInterpolator(all_coords_regionfile, ds_nsidc['sea_ice_region'].values.flatten())

    # now interpolate on osi grid
    X, Y = np.meshgrid(ds_osi.yc.values, ds_osi.xc.values)
    out = interp(X, Y)
    out = np.transpose(out)
    ds_regions_osi = ds_osi.isel(time=0).copy(data=out)

# ocean should be nan
ds_regions_osi = xr.where(ds_regions_osi == 0, np.nan, ds_regions_osi)

ds_regions_osi.attrs['flag_values'] = ds_nsidc['sea_ice_region'].attrs['flag_values'][1:]
ds_regions_osi.attrs['flag_meanings'] = np.asarray(ds_nsidc['sea_ice_region'].attrs['flag_meanings'].split(' '))[1:]
ds_regions_osi.attrs['flag_meanings_short'] = np.asarray(
    ['CARC', 'BEAS', 'CHUS', 'ESS', 'LS', 'KS', 'BARS', 'EGS', 'BBLS', 'GOSL', 'HB', 'CAA',
     'BERS', 'SOO', 'SOJ', 'BYS', 'BALS', 'GOA'])

if 'x' in ds_regions_osi.dims:
    ds_regions_osi = ds_regions_osi.rename({'x': 'xc', 'y': 'yc'})


# set projection attributes for ICECAP
if getattr(ds_osi_grid, 'grid_mapping_name') == 'lambert_azimuthal_equal_area':
    ds_regions_osi.attrs['projection'] = 'LambertAzimuthalEqualArea'
    ds_regions_osi.attrs['central_latitude'] = getattr(ds_osi_grid, 'latitude_of_projection_origin')
    ds_regions_osi.attrs['central_longitude'] = getattr(ds_osi_grid, 'longitude_of_projection_origin')

if getattr(ds_osi_grid, 'grid_mapping_name') == 'polar_stereographic':
    ds_regions_osi.attrs['projection'] = 'Stereographic'
    ds_regions_osi.attrs['central_latitude'] = getattr(ds_osi_grid, 'latitude_of_projection_origin')
    ds_regions_osi.attrs['central_longitude'] = getattr(ds_osi_grid, 'straight_vertical_longitude_from_pole')
    ds_regions_osi.attrs['true_scale_latitude'] = getattr(ds_osi_grid, 'standard_parallel')

print(f'Generating output {ofile}')
ds_regions_osi.to_netcdf(ofile)


# PLOT regions on new grid
_proj,_proj_options = _init_proj(ds_regions_osi)
proj = getattr(ccrs, _proj)(**_proj_options)
ax = plt.axes(projection=proj)

cmap = matplotlib.colormaps.get_cmap('nipy_spectral')
icolor = np.linspace(0,1,19)
icolor = icolor[::2].tolist()+icolor[1::2].tolist()
colors = cmap(icolor)

levels = np.arange(0.5,19.5)
norm = BoundaryNorm(levels, ncolors=len(colors), clip=True)
plot = ax.pcolormesh(ds_regions_osi.xc, ds_regions_osi.yc, ds_regions_osi, cmap=mcolors.ListedColormap(colors), norm=norm)

ax.coastlines()
cb = plt.colorbar(plot)
cb.set_ticks(np.arange(1,19))
cb.set_ticklabels(ds_regions_osi.attrs['flag_meanings_short'])
cb.ax.minorticks_off()

ofile_plot = ofile.replace('.nc','.png')
print(f'Plotting output to {ofile_plot}')
plt.savefig(ofile_plot, bbox_inches='tight')
