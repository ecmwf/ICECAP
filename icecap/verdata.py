"""Module containing verification classes"""

import dataobjects
import setup_icecap

params_verdata = {
    'sic' : {
        'osi-450-a' : 'ice_conc',
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
        'osi-450-a': _EumetsatThredsRetrieval(conf)
    }

    return selector[conf.verdata]



class VerifyingData(dataobjects.DataObject):
    """ Verification parent class object """
    def __init__(self, conf):
        super().__init__(conf)
        self.name = conf.verdata
        self.salldates = conf.salldates
        self.cachedir = f'{conf.cachedir}/{self.name}/'
        self.param = conf.params


    def make_filelist(self):
        """Generate a list of files which are expected to be staged"""
        filename = self._filenaming_convention('verif')
        files = [filename.format(date, self.params)
                 for date in self.salldates]
        return files




class _EumetsatThredsRetrieval(VerifyingData):
    def __init__(self, conf):
        super().__init__(conf)
        self.root_server = "https://thredds.met.no/thredds/dodsC/osisaf/met.no/"
        if self.name == 'osi-450-a':
            self.root_server += "reprocessed/ice/conc_450a_files/"
            self.filebase = "ice_conc_nh_ease2-250_cdr-v3p0_"
            self.fileext = "1200.nc"


    def process(self, verbose):
        """
        Retrieve and process verification data file
        :param verbose: more debugging output
        """
        filename = self._filenaming_convention('verif')
        setup_icecap.make_dir(self.cachedir)

        import xarray as xr

        for _date in self.salldates:
            file = f'{self.root_server}{_date[:4]}/{_date[4:6]}/{self.filebase}{_date}{self.fileext}'
            if verbose:
                print(f'Processing file {file}')
            da_in = xr.open_dataset(file)[params_verdata[self.param][self.name]]
            da_in = da_in.rename(self.param)
            da_in = da_in.rename({'lon': 'longitude', 'lat': 'latitude'})
            da_in = da_in.transpose( 'time', 'yc', 'xc')
            da_in.to_netcdf(f'{self.cachedir}/{filename.format(_date, self.param)}')
