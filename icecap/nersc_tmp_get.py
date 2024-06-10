"""Script to be executed to retrieve and process data at ECMWF"""


import argparse
import os
import config
import clargs
import nersc_tmp
import utils


os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

def nersc_tmp_api(conf, args):
    """
    API running all steps to retrieve NERSC data
    (can e.g also called from jupyter notebook)
    :param conf: configuration object
    :param args: command line arguments
    :return: N/A
    """

    data = nersc_tmp.NerscData(conf, args)

    if args.startdate == 'INIT':
        data.create_folders()
    elif args.startdate == 'WIPE':
        data.remove_native_files()
    else:
        if not data.check_cache(verbose=args.verbose):
            data.process()
            data.clean_up()



if __name__ == '__main__':
    description = 'Stage forecast from Met Norway Thredds server (experimental)'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    clargs.add_config_option(parser)
    clargs.add_staging_expid(parser)

    clargs.add_staging_startdate(parser, allow_multiple=False)

    clargs.add_verbose_option(parser)

    args = parser.parse_args()

    conf = config.Configuration(file=args.configfile)
    nersc_tmp_api(conf, args)
    utils.print_banner('ALL DONE')
