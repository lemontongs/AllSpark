
from plugins import temperature_thread
from plugins import user_thread
from plugins import memory_thread
from plugins import furnace_control
from plugins import security_thread
from plugins import set_point
from plugins import energy_thread
import comms_thread
import spark_interface
import twilio_interface
import message_broadcast
import config_utils
import logging

logger = logging.getLogger('allspark.object_group')

CONFIG_SEC_NAME = "general"


class ObjectGroup:
    def __init__(self, config):
        self._initialized = False
        self._running = False
        
        ############################################################################
        # Spark Interface
        ############################################################################
        if not config_utils.check_config_section(config, CONFIG_SEC_NAME):
            return
        
        spark_auth_filename = \
            config_utils.get_config_param( config, CONFIG_SEC_NAME, "spark_auth_file")
        if spark_auth_filename is None:
            return
        
        self.spark = spark_interface.SparkInterface(self, spark_auth_filename)
        
        if not self.spark.is_initialized():
            logger.error( "Failed to create spark interface" )
            return

        ############################################################################
        # Temperature Thread
        ############################################################################
        self.thermostat = temperature_thread.TemperatureThread(self, config = config)

        if not self.thermostat.is_initialized():
            logger.error( "Failed to create temperature thread" )
            return

        ############################################################################
        # User Thread
        ############################################################################
        self.user_thread = user_thread.UserThread(self, config = config)

        if not self.user_thread.is_initialized():
            logger.error( "Failed to create user thread" )
            return

        ############################################################################
        # Memory Thread
        ############################################################################
        self.mem = memory_thread.MemoryThread(self, config = config)

        if not self.mem.is_initialized():
            logger.error( "Failed to create memory thread" )
            return

        ############################################################################
        # Furnace Control Thread
        ############################################################################
        self.furnace_ctrl = furnace_control.FurnaceControl(self, config = config)

        if not self.furnace_ctrl.is_initialized():
            logger.error( "Failed to create furnace controller" )
            return

        ############################################################################
        # Furnace Set Point Object
        ############################################################################
        self.set_point = set_point.SetPoint(self, config = config)

        if not self.set_point.is_initialized():
            logger.error( "Failed to create set point object" )
            return

        ############################################################################
        # Comms Thread
        ############################################################################
        self.comms = comms_thread.CommsThread(port = 5555)

        if not self.comms.is_initialized():
            logger.error( "Failed to create comms thread" )
            return

        self.comms.register_callback("set_point", self.set_point.parse_set_point_message)
        
        ############################################################################
        # Security Thread
        ############################################################################
        self.security = security_thread.SecurityThread(self, config = config)

        if not self.security.is_initialized():
            logger.error( "Failed to create security thread" )
            return

        self.comms.register_callback("alarm", self.security.parse_alarm_control_message)

        ############################################################################
        # Twilio
        ############################################################################
        self.twilio = twilio_interface.TwilioInterface(config = config)

        if not self.twilio.is_initialized():
            logger.error( "Failed to create twilio interface" )
            return
        
        ############################################################################
        # UDP Multicast
        ############################################################################
        self.broadcast = message_broadcast.MessageBroadcast()
        
        ############################################################################
        # Energy Thread
        ############################################################################
        self.energy = energy_thread.EnergyThread(self, config = config)

        if not self.energy.is_initialized():
            logger.error( "Failed to create energy monitor" )
        
        self._initialized = True

    def is_initialized(self):
        return self._initialized

    def start(self):
        if self._initialized and not self._running:
            self.thermostat.start()
            self.user_thread.start()
            self.mem.start()
            self.furnace_ctrl.start()
            self.comms.start()
            self.security.start()
            self.energy.start()
            self._running = True

    def stop(self):
        if self._initialized and self._running:
            self.thermostat.stop()
            self.user_thread.stop()
            self.mem.stop()
            self.furnace_ctrl.stop()
            self.comms.stop()
            self.security.stop()
            self.energy.stop()
            self._running = False

    def get_javascript(self):
        return \
            self.thermostat.get_javascript()   + \
            self.mem.get_javascript()          + \
            self.user_thread.get_javascript()  + \
            self.security.get_javascript()     + \
            self.furnace_ctrl.get_javascript() + \
            self.set_point.get_javascript()    + \
            self.energy.get_javascript()
        
    def get_html(self):
        return \
            self.thermostat.get_html()   + \
            self.energy.get_html()       + \
            self.furnace_ctrl.get_html() + \
            self.set_point.get_html()    + \
            self.user_thread.get_html()  + \
            self.security.get_html()     + \
            self.mem.get_html()

    @staticmethod
    def get_template_config(config):
        config = temperature_thread.TemperatureThread.get_template_config(config)
        config = furnace_control.FurnaceControl.get_template_config(config)
        config = set_point.SetPoint.get_template_config(config)
        config = security_thread.SecurityThread.get_template_config(config)
        config = user_thread.UserThread.get_template_config(config)
        config = memory_thread.MemoryThread.get_template_config(config)
        config = energy_thread.EnergyThread.get_template_config(config)
        return config
