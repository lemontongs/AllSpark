
from twilio.rest import TwilioRestClient
from utilities import config_utils
import logging

CONFIG_SEC_NAME = "twilio"

logger = logging.getLogger('allspark.'+CONFIG_SEC_NAME)

class Twilio_Interface():
    def __init__(self, config):
        self._initialized = False
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        sid = config_utils.get_config_param( config, CONFIG_SEC_NAME, "sid")
        if sid == None:
            return
               
        auth = config_utils.get_config_param( config, CONFIG_SEC_NAME, "auth")
        if auth == None:
            return
               
        self.number = config_utils.get_config_param( config, CONFIG_SEC_NAME, "number")
        if self.number == None:
            return
        
        self.client = TwilioRestClient(sid, auth)
        
        self._initialized = True
    
    def isInitialized(self):
        return self._initialized
    
    def sendSMS(self, msg, number):
        if self._initialized:
            self.client.messages.create(body=msg, to=number, from_=self.number)

if __name__ == "__main__":
    import ConfigParser
    
    config = ConfigParser.ConfigParser()
    config.read("data/config.cfg")
    
    t = Twilio_Interface( config )
    
    


