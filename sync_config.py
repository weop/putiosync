"""
put.io sync config file

the config is imported into the sync script and consumed
as a python module, therefore you can configure keys with
python code.
"""

import os

# this is the dir on the local filesystem that will be synchronized
# with the put.io account
# ~/PutIO
LOCAL_MIRROR_ROOT = os.path.join(os.path.expanduser('~'), 'PutIO')

# is the oauth token encrypted in armor format then base64 encoded
OAUTH_TOKEN_SYMMETRIC_ARMOR_BASE64 = False

# This is the oauth token generated with the permission of the user
# (you most likely as the consumer of this script)
OAUTH_TOKEN = 'XXXXXX'

# how many files to download in parallel
PARALLEL_DOWNLOADS = 1

# for each download how many connections to employ
CONNECTIONS_PER_DOWNLOAD = 10

# maximum download speed ( mb * 1024 * 1024) by default
MAX_DOWNLOAD_SPEED_BYTES_PER_SECOND = 2 * 1024 * 1024

# put here names of dirs in the putio account that you dont want synced
# possible values:
# 1. absolute paths prefixed by two forward slashes e.g. //movies/spiderman.mkv
# 2. python regular expression, e.g. *.txt, somefile
#
EXCLUDE_LIST = ['//unsorted']
# or as list...
# EXCLUDE_LIST = ['//unsorted','//random']
