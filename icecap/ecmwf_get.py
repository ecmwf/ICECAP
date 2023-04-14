"""Script to be executed to retrieve and process data at ECMWF"""


import argparse
import os
import config
import clargs
import ecmwf


os.environ['HDF5_USE_FILE_LOCKING']='FALSE'


if __name__ == '__main__':
    description = 'Stage forecast or analysis from MARS tape archive'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    clargs.add_config_option(parser)
    clargs.add_staging_expid(parser)

    clargs.add_staging_startdate(parser, allow_multiple=False)

    clargs.add_staging_exptype(parser)
    clargs.add_staging_mode(parser)
    args = parser.parse_args()

    conf = config.Configuration(file=args.configfile)

    marsdata = ecmwf.EcmwfData(conf, args)
 #   marsdata.get_from_tape(dryrun=True)
    marsdata.process()
#    marsdata._check_files()
