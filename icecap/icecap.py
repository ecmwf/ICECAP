#!/usr/bin/env python3
"""
Setup script to be executed to start ICECAP
"""

import argparse
import config
import setup_icecap



def parse_clargs():
    """
    add arguments to parser
    :return: parser arguments
    """
    parser = argparse.ArgumentParser(description='Set up ICECAP suite '
                                                 + '(create directories, copy code to runtime '
                                                   'directory, build & play ecflow suite '
                                                   'if needed)',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-c', '--configfile',
                        default='icecap.conf',
                        help='configuration file to use')

    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='force recreation of code and suite. '
                             + 'WARNING: Using force implies loss of old code '
                               'and suite definition.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='verbose for more debugging output')
    parser.add_argument('-w', '--wipe', action='count', default=0,
                        help='delete data and runtime scripts, '
                             'and remove ecflow suite from server - '
                             'use -w for wiping only this suite; '
                             'use -ww to delete whole icecap from machine'
                             )

    return parser.parse_args()




if __name__ == '__main__':
    args = parse_clargs()
    conf = config.Configuration(file=args.configfile)
    flow = setup_icecap.create_flow(conf)
    execution_host = setup_icecap.ExecutionHost(conf)


    if args.wipe > 0:
        execution_host.wipe(args)
        if conf.ecflow == 'yes':
            flow.wipe_ecflow_host(args.wipe)

    else:
        execution_host.setup(args)
        if args.verbose:
            flow.to_json()
        if conf.ecflow == 'yes':
            flow.build_ecflow()
            flow.save_defs(force=args.force)
            flow.load_ecflow(force=args.force)
