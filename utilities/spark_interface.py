
from datetime import datetime
import os
import requests
import logging
from threading import Lock

base_url = 'https://api.spark.io/v1/'

logger = logging.getLogger('allspark.spark_interface')


class SparkInterface:
    def __init__(self, auth_filename = "spark_auth.txt"):

        self._initialized = False
        self.mutex = Lock()
        
        if not os.access(auth_filename, os.R_OK):
            logger.error( "Error: failure to read auth file (" + auth_filename +
                          "). File unreadable or does not exist." )
            return
        
        f = open(auth_filename, 'r')
        content = f.read()
        f.close()
        
        auth = content.strip().split(':')
        if len(auth) != 2:
            logger.error( "Error: failure to parse auth file (" + auth_filename +
                          "). Must contain 'username:password'" )
            return
        
        username = auth[0]
        password = auth[1]
        
        r = requests.get(base_url + "access_tokens", auth=(username, password))
        
        if r.status_code != 200:
            logger.error( "Error: Could not get token." )
            return
        
        j = r.json()
        
        now = datetime.now()
        
        token = None
        for token_data in j:
            if ('expires_at' in token_data) and \
               (token_data['expires_at'] is not None) and \
               ('client' in token_data) and \
               (token_data['client'] == 'spark-cli'):

                expires = datetime.strptime(token_data['expires_at'][0:-5], "%Y-%m-%dT%H:%M:%S")
                if expires < now:
                    # delete
                    r = requests.delete(base_url + "access_tokens/" + token_data['token'], auth=(username, password))
                    if r.status_code != 200:
                        logger.warning( "Warning: Could not delete token (" + token_data['token'] + "): " + r.reason )
                else:
                    token = token_data['token']
        
        if token is None:
            # create new token
            r = requests.post("https://api.spark.io/oauth/token", data={'grant_type': 'password',
                                                                        'username': username,
                                                                        'password': password},
                              auth=('spark', 'spark'))

            if r.status_code != 200:
                logger.warning( "Warning: Could not create token: " + r.reason )
                return
            token = r.json()['access_token']
        
        self.access_token = "?access_token=" + token
    
        r = requests.get(base_url + "devices" + self.access_token)
        
        if r.status_code != 200:
            logger.error( "Could not get devices: " + r.reason )
            self.devices = []
        
        self.devices = [ (x['name'], x['id']) for x in r.json() ]
        
        for device in [ n[0] for n in self.devices ]:
            logger.info( "Found particle device:" + device )
        
        self._initialized = True
    
    def is_initialized(self):
        return self._initialized
        
    def get_device_names(self, postfix=None):
        if self._initialized:
            if postfix is None:
                return [ n[0] for n in self.devices ]
            else:
                return [ n[0] for n in self.devices if n[0].endswith(postfix) ]
        
    def get_pretty_device_names(self, postfix=None):
        if self._initialized:
            devs = self.get_device_names(postfix=postfix)
            if postfix is None:
                return devs
            else:
                return [ n[0].replace(postfix, '') for n in devs ]
    
    def get_variable(self, device_name, variable):
        if self._initialized:
        
            if device_name not in [ n[0] for n in self.devices ]:
                logger.warning( "Error: requested device name (" + device_name + ") not found" )
                return None
            
            device_id = [ n[1] for n in self.devices if n[0] == device_name ]
            
            self.mutex.acquire()
            result = None
            try:
                r = requests.get(base_url + "devices/" + device_id[0] + "/" + variable + self.access_token)
                
                if r.status_code == 200:
                    result = r.json()['result']
                else:
                    logger.warning( "getVariable: Could not get '" + variable + "' from '" + device_name +
                                    "': " + r.reason )
            except requests.exceptions.RequestException:
                pass
            
            self.mutex.release()
            
            return result

if __name__ == "__main__":    
    s = SparkInterface("data/spark_auth.txt")
    devNames = s.get_device_names(postfix="_floor_temp")
    for d in devNames:
        print d, ":", s.get_variable(d, "temperature")
    
    print "Security status:", s.get_variable("security", "state")
