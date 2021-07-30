import os
import subprocess
import sys

import click


from woh_py_actions.tools import (ensure_build_directory, woh_version, merge_action_lists, realpath, run_target)
from woh_py_actions.errors import FatalError
from woh_py_actions.constants import GENERATORS
from woh_py_actions.global_options import global_options

def action_extensions(base_action, project_path):
    def build_target(target_name, ctx, args):
        """Execute the target build system to build target 'target_name'"""
        ensure_build_directory(args, ctx.info_name)
        run_target(target_name, args)

    def set_target(action, ctx, args, idf_target):
        # args.define_cache_entry.append('IDF_TARGET=' + idf_target)
        pass

    def fallback_target(target_name, ctx, args):
        """Execute targets that are not explicitly known to woh.py"""
        ensure_build_directory(args, ctx.info_name)

        try:
            subprocess.check_output(GENERATORS[args.generator]['dry_run'] + [target_name], cwd=args.build_dir)

        except Exception:
            raise FatalError(
                'command "%s" is not known to idf.py and is not a %s target' % (target_name, args.generator))

        run_target(target_name, args)

    def clean(action, ctx, args):
        if not os.path.isdir(args.build_dir):
            print("Build directory '%s' not found. Nothing to clean." % args.build_dir)
            return
        build_target('clean', ctx, args)

    def woh_version_callback(ctx, param, value):
        if not value or ctx.resilient_parsing:
            return

        version = woh_version()

        if not version:
            raise FatalError('version cannot be determined')

        print('WOH %s' % version)
        sys.exit(0)

    def verbose_callback(ctx, param, value):
        if not value or ctx.resilient_parsing:
            return

        for line in ctx.command.verbose_output:
            print(line)

        return value

    def validate_root_options(ctx, args, tasks):
        args.project_dir = realpath(args.project_dir)
        if args.build_dir is not None and args.project_dir == realpath(args.build_dir):
            raise FatalError(
                'Setting the build directory to the project directory is not supported. Suggest dropping '
                "--build-dir option, the default is a 'build' subdirectory inside the project directory.")
        if args.build_dir is None:
            args.build_dir = os.path.join(args.project_dir, './')
        args.build_dir = realpath(args.build_dir)

    root_options = {
        'global_options': [
            {
                'names': ['--version'],
                'help': 'Show version',
                'is_flag': True,
                'expose_value': False,
                'callback': woh_version_callback,
            },
            {
                'names': ['-C', '--project-dir'],
                'scope': 'shared',
                'help': 'Project directory.',
                'type': click.Path(),
                'default': os.getcwd(),
            },
            {
                'names': ['-B', '--build-dir'],
                'help': 'Build directory.',
                'type': click.Path(),
                'default': None,
            },
            {
                'names': ['-G', '--generator'],
                'help': 'CMake generator.',
                'type': click.Choice(GENERATORS.keys()),
            },
            {
                'names': ['-v', '--verbose'],
                'help': 'Verbose build output.',
                'is_flag': True,
                'is_eager': True,
                'default': False,
                'callback': verbose_callback,
            },
            {
                'names': ['--dry-run'],
                'help': "Only process arguments, but don't execute actions.",
                'is_flag': True,
                'hidden': True,
                'default': False,
            },
        ],
        'global_action_callbacks': [validate_root_options],
    }

    build_actions = {
        'actions': {
            'all': {
                'aliases': ['build'],
                'callback': build_target,
                'short_help': 'Build the woh project',
                'help': (
                    'Build the woh project.'
                ),
                # 'options': global_options,
                'order_dependencies': [
                    'reconfigure',
                    'clean',
                    'fullclean',
                ],
            }
        }
    }

    clean_actions = {
        'actions': {
            'clean': {
                'callback': clean,
                'short_help': 'Delete the entire build directory contents.',
                'help': (
                    'Delete the entire build directory contents.'
                )
            },
        },
    }

    return merge_action_lists(root_options, build_actions, clean_actions)