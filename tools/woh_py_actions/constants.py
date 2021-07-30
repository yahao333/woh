import collections
import multiprocessing

MAKE_CMD = 'make'
MAKE_GENERATOR = 'Unix Makefiles'

GENERATORS = collections.OrderedDict([
    # - command: build command line
    # - version: version command line
    # - verbose_flag: verbose flag
    (MAKE_GENERATOR, {
        'command': [MAKE_CMD, '-j', str(multiprocessing.cpu_count() + 2)],
        'version': [MAKE_CMD, '--version'],
        'dry_run': [MAKE_CMD, '-n'],
        'verbose_flag': 'VERBOSE=1',
    })
])

SUPPORTED_TARGETS = ['default', 'openwrt_6ul']
PREVIEW_TARGETS = ['linux']
