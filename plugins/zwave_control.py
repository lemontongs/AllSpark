#! /usr/bin/env python

import sys
import time
import logging
import traceback
from utilities.plugin import Plugin

from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption
from openzwave.object import ZWaveException

PLUGIN_NAME = "zwave_control"


class ZWaveControlPlugin(Plugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        Plugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        # Get parameters from the config file

        if not self.is_enabled():
            return

        # Initialize zwave library
        # Options
        try:
            opts = ZWaveOption(device="/dev/ttyUSB0",
                               config_path="/home/mlamonta/git/python-openzwave/openzwave/config/")
            opts.set_append_log_file(False)
            opts.set_console_output(False)
            opts.set_logging(False)
            opts.lock()
        except ZWaveException as e:
            self.logger.error(str(e))
            return

        # Network
        self.net = ZWaveNetwork(opts)

        self.logger.info("------------------------------------------------------------")
        self.logger.info("Waiting for network awake : ")
        self.logger.info("------------------------------------------------------------")
        for i in range(0, 300):
            if self.net.state >= self.net.STATE_AWAKED:
                self.logger.info("done")
                break
            else:
                time.sleep(1.0)

        if self.net.state < self.net.STATE_AWAKED:
            self.logger.warning("Network is not awake")
            return

        self.logger.info("------------------------------------------------------------")

        for node in self.net.nodes:
            self.logger.info("%s - %s / %s" % (self.net.nodes[node].node_id,
                                               self.net.nodes[node].manufacturer_name,
                                               self.net.nodes[node].product_name) )

        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "enabled", "true")
        
    def stop(self):
        if self.is_initialized():
            self.net.stop()

    def get_html(self):
        html = ""
        
        if self.is_initialized():
            html = """
            
            <div id="furnace" class="jumbotron">
                <div class="row">
                    <h2>Furnace State:</h2>
                    <div class="col-md-12">
                        <div id="furnace_chart_div"></div>
                    </div>
                </div>
            </div>
            
            """
        
        return html
    
    def get_javascript(self):
        jscript = ""
        
        if self.is_initialized():
            jscript = """
                function drawZwaveData()
                {
                    %s
                }
                ready_function_array.push( drawZwaveData )
                
            """ % "//blah"
        
        return jscript
    
#
# MAIN
#
if __name__ == "__main__":
    import ConfigParser
    
    logging.getLogger('').handlers = []
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
        
    conf = ConfigParser.ConfigParser()
    conf.add_section(PLUGIN_NAME)
    conf.set(PLUGIN_NAME, "enabled", "true")

    zc = ZWaveControlPlugin(None, conf)
    
    if not zc.is_initialized():
        print "NOT INITIALIZED"
    
    else:
        zc.start()
        time.sleep(80)
        zc.stop()
