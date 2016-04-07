#! /usr/bin/env python

import time
import logging
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
                               config_path="/home/mlamonta/git/python-openzwave/openzwave/config/",
                               user_path="logs")
            opts.set_log_file("./logs/zwave.log")
            opts.set_save_log_level("Alert")
            opts.set_append_log_file(False)
            opts.set_console_output(False)
            opts.set_logging(True)
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

    @staticmethod
    def get_dimmer_code(uid, name, current_value):
        dimmer_html = """

         <div class="col-md-5">
             <h2>Dimmer</h2>
             <div class="input-group input-group-lg">
                 <input type="text" class="form-control" name="%s" value="%s">  <!-- DIMMER NAME, VALUE -->
                 <div class="input-group-btn">
                     <button name="%s"
                             type="button"
                             class="btn btn-primary"
                             onclick="updateZWave('%s')">Submit</button>
                 </div>
             </div>
             <script>
                 $("input[name='%s']").TouchSpin({
                     min: 0,
                     max: 100,
                     step: 1,
                     decimals: 0,
                     boostat: 5,
                     maxboostedstep: 10,
                     prefix: "Set:",
                     postfix: '%%'
                 });
             </script>
         </div>

         """ % (str(uid),
                current_value,
                str(uid) + "_btn",
                str(uid),
                str(uid) )

        return dimmer_html

    def get_html(self):
        html = ""
        
        if self.is_initialized():

            html = '<div id="zwave" class="jumbotron">'
            for node in self.net.nodes:

                node_html = ""

                switches = self.net.nodes[node].get_switches()
                for switch in switches:
                    node_html += "<h3>" + str(switches[switch].label) + "  " + str(switches[switch].data) + "</h3>"

                dimmers = self.net.nodes[node].get_dimmers()
                for dimmer in dimmers:
                    node_html += ZWaveControlPlugin.get_dimmer_code(dimmer,
                                                                    "Dimmer: " + str(dimmer),
                                                                    str(dimmers[dimmer].data))

                html += """
                    <div class="row">
                        <div class="col-md-12">
                            <h2>%d: %s - %s</h2>
                            %s
                        </div>
                    </div>
                """ % ( self.net.nodes[node].node_id,
                        self.net.nodes[node].manufacturer_name,
                        self.net.nodes[node].product_name,
                        node_html )

            html += "</div>"

        return html

    def parse_zwave_command_message(self, msg):
        try:
            if not self.is_initialized():
                self.logger.warning("Error zwave message while uninitialized")
                return

            if len(msg.split(',')) != 3:
                self.logger.warning("Error parsing zwave message")
                return

            self.logger.debug("Got message: " + msg)

            dev = msg.split(',')[1]
            val = int(msg.split(',')[2])

            # Find the right device and set its value
            for node in self.net.nodes:
                switches = self.net.nodes[node].get_switches()
                for switch in switches:
                    self.logger.debug("checking switch: " + str(switch))
                    if str(switch) == dev:
                        switches[switch].data = switches[switch].check_data(val)
                        self.logger.debug("match")
                        return

                dimmers = self.net.nodes[node].get_dimmers()
                for dimmer in dimmers:
                    self.logger.debug("checking dimmer: " + str(dimmer) )
                    if str(dimmer) == dev:
                        dimmers[dimmer].data = dimmers[dimmer].check_data(val)
                        self.logger.debug("match")
                        return

            self.logger.warning("device: " + dev + " not found")

        except Exception as e:
            self.logger.error("Exception in parse_zwave_command_message: " + e.message)

    def get_javascript(self):
        jscript = ""

        if self.is_initialized():
            jscript = """

                function updateZWave(device)
                {
                    var new_value = $("input[name='"+device+"']").val()

                    $.get("cgi-bin/web_control.py?set_zwave="+new_value+"&device="+device, function (result)
                    {
                        if (result.trim() == "OK")
                        {
                            $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                            $("button[name='"+device+"_btn']").toggleClass('btn-success');
                            setTimeout(function()
                            {
                                $("button[name='"+device+"_btn']").toggleClass('btn-success');
                                $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                            }, 5000);
                        }
                        else
                        {
                            $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                            $("button[name='"+device+"_btn']").toggleClass('btn-danger');
                            alert(result);
                            setTimeout(function()
                            {
                                $("button[name='"+device+"_btn']").toggleClass('btn-danger');
                                $("button[name='"+device+"_btn']").toggleClass('btn-primary');
                            }, 5000);
                        }
                    });
                }

                """
        
        return jscript
    
#
# MAIN
#
if __name__ == "__main__":
    import ConfigParser
    
    logging.getLogger('').handlers = []
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
        
    conf = ConfigParser.ConfigParser()
    conf.add_section(PLUGIN_NAME)
    conf.set(PLUGIN_NAME, "enabled", "true")

    zc = ZWaveControlPlugin(None, conf)
    
    if not zc.is_initialized():
        print "NOT INITIALIZED"
    
    else:
        time.sleep(10)
        zc.stop()
