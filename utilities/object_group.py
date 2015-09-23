
from plugins import temperature_thread
from plugins import user_thread
from plugins import memory_thread
from plugins import furnace_control
from plugins import security_thread
from plugins import set_point
import comms_thread
import spark_interface
import twilio_interface
import message_broadcast
import config_utils
import logging

logger = logging.getLogger('allspark.object_group')

CONFIG_SEC_NAME = "general"

class Object_Group():
    def __init__(self, config):
        self.initialized = False
        self.running = False
        
        ############################################################################
        # Spark Interface
        ############################################################################
        if not config_utils.check_config_section(config, CONFIG_SEC_NAME):
            return
        
        spark_auth_filename = \
            config_utils.get_config_param( config, CONFIG_SEC_NAME, "spark_auth_file")
        if spark_auth_filename == None:
            return
        
        self.spark = spark_interface.Spark_Interface(self, spark_auth_filename)
        
        if not self.spark.isInitialized():
            logger.error( "Failed to create spark interface" )
            return

        
        ############################################################################
        # Temperature Thread
        ############################################################################
        self.thermostat = temperature_thread.Temperature_Thread(self, config = config)

        if not self.thermostat.isInitialized():
            logger.error( "Failed to create temperature thread" )
            return


        ############################################################################
        # User Thread
        ############################################################################
        self.user_thread = user_thread.User_Thread(self, config = config)

        if not self.user_thread.isInitialized():
            logger.error( "Failed to create user thread" )
            return


        ############################################################################
        # Memory Thread
        ############################################################################
        self.mem = memory_thread.Memory_Thread(self, config = config)

        if not self.mem.isInitialized():
            logger.error( "Failed to create memory thread" )
            return


        ############################################################################
        # Furnace Control Thread
        ############################################################################
        self.furnace_ctrl = furnace_control.Furnace_Control(self, config = config)

        if not self.furnace_ctrl.isInitialized():
            logger.error( "Failed to create furnace controller" )
            return

        ############################################################################
        # Furnace Set Point Object
        ############################################################################
        self.set_point = set_point.Set_Point(self, config = config)

        if not self.set_point.isInitialized():
            logger.error( "Failed to create set point object" )
            return

        ############################################################################
        # Comms Thread
        ############################################################################
        self.comms = comms_thread.Comms_Thread(port = 5555)

        if not self.comms.isInitialized():
            logger.error( "Failed to create comms thread" )
            return

        self.comms.register_callback("set_point", self.set_point.parse_set_point_message)
        
        ############################################################################
        # Security Thread
        ############################################################################
        self.security = security_thread.Security_Thread(self, config = config)

        if not self.security.isInitialized():
            logger.error( "Failed to create security thread" )
            return
        
        ############################################################################
        # Twilio
        ############################################################################
        self.twilio = twilio_interface.Twilio_Interface(config = config)

        if not self.twilio.isInitialized():
            logger.error( "Failed to create twilio interface" )
            return
        
        ############################################################################
        # UDP Multicast
        ############################################################################
        self.broadcast = message_broadcast.Message_Broadcast()

        self.initialized = True
        
        
    def start(self):
        if self.initialized and not self.running:
            self.thermostat.start()
            self.user_thread.start()
            self.mem.start()
            self.furnace_ctrl.start()
            self.comms.start()
            self.security.start()
            self.running = True


    def stop(self):
        if self.initialized and self.running:
            self.thermostat.stop()
            self.user_thread.stop()
            self.mem.stop()
            self.furnace_ctrl.stop()
            self.comms.stop()
            self.security.stop()
            self.running = False

    def get_javascript(self):
        return self.thermostat.get_javascript()   + \
               self.mem.get_javascript()          + \
               self.user_thread.get_javascript()  + \
               self.security.get_javascript()     + \
               self.furnace_ctrl.get_javascript() + \
               self.set_point.get_javascript()
        
    def get_html(self):
        return self.thermostat.get_html()   + \
               self.furnace_ctrl.get_html() + \
               self.set_point.get_html()    + \
               self.user_thread.get_html()  + \
               self.security.get_html()     + \
               self.mem.get_html()
        
    @staticmethod
    def get_template_config(config):
        temperature_thread.Temperature_Thread.get_template_config(config)
        furnace_control.Furnace_Control.get_template_config(config)
        set_point.Set_Point.get_template_config(config)
        security_thread.Security_Thread.get_template_config(config)
        user_thread.User_Thread.get_template_config(config)
        memory_thread.Memory_Thread.get_template_config(config)
        
        
        
