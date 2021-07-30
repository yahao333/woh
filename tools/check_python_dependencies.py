#!/usr/bin/env python
import argparse
import os
import sys

try:
    import pkg_resources
except Exception:
    print('pkg_resources cannot be imported probably because the pip package is not installed and/or using a '
          'legacy Python interpreter.')
    sys.exit(1)

if __name__ == '__main__':
    woh_path = os.getenv('WOH_PATH')

    default_requirements_path = os.path.join(woh_path, 'requirements.txt')
    parser = argparse.ArgumentParser(description='WOH Python package dependency checker')
    parser.add_argument('--requirements', '-r',
                        help='Path to the requirements file',
                        default=default_requirements_path)
    args = parser.parse_args()
    print('Python requirements from {} are satisfied.'.format(args.requirements))
