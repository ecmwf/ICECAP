""" Script for metric calculation and plotting """
import argparse

import clargs
import config
import metrics
import utils
import plottype_map
import plottype_ts


def plot_api(conf, args):
    """
    API running all steps to plot metric
    (can e.g also called from jupyter notebook)
    :param conf: configuration object
    :param args: command line arguments
    :return: list of output files created
    """
    utils.print_banner(conf.plotsets[args.plotid].plottype)

    m = metrics.factory.create(args.plotid, conf)
    m.compute()
    m.save()

    if m.gettype() == 'map':
        p = plottype_map.MapPlot(conf, args.plotid, m)
    elif m.gettype() == 'ts':
        p = plottype_ts.TsPlot(conf, m)

    utils.print_info('PLOTTING')
    ofiles = p.plot(m)

    return ofiles

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

    plot_api(conf, args)
