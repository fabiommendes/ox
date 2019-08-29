import logging
import os
from logging import getLogger

log = getLogger('ox')
logging.basicConfig(format='[ox] %(message)s')


def has_env(varname, value='true'):
    """
    Check environment variable is set.
    """
    return os.environ.get(varname, '').lower() == value


if has_env('DEBUG'):
    log.setLevel(logging.DEBUG)
elif has_env('OX_LOG', 'debug'):
    log.setLevel(logging.DEBUG)
elif has_env('OX_LOG', 'info'):
    log.setLevel('INFO')
elif has_env('OX_LOG', 'warning'):
    log.setLevel(logging.WARNING)
elif has_env('OX_LOG', 'error'):
    log.setLevel(logging.ERROR)
else:
    log.setLevel(logging.CRITICAL)
