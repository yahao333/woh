# -*- coding:utf-8 -*-
from __future__ import print_function

import sys, os, signal
from woh_py_actions.errors import FatalError

PYTHON = sys.executable

os.environ['PYTHON'] = PYTHON

PROG = os.getenv('WOH_PY_PROGRAM_NAME', 'woh.py')

def print_warning(message, stream=None):
    stream = stream or sys.stderr
    if not os.getenv('_WOH.PY_COMPLETE'):
        print(message, file=stream)

def signal_handler():
    # The Ctrl+C processed by other threads inside
    pass

def init_cli(verbose_output=None):
    # Click is imported here to run it after check_environment()
    import click

    class Deprecation(object):
        """Construct deprecation notice for help messages"""
        def __init__(self, deprecation=False):
            self.deprecation = deprecation

    class Task(object):
        def __init__(self):
            pass

    class Action(click.Command):
        def __init__(
            self,
            name=None,
            **kwargs):
            super(Action,self).__init__(name,**kwargs)

    class CLI(click.MultiCommand):
        def __init__(self, all_actions=None,verbose_output=None, help=None):
            super(CLI,self).__init__(
                chain=True,
                invoke_without_command=True,
                result_callback=self.execute_tasks,
                context_settings={'max_content_width': 140},
                help=help,
            )
            self._actions = {}

    @click.command(
        add_help_option=False,
        context_settings={
            'allow_extra_args':True,
            'ignore_unknown_options':True
        },
    )
    @click.option('-C', '--project-dir', default=os.getcwd(), type=click.Path())
    def parse_project_dir(project_dir):
        return realpath(project_dir)
    project_dir = parse_project_dir(standalone_mode=False,complete_var='_WOH.PY_COMPLETE_NOT_EXISTING')

    all_actions = {}
    woh_py_extensions_path = os.path.join(os.environ['WOH_PATH'], 'tools', 'woh_py_actions')
    extensions_dirs = [realpath(woh_py_extensions_path)]
    extra_paths = os.environ.get('WOH_EXTRA_ACTIONS_PATH')
    if extra_paths is not None:
        for path in extra_paths.split(';'):
            path = realpath(path)
            if path not in extensions_dirs:
                extensions_dirs.append(path)

    extensions = {}
    for directory in extensions_dirs:
        if directory and not os.path.exists(directory):
            print_warning('WARNING: Directory with woh.py extensions doesn\'t exist:\n    %s' % directory)
            continue

        sys.path.append(directory)

    cli_help = (
        'WOH CLI build management tool. '
        'For commands that are not known to woh.py an attempt to execute it as a build system target will be made.')

    return CLI(help=cli_help, verbose_output=verbose_output,all_actions=all_actions)


def check_environment():
    pass

def main():
    # Processing of Ctrl+C event for all threads made by main()
    signal.signal(signal.SIGINT, signal_handler)
    checks_output = check_environment()
    cli = init_cli(verbose_output=checks_output)
    # the argument `prog_name` must contain name of the file - not the absolute path to it!
    cli(sys.argv[1:], prog_name=PROG, complete_var='_WOH.PY_COMPLETE')


if __name__ == '__main__':
    try:
        main()
    except FatalError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
