#!/usr/bin/python
#command to delete the broken records which are invisible in powerdns.net gui

import sys
import urllib
import urllib2
import re

BASEURL="https://www.powerdns.net/services/express.asmx"

if len(sys.argv)!=3:
    print "usage: deleterecord.py <api-key> <recordid>"
    sys.exit(0)
    
apikey=sys.argv[1]
recordid=sys.argv[2]


url = BASEURL+'?apikey='+apikey
    
headers = { 
'Content-Type': 'application/soap+xml; charset=utf-8'      
}

data = """<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <deleteRecordById xmlns="http://powerdns.net/express">
      <recordId>%s</recordId>
    </deleteRecordById>
  </soap12:Body>
</soap12:Envelope>"""%recordid
req = urllib2.Request(url, data, headers)
response = urllib2.urlopen(req)
the_page = response.read()


print "Result:"
print the_page

