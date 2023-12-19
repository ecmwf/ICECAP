""" generate software flow by generating a flow-like strusture
which is later translated into an ecflow suiate or batch mode """

from collections import OrderedDict
import json
import os
import subprocess
import ecflow
import utils


def _merge_dict(first_dict, second_dict):
    """ Merge two dictionaries
    :param first_dict: first dictionary to be merged
    :param second_dict: second dictionary to be merged with first_dict
    :return: merged dictionary
    """
    for _keys, _variable in first_dict.items():
        if _keys in second_dict:
            second_dict[_keys] = _merge_dict(_variable, second_dict[_keys])
    merged_dict = first_dict.copy()
    merged_dict.update(second_dict)
    return merged_dict


class Tree:
    """
    object with attributes used to generate the ecflow or batch mode
    """

    def __init__(self, conf):
        self.attrs = []
        self.attrs_parents = []

        self.machine = conf.machine
        self.rundir = conf.rundir
        self.suitename = conf.suitename
        self.ecflow = conf.ecflow
        if self.ecflow == "yes":
            self.user = conf.user
            self.ecflow_host = conf.ecflow_host
            self.ecflow_port = conf.ecflow_port
            self.name = conf.suitename
            self.stage_together = conf.stage_sources_together
            self.toplevel_suite = conf.toplevel_suite
            self.suitename = conf.suitename
            self.begin_suite_suspended = conf.begin_suite_suspended
            self.stop_at_first_problem = conf.stop_at_first_problem
            self.split_get = conf.split_get
            self.ecfincdir = conf.ecfincdir
            self.ecffilesdir = conf.ecffilesdir
            self.ecfhomedir = conf.ecfhomeroot
            self.sourcedir = conf.sourcedir
            self.pydir = conf.pydir
            self.stagedir = conf.stagedir
            self.verana = conf.verdata
            self.fcsets = conf.fcsets
            self.defs_file = self.rundir + '/' + self.suitename + '.def'
            self.defs = ecflow.Defs()
            self.maximum_processes_plot = conf.maximum_processes_plot

    def add_attr(self, attr, parent):
        """
        Add attribute to class object
        :param attr: list of attributes to be added (see documentation for formatting)
        :param parent: parent to which atbute should be added
        """
        self.attrs.append(attr)
        self.attrs_parents.append(parent)

    def _create_dict_from_tree(self):
        """
        Internal function to create dictionary from _object.attrs and _object.attrs_parents
        :return: dictionary of flow object
        """
        out_dict = OrderedDict()
        for x_i, x_val in enumerate(self.attrs_parents):
            my_dict = current = {}

            for n_i, name in enumerate(x_val.split(':')):
                if name not in current.keys():
                    current[name] = {}
                if n_i < len(x_val.split(':')) - 1:
                    current = current[name]
            for attr in self.attrs[x_i]:
                # current[name] = _object.attrs[x_i]
                if not attr.split(':')[0] in current[name].keys():
                    current[name][attr.split(':')[0]] = [attr.split(':')[1]]
                else:
                    current[name][attr.split(':')[0]].append(attr.split(':')[1])
            out_dict = _merge_dict(out_dict, my_dict)

        # put retrieval to beginning
        if "retrieval" in out_dict:
            out_dict.move_to_end('retrieval', last=False)

            # sort retrieval of forecasts to be in order
            for sort_family in ['retrieval', 'clean']:
                if sort_family in out_dict:
                    dict_tmp = OrderedDict(out_dict[sort_family])
                    retrieval_families = sorted(list(dict_tmp.keys()))

                    for family in retrieval_families:
                        dict_tmp.move_to_end(family, last=True)
                    if 'verdata' in retrieval_families:
                        dict_tmp.move_to_end('verdata', last=False)
                    if 'clean' in retrieval_families:
                        dict_tmp.move_to_end('clean', last=False)
                    out_dict[sort_family] = dict_tmp



        return out_dict

    def to_json(self, ofile=None):
        """
        Saves dictionary to JSON file
        :param ofile: output file to which to save JSON (set to default ift specified)
        """

        if ofile is None:
            ofile = f'{self.rundir}/{self.suitename}.json'
        _todict = self._create_dict_from_tree()
        print(f'Writing flow object to {ofile}')
        with open(ofile, 'w', encoding="utf-8") as fout:
            json_dumps_str = json.dumps(_todict, indent=4)
            print(json_dumps_str, file=fout)

    def build_ecflow(self):
        """
        Build ecflow suite parameters based on config file and attributes in flow object
        :param clargs: command line arguments
        :param defs_file: ecflow definition file
        """

        toplevel_s = self.defs.add_suite(self.toplevel_suite)
        suite_f = toplevel_s.add_family(self.suitename)
        try:
            if self.begin_suite_suspended:
                suite_f.add_defstatus(ecflow.DState.suspended)
        except AttributeError:
            pass

        # add limits
        if self.machine == 'ecmwf':
            toplevel_s.add_limit('mars', 8)  # limit number of active MARS requests
        toplevel_s.add_limit('plot', int(self.maximum_processes_plot))  # limit total number of active tasks

        # add suite variables
        suite_f.add_variable('ECF_PYTHON', subprocess.check_output('which python3', shell=True).strip())
        suite_f.add_variable('ECF_INCLUDE', self.ecfincdir)
        suite_f.add_variable('ECF_FILES', self.ecffilesdir)
        suite_f.add_variable('ECF_HOME', self.ecfhomedir)
        suite_f.add_variable('PYDIR', self.pydir)
        suite_f.add_variable('ETCDIR', self.rundir + '/etc')

        _todict = self._create_dict_from_tree()

        self._dict_walk(_todict, suite_f)

    def load_ecflow(self, force=False):
        """
        check ecflow server and load/replace suite
        :param force: re-create ecflow server if already existing
        """

        client = ecflow.Client(self.ecflow_host, self.ecflow_port)
        client.sync_local()
        defs = client.get_defs()

        suitepath = f'/{self.toplevel_suite}/{self.name}'
        suite = defs.find_abs_node(suitepath)
        if suite is None:  # suite not yet loaded on server
            utils.print_info(f'Loading new suite {self.name} into server {self.ecflow_host}')
        else:
            if not force:
                raise RuntimeError(f'Suite {suitepath} exists on server {self.ecflow_host}. '+
                                   '\nUse option --force to re-create it.')

            utils.print_info(f'Replacing existing suite {self.name} on server {self.ecflow_host}')
        client.replace(suitepath, self.defs_file)
        client.begin_suite('/' + self.toplevel_suite)

    def wipe_ecflow_host(self, wipe_level):
        """Removes suite from ecFlow server and deletes ecFlow files"""
        ci = ecflow.Client(self.ecflow_host, self.ecflow_port)
        ci.sync_local()
        defs = ci.get_defs()
        abs_path = '/'.join([self.toplevel_suite, self.suitename])
        suitename = self.suitename
        if wipe_level == 2:
            abs_path = '/'.join([self.toplevel_suite])
            suitename = self.toplevel_suite
        suite = defs.find_abs_node(abs_path)
        # delete from ecflow server
        if suite is not None:
            ci.delete(abs_path)
            print(f'  Deleted suite {suitename.upper()} '
                  f'from ecflow server {self.ecflow_host} '
                  f'at port {self.ecflow_port}.')
        else:
            print(('  Nothing to do for ecflow server {} at port {}, ' +
                   'suite definition is not loaded.').format(
                self.ecflow_host, self.ecflow_port))

    @staticmethod
    def _add_ecflow_value(_list, suite_f, name):
        """
        Add variable/repeat/task/trigger to ecflow suite
        :param _list: list object containing variable names/reapeat dates/task name/trigger values
        :param suite_f: suite object to which to add to
        :param name: either variable/repeat/task/trigger
        """
        if name == 'variable':
            # expects _list to have 2 items
            # example: _list = ['MODE;fc']
            # function will add a variable called MODE and set it to fc (delimiter is always ;)

            _ = [suite_f.add_variable(v.split(';')[0], str(v.split(';')[1])) for v in _list]

        if name == 'repeat':
            # expects _list to have 2 items
            # example: _list = ['DATES;['1990101','20000101']]
            # function will add repeat named DATES and setting it
            #  to list given as second string separated by ; (delimiter is always ;)
            _ = [suite_f.add_repeat(
                ecflow.RepeatString(v.split(';')[0],
                                    json.loads((v.split(';')[1]).replace("'", '"'))))
                for v in _list]

        if name == 'task':
            # expects _list to have 1 or 2  item only (taskname)
            # example _list = ['ecmf_get'] or _list = ['ecmf_get;mars']
            # function will create task and add it to suite with the task name ecmwf_get
            # if len == 2 then 2nd argument is interpreted as inlimit value
            for _task in _list:
                if len(_task.split(';')) == 1:
                    suite_f.add_task(_task)
                elif len(_task.split(';')) == 2:
                    _ecflowtask = suite_f.add_task(_task.split(";")[0])
                    _ecflowtask.add_inlimit(_task.split(";")[1])

        if name == 'trigger':
            # expects _list to have 1 item if only one trigger else 2 items
            # example _list = ['retrieval==complete'] or ['retrieval!=aborted;True']
            for _trigger in _list:
                if len(_trigger.split(';')) == 1:
                    suite_f.add_part_trigger(_trigger)
                elif len(_trigger.split(';')) == 2:
                    suite_f.add_part_trigger(_trigger.split(";")[0],
                                             json.loads((_trigger.split(";")[1]).lower()))


    def _dict_walk(self, flow_dict, suite_level):
        """
        Walking through the dictionary to create ecflow families or batch scripts
        :param d: dictionary with parents and attributes
        :param suite_level: base suite object
        """

        # global attributes needs to be added first to make sure they are on the root suite level
        if 'global' in flow_dict.keys():
            for name in flow_dict['global'].keys():
                self._add_ecflow_value(flow_dict['global'][name], suite_level, name)

        for _keys, _variable in flow_dict.items():
            if _keys not in ['global']:
                if isinstance(_variable, dict):
                    if self.ecflow == 'yes':
                        tmp_f = suite_level.add_family(_keys)
                    else:
                        tmp_f = _keys
                    self._dict_walk(_variable, tmp_f)
                else:
                    # add value as ecflow task or batch mode env-variable
                    if self.ecflow == 'yes':
                        self._add_ecflow_value(_variable, suite_level, _keys)

    def save_defs(self, force=False):
        """ Save suite definition into a text file
        :param force: set to True to overwrite definition file if already existing
        """
        if not os.path.exists(self.defs_file):
            self.defs.save_as_defs(self.defs_file)
        else:
            if force:
                self.defs.save_as_defs(self.defs_file)
            else:
                errmsg = f'ecFlow suite definition file {self.defs_file} exists.\n ' \
                         f'Use --force option to overwrite.'
                raise RuntimeError(errmsg)

        checkoutput = self.defs.check_job_creation()
        if len(checkoutput) != 0:
            print('Suite building FAILED!')
            print(checkoutput)
            raise RuntimeError

        print('Saved suite definition as ' + self.defs_file)


class ProcessTree(Tree):
    """
    Anything needed to be carried out, which is machine independent,
    will be in this flow class
    """

    def __init__(self, conf):
        super().__init__(conf)

        # here the next steps which are independent from machines will be listed
        trigger_plot = ['trigger:plot != aborted']

        if conf.fcsets:
            self.add_attr(['trigger:retrieval != aborted'], 'retrieval')
            self.add_attr(['task:verdata_retrieve'], 'retrieval:verdata')
            trigger_plot = ['trigger:retrieval==complete','trigger:plot != aborted;True']
            finish_trigger = 'retrieval'

        if bool(conf.plotsets):
            self.add_attr(trigger_plot, 'plot')
            finish_trigger = 'plot'
        for plotid in conf.plotsets:
            self.add_attr(['task:plot;plot',
                           f'variable:PLOTTYPE;{plotid}'], f'plot:{plotid}')


        if conf.keep_native == 'yes':
            clean_trigger = 'retrieval'
            finish_trigger = 'clean'
            if bool(conf.plotsets):
                clean_trigger = 'plot'
            self.add_attr([f'trigger:{clean_trigger}==complete'], 'clean')


        self.add_attr([f'trigger:{finish_trigger}==complete','task:clean'], 'finish')


        for expid in conf.fcsets.keys():
            if conf.fcsets[expid].source != self.machine:
                self.add_attr([f'variable:EXPID;{expid}',
                               'trigger:verdata==complete'], f'retrieval:{expid}')



                if conf.fcsets[expid].source in ['nersc_tmp']:
                    if conf.keep_native == 'yes':
                        self.add_attr([f'variable:EXPID;{expid}',
                                       'variable:DATES;WIPE',
                                       f'task:{conf.fcsets[expid].source}_retrieve'], f'clean:{expid}')

                    self.add_attr(['variable:DATES;INIT',
                                   f'task:{conf.fcsets[expid].source}_retrieve'], f'retrieval:{expid}:init')
                    self.add_attr([f'repeat:DATES;{self.fcsets[expid].sdates}',
                                   f'task:{conf.fcsets[expid].source}_retrieve',
                                   'trigger:init==complete'],
                                  f'retrieval:{expid}:{conf.fcsets[expid].mode}')

                elif conf.fcsets[expid].source in ['cds']:
                    loopdates = self.fcsets[expid].sdates
                    self.add_attr([f'variable:DATES;{loopdates[0]}',
                                    'variable:TYPE;INIT',
                                   f'task:{conf.fcsets[expid].source}_retrieve'], f'retrieval:{expid}:init')
                    self.add_attr([f'repeat:DATES;{loopdates}',
                                   'variable:TYPE;fc',
                                   f'task:{conf.fcsets[expid].source}_retrieve',
                                   'trigger:init==complete'],
                                  f'retrieval:{expid}:{conf.fcsets[expid].mode}')

                    if conf.keep_native == 'yes':
                        self.add_attr([f'variable:EXPID;{expid}',
                                       'variable:DATES;{loopdates[0]}',
                                        'variable:TYPE;WIPE',
                                       f'task:{conf.fcsets[expid].source}_retrieve'], f'clean:{expid}')
                else:
                    raise ValueError(f'Retrieval for {conf.fcsets[expid].source} not implemented')
