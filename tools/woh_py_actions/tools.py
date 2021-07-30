import os
import subprocess
import sys

from .constants import GENERATORS
from .errors import FatalError


def executable_exists(args):
    try:
        subprocess.check_output(args)
        return True

    except Exception:
        return False


def realpath(path):
    return os.path.normcase(os.path.realpath(path))


def _woh_version_from_ide():
    return ""


def woh_version():
    try:
        version = subprocess.check_output([
            'git',
            '--git-dir=%s' % os.path.join(os.environ['WOH_PATH'], '.git'),
            '--work-tree=%s' % os.environ['WOH_PATH'],
            'describe', '--tags', '--dirty', '--match', 'v*.*',
        ]).decode('utf-8', 'ignore').strip()
    except (subprocess.CalledProcessError, UnicodeError):
        sys.stderr.write('WARNING: git version unavailable')

    return version


def _detect_make_generator(prog_name):
    for (generator_name, generator) in GENERATORS.items():
        if executable_exists(generator['version']):
            return generator_name
    raise FatalError("To use %s, either the 'ninja' or 'GNU make' build tool must be available in the PATH" % prog_name)


def ensure_build_directory(args, prog_name, always_run_make=False):
    """Check the build directory exists and that make has been run there."""
    project_dir = args.project_dir
    # Verify the project directory
    if not os.path.isdir(project_dir):
        if not os.path.exists(project_dir):
            raise FatalError('Project directory %s does not exist' % project_dir)
        else:
            raise FatalError('%s must be a project directory' % project_dir)
    if not os.path.exists(os.path.join(project_dir, "Makefile")):
        raise FatalError('Makefile not found in project directory %s' % project_dir)

    # Verify/create the build directory
    build_dir = args.build_dir
    if not os.path.isdir(build_dir):
        os.makedirs(build_dir)

    # args.define_cache_entry.append('CCACHE_ENABLE=%d' % args.ccache)
    generator = _detect_make_generator(prog_name)
    if args.generator is None:
        args.generator = generator
    if generator != args.generator:
        raise FatalError("Build is configured for generator '%s' not '%s'. Run '%s fullclean' to start again." %
                         (generator, args.generator, prog_name))

def merge_action_lists(*action_lists):
    merged_actions = {
        'global_options': [],
        'actions': {},
        'global_action_callbacks': [],
    }
    for action_list in action_lists:
        merged_actions['global_options'].extend(action_list.get('global_options', []))
        merged_actions['actions'].update(action_list.get('actions', {}))
        merged_actions['global_action_callbacks'].extend(action_list.get('global_action_callbacks', []))
    return merged_actions



def run_tool(tool_name, args, cwd, env=dict()):
    def quote_arg(arg):
        " Quote 'arg' if necessary "
        if ' ' in arg and not (arg.startswith('"') or arg.startswith("'")):
            return "'" + arg + "'"
        return arg

    args = [str(arg) for arg in args]
    display_args = ' '.join(quote_arg(arg) for arg in args)
    print('Running %s in directory %s' % (tool_name, quote_arg(cwd)))
    print('Executing "%s"...' % str(display_args))

    env_copy = dict(os.environ)
    env_copy.update(env)

    if sys.version_info[0] < 3:
        for (key, val) in env_copy.items():
            if not isinstance(val, str):
                env_copy[key] = val.encode(sys.getfilesystemencoding() or 'utf-8')

    try:
        subprocess.check_output(args, env=env_copy, cwd=cwd)
    except subprocess.CalledProcessError as e:
        raise FatalError('%s failed with exit code %d' % (tool_name, e.returncode))


def run_target(target_name, args, env=dict()):
    generator_cmd = GENERATORS[args.generator]['command']

    if args.verbose:
        generator_cmd += [GENERATORS[args.generator]['verbose_flag']]
    run_tool(generator_cmd[0], generator_cmd + [target_name], args.build_dir, env)