"""
This module contains all relevant information, to retrieve
topaz4 data from temporary THREDDS server
NOTE: Needs to be adapted if server changes (only for tests implemented)
"""

import xarray as xr
import dataobjects
import utils

class NerscData(dataobjects.ForecastObject):
    """ Class for Topaz4 data for retrieval and processing
    Might be used as template for final implementation """

    def __init__(self, conf, args):

        utils.print_info('This is a temporary implementation to retrieve '
                         'TOPAZ4 test data from THREDDS server')

        super().__init__(conf, args)

        if args.startdate not in ['INIT','WIPE']:
            self.cycle = self.init_cycle(self.startdate)
            self.fccachedir = self.init_cachedir()
            self.linterp = True
            self.periodic = False


            if self.expname == 'topaz4':
                server_ext = 't42'
                self.varname = 'fice'
            elif self.expname == 'topaz5':
                server_ext = 't5'
                self.varname = 'siconc'
            else:
                raise ValueError(f'Retrieval for expname {self.expname} not implemented')

            self.root_server = f"https://thredds.met.no/thredds/dodsC/acciberg{server_ext}/bulletins/"
            # format is YYYY/MM/topaz?_mem???_bYYYY-MM-DDT00.ncml
            self.fileformat = '{}/'f'{self.expname}''_mem{:03d}_b{}T00.ncml'



    def make_filelist(self):
        filename = self._filenaming_convention('fc')

        files = [filename.format(self.startdate, member, self.params, self.grid)
                 for member in range(self.enssize)]
        files_list = [self.fccachedir + '/' + file for file in files]

        return files_list

    def process(self):
        """ Download and stage data """
        startdatedt = utils.string_to_datetime(self.startdate)
        startdatestring = utils.datetime_to_string(startdatedt,'%Y-%m-%d')

        for member in range(self.enssize):

            ofile = self._save_filename(date=self.startdate, number=member, grid=self.grid)

            if ofile in self.files_to_retrieve:

                file_tmp = self.root_server+self.fileformat.format(startdatedt.strftime('%Y/%m'),
                                                                   member+1,startdatestring)

                ds_in = xr.open_dataset(file_tmp)
                da_in = ds_in[self.varname].rename(self.params)
                da_in = da_in.expand_dims({'number': [member]})
                da_in = da_in.transpose('number','time', 'y', 'x')

                if self.keep_native == "yes":
                    da_out_save = da_in.isel(time=slice(self.ndays))

                    # save projection details as attributes
                    if getattr(da_out_save, 'grid_mapping') == 'stereographic':
                        da_in_grid = ds_in['stereographic']
                        da_out_save.attrs['projection'] = 'Stereographic'
                        da_out_save.attrs['central_latitude'] = getattr(da_in_grid, 'latitude_of_projection_origin')
                        da_out_save.attrs['central_longitude'] = getattr(da_in_grid, 'longitude_of_projection_origin')
                    da_out_save = da_out_save.rename({'y':'yc','x':'xc'})
                    da_out_save['yc'] = da_out_save['yc'] *100 *1000
                    da_out_save['xc'] = da_out_save['xc'] * 100 * 1000
                    ofile = self._save_filename(date=self.startdate, number=member, grid='native')
                    da_out_save.sel(number=member).to_netcdf(ofile)


                if self.linterp:
                    da_out_save = self.interpolate(da_in.isel(time=slice(self.ndays)))
                    ofile = self._save_filename(date=self.startdate, number=member, grid=self.grid)
                    da_out_save.sel(number=member).to_netcdf(ofile)
