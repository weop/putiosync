#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Syncs your put.io dir tree to a target dir on your file system.
It will download directories with contained files and delete
directories and files that no longer exist.
"""

import os
import re
from sync_logging import LOG
from sync_config import OAUTH_TOKEN_SYMMETRIC_ARMOR_BASE64
from sync_config import OAUTH_TOKEN
from sync_config import PARALLEL_DOWNLOADS
from sync_config import CONNECTIONS_PER_DOWNLOAD
from sync_config import LOCAL_MIRROR_ROOT
from sync_config import MAX_DOWNLOAD_SPEED_BYTES_PER_SECOND
from sync_config import EXCLUDE_LIST
import exit_helper
import sync_utils
import putio_api
import commands

PUTIO_DIR_FTP = 0
# can be ebooks like .epub or .mobi
PUTIO_DATA_FTP = 1
PUTIO_AUDIO_FTP = 2
PUTIO_VIDEO_FTP = 3
PUTIO_IMAGE_FTP = 4
PUTIO_ARCHIVE_FTP = 5
PUTIO_PDF_FTP = 6
PUTIO_TEXT_FTP = 8


def __sync_account(conf):
    """perfoms the putio sync action

    :conf: configuration object
    :returns: None

    """
    print '\n------------------'
    print '\n...Sync started...'
    print '\n------------------'
    localdir = conf.get('localdir')
    if os.path.exists(localdir) and not os.path.isdir(localdir):
        exit_helper.exit_cant_sync_locally(localdir)
    if not os.path.exists(localdir):
        os.makedirs(localdir)

    putio_dirtree = {}
    while True:
        try:
            sync_utils.suspend_until_can_store_all(conf)
            LOG.info('sync loop iteration started')
            files_to_dirs = {}
            putio_dirtree = __get_putio_files(conf, 0, putio_dirtree)
            __create_local_dirs(
                conf.get('localdir'),
                putio_dirtree,
                files_to_dirs)

            for remoteitem, targetdir in files_to_dirs.iteritems():
                fileid = remoteitem.itemid
                filesize = remoteitem.size
                download_url = putio_api.get_download_url(conf, fileid)
                if download_url:
                    sync_utils.start_download(
                        filesize,
                        download_url,
                        targetdir,
                        conf)

        except Exception:
            LOG.error('sync iteration failed', exc_info=True)

        timenow = __gettimenow()
        print '\n%s :. waiting...' % timenow
        
        sync_utils.suspend_sync()


def __create_local_dirs(root, dirtree, files_to_dirs):
    """creates the local dir tree

    :conf: configuration object
    :dirtree: the tree fetched from the putio account
    :files_to_dirs: a mapping of file data to the dir the file should
            be downloaded to
    :returns: None

    """

    todelete = os.listdir(root)

    for name, remoteitem in dirtree.iteritems():
        if name in todelete:
            todelete.remove(name)

        if remoteitem is None:
            print ('Skipping dir %s because no data for it', name)
            LOG.error('skipping dir %s because no data for it', name)
            continue

        target = os.path.join(root, name)
        if remoteitem.isdir():
            LOG.debug('inspecting dir: %s', name)
            # this is a directory
            if os.path.exists(target) and not os.path.isdir(target):
                LOG.warn(
                    "remote dir and local file conflict" +
                    "removing local file: %s",
                    target)
                os.remove(target)

            if not os.path.exists(target):
                LOG.debug('creating dir: %s', target)
                os.makedirs(target)

            if remoteitem.dirtree:
                __create_local_dirs(target, remoteitem.dirtree, files_to_dirs)
            elif os.path.exists(target):
                todelete.append(name)

        else:
            LOG.debug('inspecting file: %s', name)
            # this is a normal file
            exists = os.path.exists(target)
            if exists and os.path.getsize(target) != remoteitem.size:
                LOG.warn('file size != from whats on putio: %s', target)
                todelete.append(name)
                files_to_dirs[remoteitem] = target
            elif not exists:
                LOG.debug(
                    'file will be downloaded: %s -> %s',
                    remoteitem,
                    target)
                files_to_dirs[remoteitem] = target

    sync_utils.delete_files(root, todelete)


def __get_putio_files(conf, parent_id=0, tree=None, root=None):
    """fetches the file list from put.io account

    :conf: configuration object
    :parent_id: the from which to start on the account
    :returns: a dict of dicts representing the account directory tree
    """
    if not tree:
        tree = {}

    if not root:
        root = '/'

    data = putio_api.getfiles(conf, parent_id)
    putio_api.ensure_valid_oauth_token(data)
    freshtree = {}
    if data:
        LOG.debug('got data for file id: %d', parent_id)
        for remotefile in data.get('files'):
            filename = remotefile.get('name')
            filetype = remotefile.get('file_type')
            fileid = remotefile.get('id')
            filesize = remotefile.get('size')
            abspath = root + '/' + filename

            skip = False
            for exclude in EXCLUDE_LIST:
                skip = abspath == exclude or re.search(exclude, abspath)
                if skip:
                    LOG.info('skipping because exclude rule match (%s ~ %s)',
                             exclude, abspath)
                    break
            if skip:
                continue

            if filetype == PUTIO_DIR_FTP:
                cached = tree.get(filename, None)
                cached_filesize = cached.size if cached else 0
                if cached:
                    freshtree[filename] = cached

                if filesize != cached_filesize:
                    subtree = cached.dirtree if cached else {}
                    subtree = __get_putio_files(conf, fileid, subtree, abspath)
                    freshtree[filename] = RemoteItem(
                        filename, filesize, fileid, subtree)
                    LOG.debug('mapped directory: %s', freshtree[filename])

            else:
                filedata = RemoteItem(filename, filesize, fileid, None)
                LOG.debug('mapped file: %s', filedata)
                freshtree[filename] = filedata

        tree = freshtree

    return tree


class RemoteItem(object):

    """A remote dir or file"""

    def __init__(self, name, size, itemid, dirtree):
        """constructor"""
        self.name = name
        self.size = size
        self.itemid = itemid
        self.dirtree = dirtree

    def isdir(self):
        """is this item a directory?"""
        return self.dirtree is not None

    def __str__(self):
        """tostring"""
        itemtype = 'Directory' if self.isdir() else 'File'
        return "%s('%s', size=%d, id=%d)" % (
            itemtype, self.name, self.size, self.itemid)

    def __repr(self):
        """representation"""
        return self.__str__()


def __getconfig():
    """creates a config object used later in the script
    :returns: dictionary with the config

    """
    if not OAUTH_TOKEN:
        exit_helper.exit_bad_config()

    oauthtoken = OAUTH_TOKEN
    if OAUTH_TOKEN_SYMMETRIC_ARMOR_BASE64:
        LOG.info('app info is encrypted, prompting gpg passphrase')
        print 'app info is encrypted, running gpg to decrypt'
        oauthtoken = sync_utils.gpgdecode(oauthtoken)

    oauthtoken = oauthtoken.strip('\n ')

    return dict(oauthtoken=oauthtoken,
                parallel_downloads=PARALLEL_DOWNLOADS,
                conn_per_downloads=CONNECTIONS_PER_DOWNLOAD,
                localdir=LOCAL_MIRROR_ROOT,
                bytes_per_second=MAX_DOWNLOAD_SPEED_BYTES_PER_SECOND)

def __gettimenow():
    try:
        time = commands.getstatusoutput(''' echo $(date +"%F %I:%M:%S") ''')
        return time[1]
    except KeyboardInterrupt:
        exit_helper.exit_interrupted()

def __readargs():
    try:
        conf = __getconfig()
        LOG.info('starting sync in home dir: %s', conf.get('localdir'))
        print '\n------------------'
        print "... PutIO/Sync ..."
        print '\n------------------'
        print "Minimum Reserved: \t%i" % sync_utils.min_space_to_reserve()
        print "Available Disk Space: \t%i" % sync_utils.total_free_space()
        print "Local Sync Dir: \t"+conf.get('localdir')
        __sync_account(conf)
    except KeyboardInterrupt:
        exit_helper.exit_interrupted()


if __name__ == '__main__':
    __readargs()
