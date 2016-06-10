"""
this module is imported by the main script to get logging setup
"""

import logging

__LOGFILE = './putio_sync.log'
__LEVEL = 'DEBUG'
__FORMAT = '%(asctime)s - [%(levelname)s] %(funcName)s: %(message)s'
logging.basicConfig(format=__FORMAT, filename=__LOGFILE, level=__LEVEL)
LOG = logging.getLogger()
