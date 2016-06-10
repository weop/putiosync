# put.io sync
syncs PutIO files to a local folder. fork of put.io synchronizer, made more verbose/loud so you know what's up.

# quick start
install axel download manager (mac users: brew install axel)
git clone this repo
./sync.py

## what the synchornizer does
this script polls put.io public API periodically for changes and synchronises your remote PutIO files and folders.

## requirements
details on how to fulfil the following requirements will be explained in later
sections
* a registered put.io account
* a registered put.io application
* a valid oauth token
* a *nix host to run on (not going to bother testing on windows)
* at least X Gigabyte of space on the host where X is the total space in your
put.io account

## software dependencies
* python 2.7
* axel download manager
* gpg if you care about storing app info securely

## security / privacy
 - The synchronizer pulls data from put.io via https
 - the put.io oauth token may be stored encrypted by gpg. Example:
```
# you will be prompted for a passphrase, paste the result into sync_config.py
$> echo $MY_OAUTH_TOKEN | gpg --symmetric --cipher-algo=AES256 --armor | base64
```
