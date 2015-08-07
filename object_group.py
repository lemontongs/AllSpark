
import comms_thread
import temperature_thread
import user_thread
import memory_thread
import furnace_control
import security_thread
import spark_interface

class Object_Group():
    def __init__(self, config):
        self.initialized = False
        self.running = False
        
        ############################################################################
        # Spark Interface
        ############################################################################
        if "spark_auth_file" not in config.options("general"):
            print "spark_auth_file property missing from general section"
            return

        spark_auth_filename = config.get("general", "spark_auth_file")
        
        self.spark = spark_interface.Spark_Interface(self, spark_auth_filename)
        
        if not self.spark.isInitialized():
            print "Error creating spark interface"
            return

        
        ############################################################################
        # Temperature Thread
        ############################################################################
        self.thermostat = temperature_thread.Temperature_Thread(self, config = config)

        if not self.thermostat.isInitialized():
            print "Error creating temperature thread"
            return


        ############################################################################
        # User Thread
        ############################################################################
        self.user_thread = user_thread.User_Thread(self, config = config)

        if not self.user_thread.isInitialized():
            print "Error creating user thread"
            return


        ############################################################################
        # Memory Thread
        ############################################################################
        self.mem = memory_thread.Memory_Thread(self, config = config)

        if not self.mem.isInitialized():
            print "Error creating memory thread"
            return


        ############################################################################
        # Furnace Control Thread
        ############################################################################
        self.furnace_ctrl = furnace_control.Furnace_Control \
            (self, "data/set_points.cfg", "data/furnace_state.csv")

        if not self.furnace_ctrl.isInitialized():
            print "Error creating furnace controller"
            return


        ############################################################################
        # Comms Thread
        ############################################################################
        self.comms = comms_thread.Comms_Thread(self)

        if not self.comms.isInitialized():
            print "Error creating comms thread"
            return

        self.comms.register_callback("set_point", self.furnace_ctrl.parse_set_point_message)
        
        ############################################################################
        # Security Thread
        ############################################################################
        self.security = security_thread.Security_Thread(self, config = config)

        if not self.security.isInitialized():
            print "Error creating security thread"
            return
        
        
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

        
