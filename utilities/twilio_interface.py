
from twilio.rest import TwilioRestClient
from utilities import config_utils
import logging

CONFIG_SEC_NAME = "twilio"

logger = logging.getLogger('allspark.' + CONFIG_SEC_NAME)


class TwilioInterface:
    def __init__(self, config):
        self._initialized = False
        
        if not config_utils.check_config_section( config, CONFIG_SEC_NAME ):
            return

        sid = config_utils.get_config_param( config, CONFIG_SEC_NAME, "sid")
        if sid is None:
            return
               
        auth = config_utils.get_config_param( config, CONFIG_SEC_NAME, "auth")
        if auth is None:
            return
               
        self.number = config_utils.get_config_param( config, CONFIG_SEC_NAME, "number")
        if self.number is None:
            return
        
        self.client = TwilioRestClient(sid, auth)
        
        self._initialized = True
    
    def is_initialized(self):
        return self._initialized
    
    def send_sms(self, msg, number):
        if self._initialized:
            self.client.messages.create(body=msg, to=number, from_=self.number)

if __name__ == "__main__":
    import ConfigParser
    
    conf = ConfigParser.ConfigParser()
    conf.read("data/config.cfg")
    
    t = TwilioInterface(conf)
    
    


