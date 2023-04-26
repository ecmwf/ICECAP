"""Script to be executed to retrieve and process verification data"""

import os
import argparse
import config
import clargs
import verdata
import utils

os.environ['HDF5_USE_FILE_LOCKING']='FALSE'

if __name__ == '__main__':
    description = 'Stage forecast or analysis from MARS tape archive'
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    clargs.add_config_option(parser)
    clargs.add_verbose_option(parser)
    args = parser.parse_args()
    conf = config.Configuration(file=args.configfile)

    data = verdata.VerifData(conf)
    if not data.check_cache(check_level=1, verbose=args.verbose):
        data.process(verbose=args.verbose)



    utils.print_banner('ALL DONE')
