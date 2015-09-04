
from datetime import datetime
import os
import requests
from threading import Lock

base_url = 'https://api.spark.io/v1/'

class Spark_Interface():
    def __init__(self, object_group, auth_filename = "spark_auth.txt"):
        self.og = object_group
        self.initialized = False
        self.mutex = Lock()
        
        if not os.access(auth_filename, os.R_OK):
            print "Error: failure to read auth file ("+auth_filename+"). File unreadable or does not exist."
            return
        
        f = open(auth_filename, 'r')
        content = f.read()
        f.close()
        
        auth = content.strip().split(':')
        if len(auth) != 2:
            print "Error: failure to read auth file ("+auth_filename+"). Must contain 'username:password'"
            return
        
        username = auth[0]
        password = auth[1]
        
        r = requests.get(base_url+"access_tokens", auth=(username, password))
        
        if r.status_code != 200:
            print "Error: Could not get token."
            return
        
        j = r.json()
        
        now = datetime.now()
        
        token = None
        for token_data in j:
            if ('expires_at' in token_data) and (token_data['expires_at'] != None) and ('client' in token_data) and (token_data['client'] == 'spark-cli'):
                expires = datetime.strptime(token_data['expires_at'][0:-5], "%Y-%m-%dT%H:%M:%S") 
                if expires < now:
                    # delete
                    r = requests.delete(base_url+"access_tokens/"+token_data['token'], auth=(username, password))
                    if r.status_code != 200:
                        print "Warning: Could not delete token ("+token_data['token']+"): "+r.reason
                else:
                    token = token_data['token']
        
        if token == None:
            # create new token
            r = requests.post("https://api.spark.io/oauth/token", data={'grant_type':'password','username':username,'password':password}, auth=('spark','spark'))
            if r.status_code != 200:
                print "Warning: Could not create token: "+r.reason
                return
            token = r.json()['access_token']
        
        self.access_token = "?access_token="+token
    
        r = requests.get(base_url+"devices"+self.access_token)
        
        if r.status_code != 200:
            print "Error: Could not get devices: " + r.reason
            self.devices = []
        
        self.devices = [ (x['name'], x['id']) for x in r.json() ]
        
        for device in [ n[0] for n in self.devices ]:
            print "Found particle device:", device
        
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
        
    def getDeviceNames(self, postfix=None):
        if self.initialized:
            if postfix == None:
                return [ n[0] for n in self.devices ]
            else:
                return [ n[0] for n in self.devices if n[0].endswith(postfix) ]
        
    def getPrettyDeviceNames(self, postfix=None):
        if self.initialized:
            devs = self.getDeviceNames(postfix=postfix);
            if postfix == None:
                return devs
            else:
                return [ n[0].replace(postfix,'') for n in devs ]
    
    def getVariable(self, deviceName, variable):
        if self.initialized:
        
            if deviceName not in [ n[0] for n in self.devices ]:
                print "Error: requested device name ("+deviceName+") not found"
                return None
            
            deviceID = [ n[1] for n in self.devices if n[0] == deviceName ]
            
            self.mutex.acquire()
            result = None
            try:
                r = requests.get(base_url+"devices/"+deviceID[0]+"/"+variable+self.access_token)
                
                if r.status_code == 200:
                    result = r.json()['result']
                else:
                    print "getVariable: Could not get '"+variable+"' from '"+deviceName+"': "+r.reason
                
            except:
                pass
            
            self.mutex.release()
            
            return result

if __name__ == "__main__":    
    s = Spark_Interface(1, "data/spark_auth.txt")
    devNames = s.getDeviceNames(postfix="_floor_temp")
    for d in devNames:
        print d, ":", s.getVariable(d,"temperature")
    
    print "Security status:", s.getVariable("security","state")
    

