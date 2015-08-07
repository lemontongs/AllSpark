
from datetime import datetime
import os
import pprint
import requests
import time

base_url = 'https://api.spark.io/v1/'

class Spark_Interface():
    def __init__(self, object_group, auth_filename = "spark_auth.txt"):
        self.og = object_group
        self.initialized = False
        
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
        
        self.devices = [ (x['name'], x['id']) for x in r.json() if x['name'].endswith('floor_temp') ]
        
        for device in [ n[0] for n in self.devices ]:
            print device
        
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
        
    def getDeviceNames(self):
        if self.initialized:
            return [ n[0] for n in self.devices ]
        
    def getPrettyDeviceNames(self):
        if self.initialized:
            return [ n[0].replace('_floor_temp','') for n in self.devices ]
        
    def getVariable(self, deviceName, variable):
        
        if deviceName not in [ n[0] for n in self.devices ]:
            print "Error: requested device name ("+deviceName+") not found"
            return None
        
        deviceID = [ n[1] for n in self.devices if n[0] == deviceName ]
        
        try:
            r = requests.get(base_url+"devices/"+deviceID[0]+"/"+variable+self.access_token)
            
            if r.status_code != 200:
                print "Error: Could not get: "+r.reason
                return None
            
            return r.json()['result']
        except:
            return None

    def callNamedDeviceFunction(self, deviceName, func, args, return_key):
        
        # Get device ID
        r = requests.get(base_url+"devices"+self.access_token)
        
        if r.status_code != 200:
            print "Error: Could not get devices: " + r.reason
            return None
        
        devices = [ (x['name'], x['id']) for x in r.json() if x['name'] == deviceName ]
        
        if len(devices) < 1:
            print "Error: Could not find device with name: " + deviceName
            return None
        
        device_id = devices[0][1]
        
        r = requests.post(base_url+"devices/"+device_id+"/"+func, \
                          data={'access_token':self.access_token.split('=')[1], 'args':args})
        
        if r.status_code != 200:
            print "Error: Could not get: "+r.reason
            return None
        
        if return_key not in r.json():
            print "Error: " + return_key + " not found in response: " + r.json()
            return None
        
        return r.json()[return_key]


if __name__ == "__main__":
    import sys
    
    s = Spark_Interface(sys.argv[1])
    devNames = s.getDeviceNames()
    for d in devNames:
        print d, s.getVariable(d,"temperature")
    
    
    

