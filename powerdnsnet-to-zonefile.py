#!/usr/bin/python
import sys
import os
import urllib
import urllib2
import xml.etree.cElementTree as et
from string import Template
import re

BASEURL="https://www.powerdns.net/services/express.asmx"

class Record(object):
    def __init__(self):
        self.id=None
        self.zoneid=None
        self.type=None
        self.ttl=None
        self.content=None
        self.name=None
        self.priority=None
        
    def __repr__(self):
        return "<Record name='%s' type='%s' content='%s' ttl='%s'"%(self.name,self.type,self.content,self.ttl)

def stderr(msg):
    sys.stderr.write(msg+"\n")
    

def get_zone_id_map(apikey):
    url = BASEURL+'?apikey='+apikey
    
    headers = { 
    'Content-Type': 'application/soap+xml; charset=utf-8'      
    }
    
    data = """<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <listZones xmlns="http://powerdns.net/express" />
      </soap12:Body>
    </soap12:Envelope>"""
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    the_page = response.read()
    tree=et.fromstring(the_page)
    body=tree[0]
    listZonesResponse = body[0]
    listZonesResult = listZonesResponse[0]
    code = listZonesResult[0]
    description = listZonesResult[1]
    if code.text!='100':
        stderr("Failed to download zone list! Errcode=%s, Description=%s"%(code.text,description.text))
        return None
    
    zonelist = listZonesResult[2]
    
    zoneids={}
    
    for zone in zonelist:
        zoneid=None
        zonename=None 
        for child in zone:
            if child.tag=='{http://powerdns.net/express}Id':
                zoneid=child.text
            if child.tag=='{http://powerdns.net/express}Name':
                zonename=child.text
        if zoneid!=None and zonename!=None:
            zoneids[zonename]=zoneid
        else:
            stderr("zone did not have name or id (name=%s, id=%s)"%(zonename,zoneid))
    return zoneids

def get_record_list(apikey,zoneid):
    url = BASEURL+'?apikey='+apikey
    
    headers = { 
    'Content-Type': 'application/soap+xml; charset=utf-8'      
    }
    data="""<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <listRecords xmlns="http://powerdns.net/express">
          <zoneId>%s</zoneId>
        </listRecords>
      </soap12:Body>
    </soap12:Envelope>"""%zoneid
    
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    the_page = response.read()
    tree=et.fromstring(the_page)
    body=tree[0]
    listRecordsResponse = body[0]
    listRecordsResult = listRecordsResponse[0]
    code = listRecordsResult[0]
    description = listRecordsResult[1]
    if code.text!='100':
        stderr("Failed to download record list for zone id=%s! Errcode=%s, Description=%s"%(zoneid,code.text,description.text))
        return None
    
    recordlist = listRecordsResult[2]
    
    retlist=[]
    
    for rec in recordlist:
        record=Record()
        record.id=rec[0].text
        record.zoneid=rec[1].text
        record.name=rec[2].text
        record.type=rec[3].text
        record.content=rec[4].text
        record.ttl=rec[5].text
        record.priority=rec[6].text
        retlist.append(record)
    return retlist

def build_zone_file_content(origin,recordlist):
    buff="$ORIGIN %s.\n"%origin
    supportedtypes=['A','AAAA','SOA','MX','NS','SPF','CNAME','TXT','SRV','PTR']
    appenddot=['NS','MX','CNAME','PTR']
    writeprio=['MX','SRV']
    
    for record in recordlist:
        if record.type not in supportedtypes:
            stderr("Zone %s record %s : unsupported type - skipping"%(origin,record))
            continue
        type=record.type
    
        if record.name==None or record.name=='':
            stderr("Zone %s record %s : empty name - skipping"%(origin,record))
            continue
        
        name=record.name+"."
        if record.name==origin:
            name="@"
            
        if record.content==None or record.content=='':
            stderr("Zone %s record %s : empty content - skipping"%(origin,record))
            continue
        content=record.content
        
        #append dots in soa
        if type=='SOA':
            content=content.split()
            content[0]=content[0]+'.'
            content[1]=content[1]+'.'
            content=" ".join(content)
        
        if type in appenddot:
            content+='.'
        
        if type in writeprio:
            priority=record.priority
            if record.priority==None:
                priority=0
        else:
            priority=''  
        
        ttl=record.ttl
        if record.ttl==None:
            ttl=''
        
        t=Template("$name $ttl IN $type $priority $content")
        values={'name':name,'type':type,'content':content,'priority':priority,'ttl':ttl}
        line=t.safe_substitute(values)
        buff+=line+'\n'
        
    return buff


if __name__=='__main__':
    if len(sys.argv)<3:
        print "Usage: powerdnsnet-to-zonefile <API-key(s) separated by comma> <outputdir> [<domainname> [<zonename> ...]]"
        sys.exit(0)
        
    apikeys=sys.argv[1]
    outdir=sys.argv[2]
    zonenames=sys.argv[3:]
    
    named_conf_buff=""
    
    if not os.path.isdir(outdir):
        stderr("%s is not a directory")
        sys.exit(1)
    
    for apikey in apikeys.split(','):
        zoneids=get_zone_id_map(apikey)
        if zoneids==None:
            stderr('Did not get zonelist for apikey %s - skipping'%apikey)
            continue
        
        for zonename,zoneid in zoneids.iteritems():
            if len(zonenames)>0 and zonename.lower() not in zonenames:
                continue
            recordlist=get_record_list(apikey,zoneids[zonename])
            zonefile=build_zone_file_content(zonename, recordlist)
            
            filename=zonename+".zone"
            abspath=os.path.abspath(outdir)
            fullpath=abspath+'/'+filename
            fp=open(fullpath,'w')
            fp.write(zonefile)
            fp.close
            print "Wrote: %s"%fullpath
            
            entry="""zone "%s" IN {
        type master;
        file "%s";
    };
    """%(zonename,fullpath)
            
            named_conf_buff+=entry+"\n"
        
    namedconf=abspath+'/named.conf'
    fp=open(namedconf,'w')
    fp.write(named_conf_buff)
    fp.close()
    
    print "wrote %s"%namedconf
    
    
    