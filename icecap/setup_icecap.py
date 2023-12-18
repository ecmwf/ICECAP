""" Module with functions needed to create environment
create folders. copy scripts etc
"""

import os
import shutil
import ecmwf
import utils
import flow

def create_flow(conf):
    """
    returns appropriate object based on local environment
    :param conf: configuration object
    :return: flow object
    """
    if conf.machine is None:
        return flow.ProcessTree(conf)
    if conf.machine == 'ecmwf':
        return ecmwf.EcmwfTree(conf)

    raise ValueError(f'Machine name {conf.machine} is not allowed. ')

class ExecutionHost:
    """
    execution host object to create and wipe needed directories
    """
    def __init__(self, conf):
        """
        :param conf: ICECAP configuration object
        """
        self.suitename = conf.suitename
        self.sourcedir = conf.sourcedir
        self.pydir = conf.pydir
        self.machine = conf.machine
        self.ecflow = conf.ecflow
        self.ecffilesdir = conf.ecffilesdir
        self.etcdir = conf.rundir+'/etc'
        self.filename = conf.filename

        self.directories_create = [conf.pydir, conf.pydir + '/metrics', conf.pydir + '/contrib',
                              conf.pydir + '/aux', conf.metricdir, conf.plotdir,
                              conf.cachedir, conf.tmpdir,
                                   self.etcdir]
        self.directories_create_ecflow = [conf.ecffilesdir, conf.ecfincdir, conf.ecfhomeroot]

        self.directories_wipe = [conf.rundir, conf.datadir, conf.tmpdir]
        self.directories_wipe_full = [conf.cachedir]


        # this is to make sure machine = ecmwf is set if needed (to avoid using wrong head.h settings)
        # this will cause problems if ecflow_host starts with 'ecflow-gen-' on other machine as well
        if 'ecflow-gen-' in conf.ecflow_host:
            if not self.machine == 'ecmwf':
                raise ValueError('It seems that you are working on ECMWF..so please set machine to ecmwf')


    def wipe(self, args):
        """
        wipe execution host by deleting directories
        :param args: command line arguments
        """
        print(f'Wiping suite {self.suitename} on execution host!')
        _directories_wipe = self.directories_wipe
        if args.wipe == 2:
            _directories_wipe += self.directories_wipe_full


        for directory in _directories_wipe:
            if os.path.exists(directory):
                if args.verbose:
                    print(f'  Deleted {directory} ')
                shutil.rmtree(directory)

    def setup(self, args):
        """
        setup execution host by creating directories and copying scripts
        :param args: command line arguments
        """
        _directories_create = self.directories_create
        if self.ecflow == 'yes':
            _directories_create += self.directories_create_ecflow


        for directory in _directories_create:
            utils.make_dir(directory, verbose=args.verbose)

        fromdir = self.sourcedir + '/icecap'
        self._copy_python_scripts(fromdir, args)

        if self.ecflow == 'yes':
            fromdir = self.sourcedir + '/ecf'
            self._copy_ecflow_files(fromdir, args, base_level_files_only=True)

            if self.machine:
                fromdir = self.sourcedir + f'/ecf/{self.machine}'
                self._copy_ecflow_files(fromdir, args)
                # copy etc files for machine
                fromdir = self.sourcedir + f'/etc/{self.machine}'
                self._copy_etc_files(fromdir, args)
            else:
                fromdir = self.sourcedir + '/ecf/include'
                self._copy_ecflow_files(fromdir, args, base_level_files_only=True)





        # copy config file
        self._safe_copy(args, self.filename, './', self.pydir, 'icecap.conf')

    def _copy_etc_files(self, fromdir, args):
        files = ['load_modules', 'module_versions']
        target_dir = self.etcdir
        for file in files:
            self._safe_copy(args, file, fromdir, target_dir)


    def _copy_ecflow_files(self, fromdir, args, base_level_files_only=False):
        """
        Recursively copy system dependent ecflow scripts to the location specified in ECF_FILES.
        :param conf: configuration object
        :param fromdir: source directory
        :param args: command line arguments (force and verbose)
        """

        module_files = ['load_modules', 'module_versions']
        ecfsourcedir = fromdir
        if not os.path.exists(ecfsourcedir):
            raise RuntimeError(f'Source directory with ecFlow scripts '
                               f'{ecfsourcedir} does not exist')

        if not base_level_files_only:
            for root, dirs, files in os.walk(ecfsourcedir):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for file in files:
                    target_dir = self.ecffilesdir + root.replace(ecfsourcedir, '')
                    if file.endswith('.ecf') or file.endswith('.h') or file in module_files:
                        self._safe_copy(args, file, root, target_dir)
        else:
            for file in os.listdir(ecfsourcedir):
                target_dir = self.ecffilesdir
                if file.endswith('.h'):
                    target_dir = self.ecffilesdir+'/include'
                if file.endswith('.ecf') or file.endswith('.h') or file in module_files:
                    self._safe_copy(args, file, ecfsourcedir, target_dir)


    def _copy_python_scripts(self, fromdir, args):
        """
        Recursively copy python code and auxiliary files to the PYDIR location.
        :param conf: configuration object
        :param fromdir: source directory
        :param args: command line arguments (force and verbose)
        """

        module_files = ['load_modules', 'module_versions']
        pysourcedir = fromdir
        if not os.path.exists(pysourcedir):
            raise RuntimeError(f'Source directory with Python scripts {pysourcedir} does not exist')
        for root, dirs, files in os.walk(pysourcedir):
            dirs[:] = [d for d in dirs if
                       not d.startswith('.') and not d.startswith('_')
                       and d != 'tests']
            target_dir = self.pydir + root.replace(pysourcedir, '')
            if not os.path.isdir(target_dir):
                msg = f'Directory {target_dir} should have been created before copying files'
                raise RuntimeError(msg)
            for file in files:
                py_dontcopy = ['icecap.py']
                if (file.endswith('.py') and file not in py_dontcopy) or file in module_files:
                    self._safe_copy(args, file, root, target_dir)
                elif 'aux' in root or 'contrib' in root:
                    self._safe_copy(args, file, root, target_dir)

    @staticmethod
    def _safe_copy(args, fname, source_dir, target_dir, fname_save=None):
        """
        check whether target file exists and copy if appropriate
        :param args: arguments providing force and verbose
        :param fname: name of the file
        :param source_dir: source directory
        :param target_dir: target directory
        :param fname_save: set to other than None tp specify output file name (if different from fname)
        """

        sfile = os.path.join(source_dir, fname)
        if fname_save is None:
            fname_save = fname
        tfile = os.path.join(target_dir, fname_save)

        if os.path.isfile(tfile):
            if not args.force:
                raise RuntimeError(('File {} exists. ' +
                                    '\nUse option --force to overwrite').format(tfile))
        if args.verbose:
            print(f'Copying file {sfile} --> {target_dir}')
        shutil.copy(sfile, f'{target_dir}/{fname_save}')
