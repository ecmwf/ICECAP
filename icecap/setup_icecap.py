""" Module with functions needed to create environment
create folders. copy scripts etc
"""

import os
import shutil
import ecmwf

def create_flow(conf):
    """
    returns appropriate object based on local environment
    :param conf: configuration object
    :return: flow object
    """
    if conf.machine == 'ecmwf':
        return ecmwf.EcmwfTree(conf)

    raise RuntimeError('Machine name {} is not allowed. '.format(conf.machine))

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
                              conf.pydir + '/aux', conf.stagedir, conf.metricdir, conf.plotdir,
                              conf.stagedir + '/aux', conf.cachedir, conf.tmpdir,
                                   self.etcdir]
        self.directories_create_ecflow = [conf.ecffilesdir, conf.ecfincdir, conf.ecfhomeroot]
        self.directories_wipe = [conf.rundir, conf.datadir, conf.tmpdir,
                                 ]
        self.directories_wipe_full = [conf.cachedir]

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
            make_dir(directory, verbose=args.verbose)

        fromdir = self.sourcedir + '/icecap'
        self._copy_python_scripts(fromdir, args)

        if self.ecflow == 'yes':
            fromdir = self.sourcedir + f'/ecf/{self.machine}'
            self._copy_ecflow_files(fromdir, args)
            fromdir = self.sourcedir + '/ecf'
            self._copy_ecflow_files(fromdir, args, base_level_files_only=True)

        # copy etc files for machine
        fromdir = self.sourcedir + f'/etc/{self.machine}'
        self._copy_etc_files(fromdir,args)


        # copy config file
        self._safe_copy(args, self.filename, './', self.pydir)

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
    def _safe_copy(args, fname, source_dir, target_dir):
        """
        check whether target file exists and copy if appropriate
        :param args: arguments providing force and verbose
        :param fname: name of the file
        :param source_dir: source directory
        :param target_dir: target directory
        """

        sfile = os.path.join(source_dir, fname)
        tfile = os.path.join(target_dir, fname)
        if os.path.isfile(tfile):
            if not args.force:
                raise RuntimeError(('File {} exists. ' +
                                    '\nUse option --force to overwrite').format(tfile))
        if args.verbose:
            print('Copying file {} --> {}'.format(sfile, target_dir))
        shutil.copy(sfile, target_dir)


def make_dir(directory_name, verbose=False):
    """
    routine to create directory on operating system
    :param directory_name: name of directory to create
    :param verbose: if verbose is True provide additional output
    """
    if not os.path.isdir(directory_name):
        try:
            os.makedirs(directory_name)
        except OSError:
            raise RuntimeError('OS reported error when trying to create\n'
                               + directory_name
                               + '\nIs the path reachable, '
                                 'and do you have write permission?') from None
        if verbose:
            print(f'Created directory {directory_name}')


def print_banner(word):
    """
    Create printed output as banner
    (from https://code.activestate.com/recipes/577537-banner/)
    :param word: word to be printed
    """
    letterforms = '''\
       |       |       |       |       |       |       | |
  XXX  |  XXX  |  XXX  |   X   |       |  XXX  |  XXX  |!|
  X  X |  X  X |  X  X |       |       |       |       |"|
  X X  |  X X  |XXXXXXX|  X X  |XXXXXXX|  X X  |  X X  |#|
 XXXXX |X  X  X|X  X   | XXXXX |   X  X|X  X  X| XXXXX |$|
XXX   X|X X  X |XXX X  |   X   |  X XXX| X  X X|X   XXX|%|
  XX   | X  X  |  XX   | XXX   |X   X X|X    X | XXX  X|&|
  XXX  |  XXX  |   X   |  X    |       |       |       |'|
   XX  |  X    | X     | X     | X     |  X    |   XX  |(|
  XX   |    X  |     X |     X |     X |    X  |  XX   |)|
       | X   X |  X X  |XXXXXXX|  X X  | X   X |       |*|
       |   X   |   X   | XXXXX |   X   |   X   |       |+|
       |       |       |  XXX  |  XXX  |   X   |  X    |,|
       |       |       | XXXXX |       |       |       |-|
       |       |       |       |  XXX  |  XXX  |  XXX  |.|
      X|     X |    X  |   X   |  X    | X     |X      |/|
  XXX  | X   X |X     X|X     X|X     X| X   X |  XXX  |0|
   X   |  XX   | X X   |   X   |   X   |   X   | XXXXX |1|
 XXXXX |X     X|      X| XXXXX |X      |X      |XXXXXXX|2|
 XXXXX |X     X|      X| XXXXX |      X|X     X| XXXXX |3|
X      |X    X |X    X |X    X |XXXXXXX|     X |     X |4|
XXXXXXX|X      |X      |XXXXXX |      X|X     X| XXXXX |5|
 XXXXX |X     X|X      |XXXXXX |X     X|X     X| XXXXX |6|
XXXXXX |X    X |    X  |   X   |  X    |  X    |  X    |7|
 XXXXX |X     X|X     X| XXXXX |X     X|X     X| XXXXX |8|
 XXXXX |X     X|X     X| XXXXXX|      X|X     X| XXXXX |9|
   X   |  XXX  |   X   |       |   X   |  XXX  |   X   |:|
  XXX  |  XXX  |       |  XXX  |  XXX  |   X   |  X    |;|
    X  |   X   |  X    | X     |  X    |   X   |    X  |<|
       |       |XXXXXXX|       |XXXXXXX|       |       |=|
  X    |   X   |    X  |     X |    X  |   X   |  X    |>|
 XXXXX |X     X|      X|   XXX |   X   |       |   X   |?|
 XXXXX |X     X|X XXX X|X XXX X|X XXXX |X      | XXXXX |@|
   X   |  X X  | X   X |X     X|XXXXXXX|X     X|X     X|A|
XXXXXX |X     X|X     X|XXXXXX |X     X|X     X|XXXXXX |B|
 XXXXX |X     X|X      |X      |X      |X     X| XXXXX |C|
XXXXXX |X     X|X     X|X     X|X     X|X     X|XXXXXX |D|
XXXXXXX|X      |X      |XXXXX  |X      |X      |XXXXXXX|E|
XXXXXXX|X      |X      |XXXXX  |X      |X      |X      |F|
 XXXXX |X     X|X      |X  XXXX|X     X|X     X| XXXXX |G|
X     X|X     X|X     X|XXXXXXX|X     X|X     X|X     X|H|
  XXX  |   X   |   X   |   X   |   X   |   X   |  XXX  |I|
      X|      X|      X|      X|X     X|X     X| XXXXX |J|
X    X |X   X  |X  X   |XXX    |X  X   |X   X  |X    X |K|
X      |X      |X      |X      |X      |X      |XXXXXXX|L|
X     X|XX   XX|X X X X|X  X  X|X     X|X     X|X     X|M|
X     X|XX    X|X X   X|X  X  X|X   X X|X    XX|X     X|N|
XXXXXXX|X     X|X     X|X     X|X     X|X     X|XXXXXXX|O|
XXXXXX |X     X|X     X|XXXXXX |X      |X      |X      |P|
 XXXXX |X     X|X     X|X     X|X   X X|X    X | XXXX X|Q|
XXXXXX |X     X|X     X|XXXXXX |X   X  |X    X |X     X|R|
 XXXXX |X     X|X      | XXXXX |      X|X     X| XXXXX |S|
XXXXXXX|   X   |   X   |   X   |   X   |   X   |   X   |T|
X     X|X     X|X     X|X     X|X     X|X     X| XXXXX |U|
X     X|X     X|X     X|X     X| X   X |  X X  |   X   |V|
X     X|X  X  X|X  X  X|X  X  X|X  X  X|X  X  X| XX XX |W|
X     X| X   X |  X X  |   X   |  X X  | X   X |X     X|X|
X     X| X   X |  X X  |   X   |   X   |   X   |   X   |Y|
XXXXXXX|     X |    X  |   X   |  X    | X     |XXXXXXX|Z|
 XXXXX | X     | X     | X     | X     | X     | XXXXX |[|
X      | X     |  X    |   X   |    X  |     X |      X|\|
 XXXXX |     X |     X |     X |     X |     X | XXXXX |]|
   X   |  X X  | X   X |       |       |       |       |^|
       |       |       |       |       |       |XXXXXXX|_|
       |  XXX  |  XXX  |   X   |    X  |       |       |`|
       |   XX  |  X  X | X    X| XXXXXX| X    X| X    X|a|
       | XXXXX | X    X| XXXXX | X    X| X    X| XXXXX |b|
       |  XXXX | X    X| X     | X     | X    X|  XXXX |c|
       | XXXXX | X    X| X    X| X    X| X    X| XXXXX |d|
       | XXXXXX| X     | XXXXX | X     | X     | XXXXXX|e|
       | XXXXXX| X     | XXXXX | X     | X     | X     |f|
       |  XXXX | X    X| X     | X  XXX| X    X|  XXXX |g|
       | X    X| X    X| XXXXXX| X    X| X    X| X    X|h|
       |    X  |    X  |    X  |    X  |    X  |    X  |i|
       |      X|      X|      X|      X| X    X|  XXXX |j|
       | X    X| X   X | XXXX  | X  X  | X   X | X    X|k|
       | X     | X     | X     | X     | X     | XXXXXX|l|
       | X    X| XX  XX| X XX X| X    X| X    X| X    X|m|
       | X    X| XX   X| X X  X| X  X X| X   XX| X    X|n|
       |  XXXX | X    X| X    X| X    X| X    X|  XXXX |o|
       | XXXXX | X    X| X    X| XXXXX | X     | X     |p|
       |  XXXX | X    X| X    X| X  X X| X   X |  XXX X|q|
       | XXXXX | X    X| X    X| XXXXX | X   X | X    X|r|
       |  XXXX | X     |  XXXX |      X| X    X|  XXXX |s|
       |  XXXXX|    X  |    X  |    X  |    X  |    X  |t|
       | X    X| X    X| X    X| X    X| X    X|  XXXX |u|
       | X    X| X    X| X    X| X    X|  X  X |   XX  |v|
       | X    X| X    X| X    X| X XX X| XX  XX| X    X|w|
       | X    X|  X  X |   XX  |   XX  |  X  X | X    X|x|
       |  X   X|   X X |    X  |    X  |    X  |    X  |y|
       | XXXXXX|     X |    X  |   X   |  X    | XXXXXX|z|
  XXX  | X     | X     |XX     | X     | X     |  XXX  |{|
   X   |   X   |   X   |       |   X   |   X   |   X   |||
  XXX  |     X |     X |     XX|     X |     X |  XXX  |}|
 XX    |X  X  X|    XX |       |       |       |       |~|
    '''.splitlines()

    table = {}
    for form in letterforms:
        if '|' in form:
            table[form[-2]] = form[:-3].split('|')
    rows = len(list(table.values())[0])


    print("-" * 80)
    for row in range(rows):
        space = ' ' * 5
        text = '  '.join([table[c][row] for c in word])
        print(space, text.replace('X', '#'))

    print("-" * 80)
