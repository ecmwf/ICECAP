"""Module containing verification classes"""

import datetime as dt
import xarray as xr
from dateutil.relativedelta import relativedelta
import numpy as np

import dataobjects
import utils

xr.set_options(keep_attrs=True)

params_verdata = {
    'sic' : {
        'osi-450-a' : 'ice_conc',
        'osi-401-b' : 'ice_conc',
        'osi-401-b-grid' : 'ice_conc',
        'osi-cdr' : 'ice_conc',
        'osi-cdr-grid' : 'ice_conc',
    }
}

def VerifData(conf):
    """
    This function works like a factory and creates the
    appropriate class depending on the verification datasets
    :param conf: ICECAP configuration object
    :return: Verification object
    """
    selector = {
        'osi-450-a': _OSIThreddsRetrieval(conf),
        'osi-401-b': _OSIThreddsRetrieval(conf),
        'osi-cdr': _OSIThreddsRetrieval(conf), # was osi-450-a_osi-430-a_mixed'
        'osi-401-b-grid': _OSIThreddsRetrieval(conf),
        'osi-cdr-grid': _OSIThreddsRetrieval(conf),
    }

    return selector[conf.verdata]



class VerifyingData(dataobjects.DataObject):
    """ Verification parent class object """
    def __init__(self, conf):
        super().__init__(conf)
        # there is a 16 day delay for osi data, so retrieval of dates after 16 days before today are removed from list
        dt_loopdates = np.asarray([utils.string_to_datetime(_date) for _date in self.salldates])
        last_date = utils.datetime_to_string(dt.datetime.now() -  relativedelta(days=int(16)))
        last_date = utils.string_to_datetime(last_date)
        mask = dt_loopdates <= last_date
        dt_loopdates = dt_loopdates[mask].tolist()
        self.loopdates = [utils.datetime_to_string(_date) for _date in dt_loopdates]








class _OSIThreddsRetrieval(VerifyingData):
    def __init__(self, conf):
        super().__init__(conf)

        self.root_server = "https://thredds.met.no/thredds/dodsC/osisaf/met.no/"
        if self.verif_name == 'osi-450-a':
            self.server = [self.root_server+"reprocessed/ice/conc_450a_files/"]
            self.filebase = ["ice_conc_nh_ease2-250_cdr-v3p0_"]
            self.fileext = ["1200.nc"]

        if self.verif_name == 'osi-401-b':
            self.server = [self.root_server+"ice/conc/"]
            self.filebase = ["ice_conc_nh_polstere-100_multi_"]
            self.fileext = ["1200.nc"]

        if self.verif_name == 'osi-cdr':
            self.server = self.root_server+"reprocessed/ice/conc_450a_files/"
            self.filebase = "ice_conc_nh_ease2-250_cdr-v3p0_"
            self.fileext = "1200.nc"

            self.server = [self.server, self.root_server+"reprocessed/ice/conc_cra_files/"]
            self.filebase = [self.filebase, "ice_conc_nh_ease2-250_icdr-v3p0_"]
            self.fileext = [self.fileext, "1200.nc"]

        if self.verif_name == 'osi-401-b-grid':
            self.loopdates = ['20171130']
            self.server = [self.root_server + "ice/conc/"]
            self.filebase = ["ice_conc_nh_polstere-100_multi_"]
            self.fileext = ["1200.nc"]

        if self.verif_name == 'osi-cdr-grid':
            self.loopdates = ['20171130']
            self.server = [self.root_server + "reprocessed/ice/conc_450a_files/"]
            self.filebase = ["ice_conc_nh_ease2-250_cdr-v3p0_"]
            self.fileext = ["1200.nc"]



    def make_filelist(self):
        """Generate a list of files which are expected to be staged"""
        if 'grid' in self.verif_name:
            files = [f'{self.obscachedir}/{self.verif_name}.nc']
        else:
            filename = self._filenaming_convention('verif')
            files = [self.obscachedir +'/' + filename.format(date, self.params)
                     for date in self.loopdates]
        return files

    def process(self, verbose):
        """
        Retrieve and process verification data file
        :param verbose: more debugging output
        """
        filename = self._filenaming_convention('verif')
        utils.make_dir(self.obscachedir)

        for _date in self.loopdates:
            _ofile = f'{self.obscachedir}/{filename.format(_date, self.params)}'

            if 'grid' in self.verif_name:
                _ofile = f'{self.obscachedir}/{self.verif_name}.nc'

            if _ofile in self.files_to_retrieve:
                try:
                    file = f'{self.server[0]}{_date[:4]}/{_date[4:6]}/{self.filebase[0]}{_date}{self.fileext[0]}'
                    if verbose:
                        print(f'Processing file {file}')
                    da_in = xr.open_dataset(file)[params_verdata[self.params][self.verif_name]]

                except:
                    if len(self.server) > 1:
                        try:
                            file = f'{self.server[1]}{_date[:4]}/{_date[4:6]}/{self.filebase[1]}{_date}{self.fileext[1]}'
                            if verbose:
                                print(f'Processing file {file}')
                            da_in = xr.open_dataset(file)[params_verdata[self.params][self.verif_name]]
                        except:
                            raise BaseException(f'Data {file} not found')
                    else:
                        raise BaseException(f'Data {file} not found')


                da_in = da_in.rename(self.params)

                da_in = da_in/100
                da_in = da_in.rename({'lon': 'longitude', 'lat': 'latitude'})
                da_in = da_in.transpose( 'time', 'yc', 'xc')
                da_in['xc'] = da_in['xc'] * 1000
                da_in['yc'] = da_in['yc'] * 1000


                mapping_grid = getattr(da_in,'grid_mapping')
                da_in_grid = xr.open_dataset(file)[mapping_grid]
                if getattr(da_in_grid, 'grid_mapping_name') == 'lambert_azimuthal_equal_area':
                    da_in.attrs['projection'] = 'LambertAzimuthalEqualArea'
                    da_in.attrs['central_latitude'] = getattr(da_in_grid, 'latitude_of_projection_origin')
                    da_in.attrs['central_longitude'] = getattr(da_in_grid, 'longitude_of_projection_origin')

                if getattr(da_in_grid, 'grid_mapping_name') == 'polar_stereographic':
                    da_in.attrs['projection'] = 'Stereographic'
                    da_in.attrs['central_latitude'] = getattr(da_in_grid, 'latitude_of_projection_origin')
                    da_in.attrs['central_longitude'] = getattr(da_in_grid, 'straight_vertical_longitude_from_pole')
                    da_in.attrs['true_scale_latitude'] = getattr(da_in_grid, 'standard_parallel')


                da_in.to_netcdf(_ofile)
