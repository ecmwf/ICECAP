"""Module with parent class with attributes linked
to forecasts and verification data"""
import os

xr = None

class DataObject:
    """ Parent data object, with attributes valid
    for both forecasts and verification data"""

    def __init__(self, conf):
        self.params = conf.params
        self.cachedir = None
        self.ndays = conf.ndays
        self.filelist = None

    def check_cache(self, check_level=2, verbose=False):
        """
        Check if files already exist in cachedir
        :param check_level: check only if file exists (1)
                            check if timesteps are correct (2)
        :param verbose: switch on debugging output
        """

        files_to_check = self.make_filelist()
        if verbose:
            print(f'files to check {files_to_check}')

        for file in files_to_check:
            # quick check if exist
            if not os.path.exists(f'{self.cachedir}/{file}'):
                if verbose:
                    print(f'Not all files are found in cache {self.cachedir}/{file}')
                return False

        if check_level > 1:
            global xr
            if xr is None:
                import xarray as xr

            for file in files_to_check:
                ds_in = xr.open_dataset(f'{self.cachedir}/{file}')
                if len(ds_in.time) < self.ndays:
                    if verbose:
                        print(f'Not all timesteps needed found in {self.cachedir}/{file}')
                    return False
        return True

    def make_filelist(self):
        """
        Create list of files to be saved in cachedir
        This depends on the forecast/verification object and is thus
        overriden by the respective class
        """
        self.filelist = []
        return self.filelist

    @staticmethod
    def _filenaming_convention(args):
        """
        Naming convention for verification and forecast cache files
        :param args: fc for forecast data and verif for verification data
        """
        if args == 'fc':
            return '{}_mem-{:03d}_{}.nc'
        if args == 'verif':
            return '{}_{}.nc'

        raise f'Argument {args} not supported'
