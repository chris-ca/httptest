#!/usr/bin/env python3

import sys
import re
import time
import requests
import logging
import argparse

import config
import templates

from bs4 import BeautifulSoup
logger = logging.getLogger('httptest')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s")

fh = logging.FileHandler('httptest.log')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

ch.setFormatter(formatter)
fh.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(fh)

parser = argparse.ArgumentParser()
parser.add_argument('--start-line', dest='start_line', help='start reading data from file in line N', default=0)
parser.add_argument('--limit', dest='limit', help='number of records to process before ending script', default=0)
parser.add_argument('--file', dest='file', default='accommodations.txt', help='File name to read URLs from')
parser.add_argument('--env', dest='environment', required=True, help='Environment must be specified')
parser.add_argument('--timeout', dest='timeout', help='TCP connect timeout')
parser.add_argument('--template', dest='template', required=True, help='Template for validation')

args = parser.parse_args()

cookies = {}

if args.environment != 'eiger':
    cookies = {'hhd_router_info': config.environments[args.environment]}

template = {}
for t  in templates.templates:
    if (t['name'] == args.template):
        template = t

class ConnectFailedException(Exception):
    pass

class TestFailedException(Exception):
    pass

class TestRunner:
    request_count = 0
    average_response_time = 0

    def __init__(self):
        self.logger = logging.getLogger('httptest')
        self.logger.info("URLtest starting. Cookies: " + str(cookies))

    def get(self, record):
        try:
            logoutput = ''

            requestOptions = {}

            if 'requestOptions' in record:
                requestOptions = record['requestOptions']

            starttime = time.time()
            r = requests.get(record['url'], cookies=cookies, **requestOptions)
            roundtrip = time.time() - starttime
            self.average_response_time = (self.average_response_time * self.request_count)
            self.request_count+=1
            self.average_response_time = (self.average_response_time + roundtrip) / self.request_count

            logoutput += "\t{0:3d}\t{1:6d}\t{2: 4.2f}".format(r.status_code, len(r.content), round(roundtrip,2))

            if 'desc' in record:
                logoutput += "\t"+record['desc']


            if 'test' in record:
                if record['test']['status_code'] != r.status_code:
                    ''' verify status code '''
                    raise ConnectFailedException("Status Code: got {}, expected {} ".format(r.status_code, record['test']['status_code']))

                ''' verify presence of robots meta if not skipped '''
                if r.status_code != 200 or ('skip_robots' in record['test'] and record['test']['skip_robots'] == True):
                    pass
                else:
                    soup = BeautifulSoup(r.content,"lxml")
                    samples = soup.find(attrs={'name':'robots'})
                    if not re.match(r'.*index, *follow|follow, *?index.*', str(samples), re.DOTALL):
                        raise TestFailedException ("Value not matched: got {}".format(samples))

                ''' verify contents of html elements '''
                if 'elements' in record['test']:
                    soup = BeautifulSoup(r.content,"lxml")
                    for element in record['test']['elements']:
                        pattern = record['test']['elements'][element]
                        samples = soup.find(element)
                        if not re.match(pattern, str(samples), re.DOTALL):
                            raise TestFailedException ("Value not matched: got {}, expected {}".format(samples, pattern))
                        
            logoutput += "\tGET {}".format(record['url'])
            self.logger.info(logoutput)
            self.logger.debug("avg ({0}): {1:04f}".format(self.request_count, self.average_response_time))
        
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, TestFailedException, ConnectFailedException) as e:
            logoutput += "\tGET {}".format(record['url'])
            self.logger.error(logoutput+"\t"+str(e)) 
            if ('r' in locals()):
                self.logger.debug(r.headers)

if __name__ == "__main__":
    tr = TestRunner()
    options = template

    if (args.timeout != None and int(args.timeout) > 0):
        options['requestOptions']['timeout'] = int(args.timeout)
  
    linecount=0
    processed=0
    with open(args.file) as f:
        for url in f:
            linecount=linecount+1
            if (int(args.start_line) > 0 and linecount < int(args.start_line)):
                continue

            record = {
                'url': url.strip(),
                'desc': '#{0:06d} '.format(linecount),
                **options
            }

            processed=processed+1
            tr.get(record)
            if int(args.limit) > 0 and processed >= int(args.limit):
                print("END: Limit reached: "+str(processed))
                break
