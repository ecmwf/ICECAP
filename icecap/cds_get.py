"""Script to be executed to retrieve and process data from the CDS"""


import argparse
import os
import config
import clargs
import cds
import utils

os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

if __name__ == '__main__':
    description = 'Stage forecast or analysis from MARS tape archive'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    clargs.add_config_option(parser)
    clargs.add_staging_expid(parser)

    clargs.add_staging_startdate(parser, allow_multiple=False)
    clargs.add_staging_exptype(parser)
    clargs.add_verbose_option(parser)

    args = parser.parse_args()

    conf = config.Configuration(file=args.configfile)

    data = cds.CdsData(conf, args)

    if args.exptype == 'INIT':
        data.create_folders()
        data.process_lsm()
    elif args.exptype == 'WIPE':
        data.remove_native_files()
    else:
        if not data.check_cache(verbose=args.verbose):
            data.get_from_tape(dryrun=False)
            data.process()
            data.clean_up()


    utils.print_banner('ALL DONE')
