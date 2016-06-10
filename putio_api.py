"""this module consists solely of methods that operate the putio API"""

import httplib
import urllib2
import gzip
import StringIO
import json
from urllib import urlencode
from sync_logging import LOG
import exit_helper

USER_AGENT = 'putio-sync-client'
API_URL = 'https://api.put.io/v2'


def accountinfo(conf):
    """returns the account info"""
    resource = '/account/info'
    return make_api_request(conf, resource, {}, compress=False)


def getfiles(conf, parent_id):
    """fetches the files based in the parent in the putio account"""
    resource = '/files/list'
    return make_api_request(conf, resource, {'parent_id': parent_id})


def make_api_request(conf, resource, params, compress=True):
    """makes an http call to put.io api

    :conf: configuration object
    :resource: the REST resource in the api
    :params: a dictionary of url parameters key-val
    :returns: raw response from http response or None if failed

    """
    params['oauth_token'] = conf.get('oauthtoken')
    url = API_URL + resource + '?' + urlencode(params)
    LOG.debug('making http request: %s', url)
    req = urllib2.Request(url)
    req.add_header('User-Agent', USER_AGENT)
    req.add_header('Accept', 'application/json')
    if compress:
        req.add_header('Accept-Encoding', 'gzip;q=1.0,deflate;q=0.5,*;q=0')
    try:
        response = urllib2.urlopen(req)
        if response.getcode() == 200:
            content = response.read()
            try:
                if compress:
                    try:
                        inflated = gzip.GzipFile(
                            fileobj=StringIO.StringIO(content))

                        return json.loads(inflated.read())
                    except IOError:
                        LOG.error(
                            'request failed due to IO error, content',
                            exc_info=True)

                        return json.loads(content)
                else:
                    return json.loads(content)
            except ValueError:
                LOG.error(
                    'cant parse api response: %s',
                    content,
                    exc_info=True)

                return None
        elif response.getcode() == 302:
            LOG.debug('got redirect: %s', str(response.info()))
            return response.info()
        else:
            LOG.error('request failed %s status: %s', url, response.getcode())

    except urllib2.HTTPError as exc:
        LOG.error(
            'request failed %s status: %s message: %s',
            url,
            exc.code,
            exc.reason)

    return None


def get_download_url(conf, fileid):
    """the api to download just redirects to the real url to download

    :conf: configuration object
    :fileid: fileid to download
    :returns: the download url

    """
    LOG.debug(
        'trying to dereference download url for file id: %s',
        str(fileid))
    try:
        conn = httplib.HTTPSConnection('api.put.io')
        url = API_URL + \
            '/files/%s/download?oauth_token=' + conf.get('oauthtoken')
        url = url % fileid
        conn.request("GET", url, None, {'User-Agent': USER_AGENT})
        response = conn.getresponse()
        if response.status == 302:
            return response.getheader('Location')
        else:
            LOG.error(
                'putio api returned status %d for download: %s',
                response.status, url)
            return None
    except (httplib.HTTPException, IOError, OSError):
        LOG.error(
            'error dereferencing download url for file id: %s',
            str(fileid), exc_info=True)
        return None


def ensure_valid_oauth_token(api_response):
    """validates the api response isn't indicating invalid oauth token

    :api_response: self explanatory
    :returns: None

    """
    status = api_response.get('status', '')
    error_type = api_response.get('error_type', '')
    if status.lower() == 'error' and error_type.lower() == 'invalid_grant':
        exit_helper.exit_invalid_oauth_token()
