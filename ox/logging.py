import os
from logging import getLogger
import logging

log = getLogger('ox')
logging.basicConfig(format='%(message)s')
has_env = (lambda x, value='true': os.environ.get(x, '').lower() == value)

if has_env('DEBUG'):
    log.setLevel(logging.DEBUG)
elif has_env('OX_LOG', 'debug'):
    log.setLevel(logging.DEBUG)
elif has_env(logging.INFO):
    log.setLevel('INFO')
elif has_env('OX_LOG', 'warning'):
    log.setLevel(logging.WARNING)
elif has_env('OX_LOG', 'error'):
    log.setLevel(logging.ERROR)
else:
    log.setLevel(logging.CRITICAL)
