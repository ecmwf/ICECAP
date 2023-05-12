"""Module containing verification classes"""

import xarray as xr

import dataobjects
import utils

xr.set_options(keep_attrs=True)

params_verdata = {
    'sic' : {
        'osi-450-a' : 'ice_conc',
        'osi-401-b' : 'ice_conc',
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
        'osi-401-b': _OSIThreddsRetrieval(conf)
    }

    return selector[conf.verdata]



class VerifyingData(dataobjects.DataObject):
    """ Verification parent class object """
    def __init__(self, conf):
        super().__init__(conf)
        self.name = conf.verdata




    def make_filelist(self):
        """Generate a list of files which are expected to be staged"""
        filename = self._filenaming_convention('verif')
        files = [self.obscachedir+'/'+filename.format(date, self.params)
                 for date in self.salldates]
        return files




class _OSIThreddsRetrieval(VerifyingData):
    def __init__(self, conf):
        super().__init__(conf)
        self.root_server = "https://thredds.met.no/thredds/dodsC/osisaf/met.no/"
        if self.name == 'osi-450-a':
            self.root_server += "reprocessed/ice/conc_450a_files/"
            self.filebase = "ice_conc_nh_ease2-250_cdr-v3p0_"
            self.fileext = "1200.nc"

        if self.name == 'osi-401-b':
            self.root_server += "ice/conc/"
            self.filebase = "ice_conc_nh_polstere-100_multi_"
            self.fileext = "1200.nc"


    def process(self, verbose):
        """
        Retrieve and process verification data file
        :param verbose: more debugging output
        """
        filename = self._filenaming_convention('verif')
        utils.make_dir(self.obscachedir)

        for _date in self.salldates:
            _ofile = f'{self.obscachedir}/{filename.format(_date, self.params)}'
            if _ofile in self.files_to_retrieve:
                file = f'{self.root_server}{_date[:4]}/{_date[4:6]}/{self.filebase}{_date}{self.fileext}'
                if verbose:
                    print(f'Processing file {file}')
                da_in = xr.open_dataset(file)[params_verdata[self.params][self.name]]
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
