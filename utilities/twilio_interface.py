
from twilio.rest import TwilioRestClient

base_url = 'https://api.twilio.com/2010-04-01'

class Twilio_Interface():
    def __init__(self, config):
        self.initialized = False

        config_sec = "twilio"
        
        if config_sec not in config.sections():
            print config_sec + " section missing from config file"
            return
        
        if "sid" not in config.options(config_sec):
            print "sid property missing from " + config_sec + " section"
            return

        sid = config.get(config_sec, "sid")
                
        if "auth" not in config.options(config_sec):
            print "auth property missing from " + config_sec + " section"
            return

        auth = config.get(config_sec, "auth")
                
        if "number" not in config.options(config_sec):
            print "number property missing from " + config_sec + " section"
            return

        self.number = config.get(config_sec, "number")
        
        self.client = TwilioRestClient(sid, auth)
        
        self.initialized = True
    
    def isInitialized(self):
        return self.initialized
    
    def sendSMS(self, msg, number):
        if self.initialized:
            self.client.messages.create(body=msg, to=number, from_=self.number)

if __name__ == "__main__":
    import ConfigParser
    
    config = ConfigParser.ConfigParser()
    config.read("data/config.cfg")
    
    t = Twilio_Interface( config )
    
    


