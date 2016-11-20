#!/usr/bin/python

import ConfigParser
import validators
import tempfile
import urllib2
import logging
import socket
import errno
import time
import os

config = ConfigParser.ConfigParser()
config.readfp(open('defaults.cfg'))

# config vars:
LINKS_FILE = config.get("downloader", "LINKS_FILE")
LOG_LEVEL = config.get("downloader", "LOG_LEVEL")
STORE_PATH = config.get("downloader", "STORE_PATH")

# filesize limit in mb
FILESIZE_LIMIT = config.get("downloader", "FILESIZE_LIMIT")

# TIMEOUT
TIMEOUT = config.get("downloader", "TIMEOUT")

# LOGGING
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


# should we also check inodes / available storage ?

# env variables
# $ http_proxy="http://www.someproxy.com:3128"
# $ export http_proxy

def checkVars():
	try:
		LINKS_FILE
		LOG_LEVEL
		STORE_PATH
		TIMEOUT
		FILESIZE_LIMIT
	except NameError:
		logger.error('Var not defined')		
	else:
		logger.info('All vars defined')
		return True

# additional check: check if folder exists
def doPathsExist(links_f,storage_p):
	if os.path.isfile(links_f):
		logger.info('Links file OK')
	else:
		logger.error('No file with links')
		return False

	if os.path.isdir(storage_p):
		logger.info('Storage path exists')
	else:
		logger.error('No storage path')
		return False

	return True

def isStorageWritable(storage_p):
    try:
        testfile = tempfile.TemporaryFile(dir = storage_p)
        testfile.close()
        logger.info('Directory writable')
    except OSError as e:
        if e.errno == errno.EACCES:
        	logger.error('Directory not writable')
        	return False
        e.filename = storage_p
        raise
    return True

# isFileWithinLimits(LINKS_FILE,FILESIZE_LIMIT)
def isFileWithinLimits(links_f,file_l):
	try:
		file_size = os.path.getsize(links_f)
		if (file_size/(1024*1024) > file_l):
			logger.error('File greater then filesize limit')
			return False
		else:
			logger.info('File size within parameters : ' + str(file_size) + ' bytes')
			return True
	except:
	    logger.error("Unexpected error on getting filesize " + sys.exc_info()[0] )
	    return False


def getLinksFromFile(links_f):
	try:
	    f = open(links_f)
	    content = f.read()
	    f.close()
	    logger.info('Got content from file')
	    return content
	except IOError as (errno, strerror):
	    logger.error("I/O error" + errno + " " + strerror)
	except Exception,e:
	    logger.error("Unexpected error " + str(e))
	    raise

def checkLinkForm(temp_url):
	return (validators.url(temp_url))

def testAll():
	if (checkVars() and 
		doPathsExist(LINKS_FILE,STORE_PATH) and 
		isStorageWritable(STORE_PATH) and 
		isFileWithinLimits(LINKS_FILE,FILESIZE_LIMIT)):
		return True
	else:
		return False

def startAll():

	if not testAll():
		logger.error('Test failed')
		exit(3)

	links = getLinksFromFile(LINKS_FILE).split("\n")
	TODAY = (time.strftime("%Y%m%d"))

	try:
	    os.stat(STORE_PATH + TODAY)
	except:
	    os.mkdir(STORE_PATH + TODAY)      

	# When opening HTTPS URLs, it does not attempt to validate the server certificate
	# should doublecheck this..

	socket.setdefaulttimeout(10)

	for url in links:
		if(checkLinkForm(url)):
			logger.debug('url valid ' + url)
			try:
				# this should work unless the URL are dynamically generated 
				# otherwise we should get the filename from the headers
				filename=url.split('/')[-1]
				resp = urllib2.urlopen(url, timeout = int(TIMEOUT))
				with open(STORE_PATH + TODAY + '/' + filename, 'wb') as f:
				  f.write(resp.read())
  				f.close()
  			# Errors to catch if we're interested (L7 to L3):
			# urllib2.URLError, 
			# urllib2.HTTPError, 
			# httplib.HTTPException
			# socket.error
			except Exception,e:
				logger.error(e)
				failed = open(STORE_PATH + TODAY + '/' + 'failed_urls',"w+")
				failed.write(url + "\n")
				failed.close()
				continue
		else:
			logger.error('url non valid ' + url)
			# append to failed urls
		
startAll()
