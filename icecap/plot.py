""" Script for metric calculation and plotting """
import argparse

import clargs
import config
import metrics
import utils
import plottypes


if __name__ == '__main__':
    des = 'Plot a metric from staged data files'
    parser = argparse.ArgumentParser(description=des,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    clargs.add_config_option(parser)
    clargs.add_verbose_option(parser)
    clargs.add_plot_config_option(parser)
    clargs.add_plotid(parser)

    args = parser.parse_args()
    if args.plotconfigfile:
        args.configfile.append(args.plotconfigfile)

    conf = config.Configuration(file=args.configfile)
    utils.print_banner(conf.plotsets[args.plotid].plottype)

    m = metrics.factory.create(args.plotid, conf)

    m.compute()
    m.save()
    if m.gettype() == 'map':
        p = plottypes.MapPlot(conf, args.plotid,m)
    elif m.gettype() == 'ts':
        p = plottypes.TsPlot(conf,m)



    utils.print_info('PLOTTING')
    p.plot(m)
