"""
this module is composed solely of constants and methods that are related to
exiting the process
"""

import sys
from sync_logging import LOG

__CODE_BAD_CONFIG = 1
__GPG_NOT_INSTALLED = 2
__GPG_CALL_ERROR = 3
__INTERRUPTED = 4
__ROOT_MIRROR_CANT_BE_SYNCED = 5
__INVALID_OAUTH_TOKEN = 6


def exit_bad_config():
    """exits the process with __CODE_BAD_CONFIG
    :returns: None

    """
    LOG.error('config file is missing essential app info', exc_info=True)
    print 'config file is missing put.io application info, cant proceed.'
    sys.exit(__CODE_BAD_CONFIG)


def gpg_not_installed():
    """exits the process with __GPG_NOT_INSTALLED
    :returns: None

    """
    LOG.error('gpg execution failed: probably doesnt exist', exc_info=True)
    print 'seems like gpg isnt installed'
    sys.exit(__GPG_NOT_INSTALLED)


def gpg_call_error(message):
    """exits the process with __GPG_CALL_ERROR
    :returns: None

    """
    LOG.error('gpg returned with error, perhaps wrong passphrase? %s', message)
    print message
    sys.exit(__GPG_CALL_ERROR)


def exit_interrupted():
    """exits the process with __INTERRUPTED
    :returns: None

    """
    LOG.error('interrupted by user', exc_info=True)
    print 'interrupted, exiting.'
    sys.exit(__INTERRUPTED)


def exit_cant_sync_locally(localdir):
    """exits the process with __ROOT_MIRROR_CANT_BE_SYNCED
    :returns: None

    """
    LOG.error('local root cant be synced: %s', localdir)
    print 'cant sync into %s' % localdir
    sys.exit(__ROOT_MIRROR_CANT_BE_SYNCED)


def exit_invalid_oauth_token():
    """exits the process with __INVALID_OAUTH_TOKEN
    :returns: None

    """
    LOG.error('invalid oauth token')
    print 'invalid oauth token, please check your configuration.'
    sys.exit(__INVALID_OAUTH_TOKEN)
