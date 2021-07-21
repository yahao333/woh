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
        def __init__(self):
            pass

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
