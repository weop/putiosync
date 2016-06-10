"""static methods to help the sync process"""

import time
import os
import shutil
from base64 import b64decode
import subprocess
from subprocess import PIPE
import binascii
import putio_api
from sync_logging import LOG
import exit_helper


def gpgdecode(string):
    """decodes a base64 and symmetric cipher"""
    string = b64decode(string)
    echo = subprocess.Popen(['echo', string], stdout=PIPE)
    try:
        return subprocess.check_output(
            ['gpg', '--decrypt'], stdin=echo.stdout)
    except OSError:
        exit_helper.gpg_not_installed()
    except subprocess.CalledProcessError as exc:
        exit_helper.gpg_call_error('gpg error code %d' % exc.returncode)


def suspend_sync():
    """simple sleep helper"""
    sleep_seconds = 60 * 1
    LOG.debug('sleeping for %d seconds', sleep_seconds)
    time.sleep(sleep_seconds)


def total_free_space():
    """total free bytes in the disk"""
    root = os.statvfs('/')
    return root.f_bavail * root.f_frsize


def total_disk_size():
    """total bytes in the disk"""
    root = os.statvfs('/')
    return root.f_blocks * root.f_frsize


def min_space_to_reserve():
    """minimum space on the filesystem after the sync"""
    return total_disk_size() * 0.1


def putio_root_size(conf):
    """total space occupied by the putio account"""
    info = putio_api.accountinfo(conf)
    putio_api.ensure_valid_oauth_token(info)
    return info.get('info').get('disk').get('used')


def suspend_until_can_store_all(conf):
    """ensures local filesystem have enough space on disk to sync

    :conf: configuration object
    :returns:
    """
    LOG.info('ensuring enough space in filesystem')
    while True:
        localsize = os.path.getsize(conf.get('localdir'))
        # we don't account for local size because it's replaced if necessary
        free_space = total_free_space() + localsize
        putio_size = putio_root_size(conf)
        if free_space - min_space_to_reserve() < putio_size:
            print '\n[!] Suspending Sync: not enough space to sync local: %d remote: %d ' % free_space,putio_size
            LOG.warn('not enough space to sync local: %d remote: %d',
                     free_space,
                     putio_size)
            suspend_sync()
        else:
            break


def suspend_until_can_store_file(filesize, targetfile):
    """suspends execution until filesystem can store targetfile"""
    while True:
        if total_free_space() - min_space_to_reserve() < filesize:
            print '\n[!] Suspending Sync: not enough free space to download:\n %s' % targetfile
            LOG.warn('not enough free space to download: %s',
                     targetfile)
            suspend_sync()
        else:
            break


def delete_files(root, files):
    """deletes files and direcotries that exist locally but not in put.io"""
    for target in files:
        abspath = os.path.join(root, target)
        print '\n [!] Deleting %s since its not in the putio account' % abspath
        LOG.info('deleting %s since its not in the putio account',
                 abspath)
        if os.path.exists(abspath):
            try:
                if os.path.isdir(abspath):
                    shutil.rmtree(abspath)
                else:
                    os.remove(abspath)
            except (OSError, ValueError):
                print '\n [E] Cant delete dir %s' % abspath
                LOG.error('cant delete dir %s', abspath, exc_info=True)
        else:
            LOG.error(
                'wanted to delete %s but it no longer exists',
                abspath)


def start_download(filesize, download_url, targetfile, conf):
    """downloads the file"""
    suspend_until_can_store_file(filesize, targetfile)
    bps = conf.get('bytes_per_second')
    connections = conf.get('conn_per_downloads')

    print '\nStarting download :%s' % download_url
    LOG.info('starting download :%s into %s', download_url, targetfile)
    cmd = 'axel -o %s -n %d -a -s %d %s' % (targetfile,
                                            connections,
                                            bps,
                                            download_url)
    LOG.debug('running axel: %s', cmd)
    axel = subprocess.Popen(
        ['axel',
         '-o',
         targetfile,
         '-a',
         '-s',
         str(bps),
         '-n',
         str(connections),
         download_url])

    currsize = os.path.getsize(targetfile) if os.path.exists(targetfile) else 0
    pollinterval = 5
    time.sleep(pollinterval)
    remaining_attempts = 3
    while axel.poll() is None:
        time.sleep(pollinterval)
        progress = os.path.getsize(targetfile) - currsize
        currsize = currsize + progress
        if progress == 0:
            LOG.warn('seems like axel isnt effective in the last %d seconds',
                     pollinterval)
            if remaining_attempts == 0:
                LOG.error('axel seems totally stuck, aborting')
                axel.kill()
                return

            remaining_attempts = remaining_attempts - 1
            pollinterval = pollinterval * 2

    returncode = axel.poll()
    if returncode != 0:
        print '\n[E] Download %s failed!' % download_url
        LOG.error(
            'download %s failed with code: %d',
            download_url,
            returncode)
        return

    if os.path.exists(targetfile):
        if os.path.getsize(targetfile) != filesize:
            LOG.info(
                'detected partial download %s due to file size',
                targetfile)
            try:
                os.remove(targetfile)
            except (OSError, IOError):
                print '\n[E] Cant remove bad download %s' % targetfile
                LOG.error(
                    'cant remove bad download %s',
                    targetfile,
                    exc_info=True)


def __check_filesize_and_crc(targetfile, expected_size, expected_crc32):
    """check a file for expected size and crc32

    :targetfile: file to check
    :size: expected size
    :crc: crc32 checksum
    :returns: True if check is ok

    """
    LOG.info('doing byte count and crc32 check to file %s', targetfile)
    if os.path.getsize(targetfile) != expected_size:
        LOG.info(
            'detected partial download %s due to filesize', targetfile)
        return False
    else:
        with open(targetfile, 'r') as binfile:
            crc32 = binascii.crc32(binfile.read()) & 0xFFFFFFFF
            crchex = "%08X" % crc32
            crchex = crchex.lower()
            if crchex.encode('utf-8') != expected_crc32.encode('utf-8'):
                LOG.info('detected partial download due to crc32 got: ' +
                         '%s expected: %s file: %s',
                         crchex, expected_crc32, targetfile)
                return False

    return True
