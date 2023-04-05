"""
This module should contain all ecmwf specific relevant information, e.g.
mars retrieval, ecmwf retrieval flow
"""

import flow


class EcmwfTree(flow.ProcessTree):
    """
    Specific ECMWF flow
    """
    def __init__(self, conf):
        super().__init__(conf)
        # self.add_attr(['variable:EXEHOST;hpc-batch'], f'global')
        site = 'hpc'
        self.add_attr([f'variable:ECF_JOB_CMD;troika submit -o %ECF_JOBOUT% {site} %ECF_JOB%',
                       f'variable:ECF_KILL_CMD;troika kill {site} %ECF_JOB%',
                       f'variable:ECF_STATUS_CMD;troika monitor {site} %ECF_JOB%',
                       'variable:EXEHOST;hpc-batch'], 'global')

        for expid in conf.fcsets.keys():
            if conf.fcsets[expid].mode in ['fc', 'both']:
                self.add_attr(['variable:MODE;fc',
                               'repeat:DATES;{}'.format(self.fcsets[expid].sdates)],
                              f'retrieval:{expid}:fc')
                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:fc:cf')
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;pf'], f'retrieval:{expid}:fc:pf')

            if conf.fcsets[expid].mode in ['hc', 'both']:
                self.add_attr(['variable:MODE;hc',
                               'repeat:DATES;{}'.format(self.fcsets[expid].shcrefdate)],
                              f'retrieval:{expid}:hc')
                if conf.fcsets[expid].fcsystem in ['extended-range', 'medium-range']:
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;cf'], f'retrieval:{expid}:hc:cf')
                    self.add_attr(['task:ecmwf_retrieve;mars',
                                   'variable:TYPE;pf'], f'retrieval:{expid}:hc:pf')


class EcmwfRetrieval:
    """Defines a single ECMWF retrieval request"""

    #@staticmethod
    #def factory(conf, kwargs):

