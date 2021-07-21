import subprocess, sys

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
            'git', '--tags'
        ]).decode('utf-8', 'ignore').strip()
    except (subprocess.CalledProcessError, UnicodeError):
        sys.stderr.write('WARNING: git version unavailable')

    return version
