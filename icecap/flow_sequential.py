""" generate software flow which can be used to run
 ICECAP in batch mode """

import flow
import utils
from nersc_tmp_get import nersc_tmp_api
from cds_get import cds_api
from verdata_get import verdata_api
from plot import plot_api


class ProcesstreeSequential(flow.Tree):
    """
    Anything needed to be carried out, which is machine independent,
    will be in this flow class if run sequentially (jupyter notebook)
    """


    def __init__(self, conf):
        super().__init__(conf)
        self.fcsets = conf.fcsets
        self.conf = conf

    def retrieve_verdata(self, verbose=False):
        """
        Retrieve observations
        :param verbose: True or False
        """
        verdata_api(self.conf, verbose)

    def retrieve_forecasts(self, args):
        """
        Retrieve forecast data
        :param args: command line arguments
        """
        for expid in self.conf.fcsets.keys():
            loopdates = self.conf.fcsets[expid].sdates
            if self.conf.fcsets[expid].source in ['nersc_tmp']:
                args.expid = expid
                args.startdate = 'INIT'
                nersc_tmp_api(self.conf, args)

                for date in loopdates:
                    args.startdate = date
                    nersc_tmp_api(self.conf,args)

            elif self.conf.fcsets[expid].source in ['cds']:
                args.expid = expid
                args.exptype = 'INIT'
                args.startdate = loopdates[0]
                cds_api(self.conf, args)

                for date in loopdates:
                    args.startdate = date
                    args.exptype = 'fc'
                    cds_api(self.conf,args)



        utils.print_banner('ALL DONE')

    def plot(self, args, plotid_select=None):
        """
        Plot results
        :param args: command line arguments
        :param plotid_select: if None plot all plotsets, otherwise only selected
        :return: list of output files
        """
        ofiles_all = []
        if plotid_select is None:
            loop_ids = self.conf.plotsets.keys()
        else:
            loop_ids = utils.convert_to_list(plotid_select)

        for plotid in loop_ids:
            args.plotid = plotid
            ofiles = plot_api(self.conf, args)
            ofiles_all += ofiles

        return ofiles_all

    def execute(self, args):
        """
        Execute batch mode
        :param args: command line arguments
        :return: output files as list
        """
        self.retrieve_verdata(args.verbose)
        self.retrieve_forecasts(args)
        ofiles = self.plot(args)
        return ofiles
