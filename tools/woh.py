#!/usr/bin/env python
# -*- coding:utf-8 -*-
from __future__ import print_function

import os
import signal
import subprocess
import sys
import os.path
from collections import Counter, OrderedDict
from importlib import import_module
from pkgutil import iter_modules

from woh_py_actions.errors import FatalError
from woh_py_actions.tools import realpath, woh_version, executable_exists, merge_action_lists

PYTHON = sys.executable

os.environ['PYTHON'] = PYTHON

PROG = os.getenv('WOH_PY_PROGRAM_NAME', 'woh.py')


def print_warning(message, stream=None):
    stream = stream or sys.stderr
    if not os.getenv('_WOH.PY_COMPLETE'):
        print(message, file=stream)


def check_environment():
    """
    Verify the environment contains the top-level tools we need to operate
    """
    checks_output = []
    if not executable_exists(['make', '--version']):
        debug_print_woh_version()
        raise FatalError("'make' must be available on the PATH to use %s" % PROG)

    # verify that WOH_PATH env variable is set
    # find the directory woh.py is in, then the parent directory of this, and assume this is WOH_PATH
    detected_woh_path = realpath(os.path.join(os.path.dirname(__file__), '..'))
    if 'WOH_PATH' in os.environ:
        set_woh_path = realpath(os.environ['WOH_PATH'])
        if set_woh_path != detected_woh_path:
            print_warning(
                'WARNING: WOH_PATH environment variable is set to %s but %s path indicates WOH directory %s. '
                'Using the environment variable directory, but results may be unexpected...' %
                (set_woh_path, PROG, detected_woh_path))
    else:
        print_warning('Setting WOH_PATH environment variable: %s' % detected_woh_path)
        os.environ['WOH_PATH'] = detected_woh_path

    checks_output.append('Checking Python dependencies...')
    try:
        out = subprocess.check_output(
            [
                os.environ['PYTHON'],
                os.path.join(os.environ['WOH_PATH'], 'tools', 'check_python_dependencies.py'),
            ],
            env=os.environ,
        )

        checks_output.append(out.decode('utf-8', 'ignore').strip())
    except subprocess.CalledProcessError as e:
        print_warning(e.output.decode('utf-8', 'ignore'), stream=sys.stderr)
        debug_print_woh_version()
        raise SystemExit(1)

    return checks_output


def debug_print_woh_version():
    version = woh_version()
    if version:
        print_warning('WOH %s' % version)
    else:
        print_warning('WOH version unknown')


def signal_handler():
    # The Ctrl+C processed by other threads inside
    pass


class PropertyDict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("'PropertyDict' object has no attribute '%s'" % name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("'PropertyDict' object has no attribute '%s'" % name)


def init_cli(verbose_output=None):
    # Click is imported here to run it after check_environment()
    import click

    def check_deprecation(ctx):
        """Prints deprecation warnings for arguments in given context"""
        for option in ctx.command.params:
            default = () if option.multiple else option.default
            if isinstance(option, Option) and option.deprecated and ctx.params[option.name] != default:
                deprecation = Deprecation(option.deprecated)
                if deprecation.exit_with_error:
                    raise FatalError('Error: %s' % deprecation.full_message('Option "%s"' % option.name))
                else:
                    print_warning('Warning: %s' % deprecation.full_message('Option "%s"' % option.name))

    class Deprecation(object):
        """Construct deprecation notice for help messages"""

        def __init__(self, deprecation=False):
            self.deprecation = deprecation

    class Task(object):
        def __init__(self, callback, name, aliases, dependencies, order_dependencies, action_args):
            self.callback = callback
            self.name = name
            self.dependencies = dependencies
            self.order_dependencies = order_dependencies
            self.action_args = action_args
            self.aliases = aliases

        def __call__(self, context, global_args, action_args=None):
            if action_args is None:
                action_args = self.action_args

            self.callback(self.name, context, global_args, **action_args)

    class Scope(object):
        SCOPES = ('default', 'global', 'shared')

        def __init__(self, scope=None):
            if scope is None:
                self._scope = 'default'
            elif isinstance(scope, str) and scope in self.SCOPES:
                self._scope = scope
            elif isinstance(scope, Scope):
                self._scope = str(scope)
            else:
                raise FatalError('Unknown scope for option: %s' % scope)

        @property
        def is_global(self):
            return self._scope == 'global'

        @property
        def is_shared(self):
            return self._scope == 'shared'

        def __str__(self):
            return self._scope

    class Action(click.Command):
        def __init__(
                self,
                name=None,
                aliases=None,
                deprecated=False,
                dependencies=None,
                order_dependencies=None,
                hidden=False,
                **kwargs):
            super(Action, self).__init__(name, **kwargs)

            self.name = self.name or self.callback.__name__
            self.deprecated = deprecated
            self.hidden = hidden

            if aliases is None:
                aliases = []
            self.aliases = aliases

            self.help = self.help or self.callback.__doc__
            if self.help is None:
                self.help = ''

            if dependencies is None:
                dependencies = []

            if order_dependencies is None:
                order_dependencies = []

            # Show first line of help if short help is missing
            self.short_help = self.short_help or self.help.split('\n')[0]

            if deprecated:
                deprecation = Deprecation(deprecated)
                # self.short_help = deprecation.sho

            if aliases:
                aliases_help = 'Aliases: %s.' % ', '.join(aliases)

                self.help = '\n'.join([self.help, aliases_help])
                self.short_help = ' '.join([aliases_help, self.short_help])

            self.unwrapped_callback = self.callback
            if self.callback is not None:
                def wrapped_callback(**action_args):
                    return Task(
                        callback=self.unwrapped_callback,
                        name=self.name,
                        dependencies=dependencies,
                        order_dependencies=order_dependencies,
                        action_args=action_args,
                        aliases=self.aliases,
                    )
                self.callback = wrapped_callback

        def invoke(self, ctx):
            if self.deprecated:
                print('invoke deprecated')

            # Print warnings for options
            check_deprecation(ctx)
            return super(Action, self).invoke(ctx)

    class Argument(click.Argument):
        def __init__(self, **kwargs):
            names = kwargs.pop('names')
            super(Argument, self).__init__(names, **kwargs)

    class Option(click.Option):
        """Option that knows whether it should be global"""

        def __init__(self, scope=None, deprecated=False, hidden=False, **kwargs):
            """Keyword arguments additional to Click's Option class:"""
            kwargs['param_decls'] = kwargs.pop('names')
            super(Option, self).__init__(**kwargs)

            self.deprecated = deprecated
            self.scope = Scope(scope)
            self.hidden = hidden

            if deprecated:
                deprecation = Deprecation(deprecated)
                self.help = deprecation.help(self.help)

        def get_help_record(self, ctx):
            if self.hidden:
                return

            return super(Option, self).get_help_record(ctx)

    class CLI(click.MultiCommand):
        """Action list contains all actions with options available for CLI"""

        def __init__(self, all_actions=None, verbose_output=None, help=None):
            super(CLI, self).__init__(
                chain=True,
                invoke_without_command=True,
                result_callback=self.execute_tasks,
                context_settings={'max_content_width': 140},
                help=help,
            )
            self._actions = {}
            self.global_action_callback = []
            self.commands_with_aliases = {}

            if verbose_output is None:
                verbose_output = []

            self.verbose_output = verbose_output

            if all_actions is None:
                all_actions = {}

            shared_options = []

            # Global options
            for option_args in all_actions.get('global_options', []):
                option = Option(**option_args)
                self.params.append(option)

            # Global options validators
            self.global_action_callbacks = all_actions.get('global_action_callbacks', [])

            # Actions
            for name, action in all_actions.get('actions', {}).items():
                arguments = action.pop('arguments', [])
                options = action.pop('options', [])

                if arguments is None:
                    arguments = []

                if options is None:
                    options = []

                self._actions[name] = Action(name=name, **action)
                for alias in [name] + action.get('aliases', []):
                    self.commands_with_aliases[alias] = name

                for argument_args in arguments:
                    self._actions[name].params.append(Argument(**argument_args))

                for option in shared_options:
                    self._actions[name].params.append(option)

                for option_args in options:
                    option = Option(**option_args)

                    if option.scope.is_shared:
                        raise FatalError(
                            '"%s" is defined for action "%s". '
                            ' "shared" options can be declared only on global level' % (option.name, name)
                        )

                    if option.scope.is_global and option.name not in [o.name for o in self.params]:
                        self.params.append(option)

                    self._actions[name].params.append(option)

        def list_commands(self, ctx):
            return sorted(filter(lambda name: not self._actions[name].hidden, self._actions))

        def get_command(self, ctx, name):
            if name in self.commands_with_aliases:
                return self._actions.get(self.commands_with_aliases.get(name))

            # Trying fallback to build target (from "all" action) if command is not known
            else:
                return Action(name=name, callback=self._actions.get('fallback').unwrapped_callback)

        def _print_closing_message(self, args, actions):
            if any(t in str(actions) for t in ('flash', 'dfu')):
                print('Done')
                return

            # Otherwise, if we built any binaries print a message about
            def print_flashing_message(title, key):
                print('\n%s build complete. To flash, run this command:' % title)

            if 'all' in actions or 'build' in actions:
                print_flashing_message('Project', 'project')
            else:
                if 'app' in actions:
                    print_flashing_message('App', 'app')

        def execute_tasks(self, tasks, **kwargs):
            ctx = click.get_current_context()
            global_args = PropertyDict(kwargs)

            def _help_and_exit():
                print(ctx.get_help())
                ctx.exit()

            dupplicated_tasks = sorted(
                [item for item, count in Counter(task.name for task in tasks).items() if count > 1])

            if dupplicated_tasks:
                dupes = ', '.join('"%s"' % t for t in dupplicated_tasks)
                print_warning(
                    'WARNING: Command%s found in the list of commands more than once. ' %
                    ('s %s are' % dupes if len(dupplicated_tasks) > 1 else ' %s is' % dupes) +
                    'Only first occurrence will be executed.')

            for task in tasks:
                if task.name == 'help':
                    _help_and_exit()

                for key in list(task.action_args):
                    option = next((o for o in ctx.command.params if o.name == key), None)

                    if option and (option.scope.is_global or option.scope.is_shared):
                        pass

            check_deprecation(ctx)

            # Make sure that define_cache_entry is mutable list and can be modified in callbacks
            # global_args.define_cache_entry = list(global_args.define_cache_entry)

            # Execute all global action callback
            for action_callback in ctx.command.global_action_callbacks:
                action_callback(ctx, global_args, tasks)

            if not tasks:
                _help_and_exit()

            tasks_to_run = OrderedDict()

            while tasks:
                task = tasks[0]
                tasks_dict = dict([(t.name, t) for t in tasks])

                dependecies_processed = True

                # If task have some dependecies they have to be executed before the task.
                for dep in task.dependencies:
                    if dep not in tasks_to_run.keys():
                        if dep in tasks_dict.keys():
                            dep_task = tasks.pop(tasks.index(tasks_dict[dep]))
                        else:
                            print(
                                'Adding "%s"\'s dependency "%s" to list of commands with default set of options.' %
                                (task.name, dep)
                            )
                            dep_task = ctx.invoke(ctx.command.get_command(ctx, dep))

                        tasks.insert(0, dep_task)
                        dependecies_processed = False

                for dep in task.order_dependencies:
                    if dep in tasks_dict.keys() and dep not in tasks_to_run.keys():
                        tasks.insert(0, tasks.pop(tasks.index(tasks_dict[dep])))
                        dependecies_processed = False

                if dependecies_processed:
                    # Remove task from list of unprocessed tasks
                    tasks.pop(0)

                    # And add to the queue
                    if task.name not in tasks_to_run.keys():
                        tasks_to_run.update([(task.name, task)])

            if not global_args.dry_run:
                for task in tasks_to_run.values():
                    name_with_aliases = task.name
                    if task.aliases:
                        name_with_aliases += ' (aliases: %s)' % ', '.join(task.aliases)

                    print('Executing action: %s' % name_with_aliases)
                    task(ctx, global_args, task.action_args)

                self._print_closing_message(global_args, tasks_to_run.keys())

            return tasks_to_run

    @click.command(
        add_help_option=False,
        context_settings={
            'allow_extra_args': True,
            'ignore_unknown_options': True
        },
    )
    @click.option('-C', '--project-dir', default=os.getcwd(), type=click.Path())
    def parse_project_dir(project_dir):
        return realpath(project_dir)

    # Set `complete_var` to not existing environment variable name to prevent early cmd completion
    project_dir = parse_project_dir(standalone_mode=False, complete_var='_WOH.PY_COMPLETE_NOT_EXISTING')

    all_actions = {}
    # Load extensions from components dir
    woh_py_extensions_path = os.path.join(os.environ['WOH_PATH'], 'tools', 'woh_py_actions')
    extensions_dirs = [realpath(woh_py_extensions_path)]
    extra_paths = os.environ.get('WOH_EXTRA_ACTIONS_PATH')
    if extra_paths is not None:
        for path in extra_paths.split(';'):
            path = realpath(path)
            if path not in extensions_dirs:
                extensions_dirs.append(path)

    extensions = []
    for directory in extensions_dirs:
        if directory and not os.path.exists(directory):
            print_warning('WARNING: Directory with woh.py extensions doesn\'t exist:\n    %s' % directory)
            continue

        sys.path.append(directory)
        for _finder, name, _ispkg in sorted(iter_modules([directory])):
            if name.endswith('_ext'):
                extensions.append((name, import_module(name)))

    for name, extension in extensions:
        try:
            all_actions = merge_action_lists(all_actions, extension.action_extensions(all_actions, project_dir))
        except AttributeError:
            print_warning('WARNING: Cannot load woh.py extension "%s"' % name)

    # Load extensions from project dir
    if os.path.exists(os.path.join(project_dir, 'woh_ext.py')):
        sys.path.append(project_dir)

    cli_help = (
        'WOH CLI build management tool. '
        'For commands that are not known to woh.py an attempt to execute it as a build system target will be made.')

    return CLI(help=cli_help, verbose_output=verbose_output, all_actions=all_actions)


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
