
import time
from utilities import config_utils
from utilities.thread_base import ThreadedPlugin

PLUGIN_NAME = "debug_thread"


class DebugThreadPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        if not self.enabled:
            return

        self.enabled = config_utils.get_config_param(config, PLUGIN_NAME, "enabled", self.logger)
        if self.enabled is None or self.enabled.lower() != "true":
            return

        if "collect_period" not in config.options(PLUGIN_NAME):
            self.collect_period = 10
        else:
            self.collect_period = float(config.get(PLUGIN_NAME, "collect_period", True))

        self._initialized = True
    
    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "enabled", "false")

    def get_plugin_info(self):

        result = ""

        if self.is_initialized():

            plugins = self.og.get_plugins()

            for plugin in plugins:

                plugin_name      = plugin.get_name()
                plugin_is_active = plugin.is_initialized()

                # <tr class="success">
                #     <td>Plugin 1</td>
                #     <td>Alive</td>
                # </tr>
                entry = '\n<tr class="'
                if plugin_is_active:
                    entry += 'success">\n'
                else:
                    entry += 'warning">\n'
                entry += '    <td>' + plugin_name + '</td>\n'
                if plugin_is_active:
                    entry += "    <td>active</td>\n"
                else:
                    entry += "    <td>inactive</td>\n"
                entry += '</tr>\n'

                result += entry

        return result

    def get_html(self):
        html = ""
        
        if self.is_initialized():

            html = """
                <div id="debug" class="jumbotron">
                    <div class="row">
                        <div class="col-md-12">
                            <h2>Debug:</h2>
                            <table class="table table-condensed">
                                <thead>
                                    <tr>
                                        <th>Plugin</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    %s
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            """ % self.get_plugin_info()
        
        return html
    
    def get_javascript(self):
        jscript = ""
        
        if self.is_initialized():
            jscript = ""
        
        return jscript
    
    def private_run(self):

        try:
            pass
        except:
            raise

    def private_run_cleanup(self):        
        pass
        
        
if __name__ == "__main__":
    import ConfigParser

    conf = ConfigParser.ConfigParser()

    DebugThreadPlugin.get_template_config(conf)

    dbg = DebugThreadPlugin(None, conf)
    
    if not dbg.is_initialized():
        print "ERROR: initialization failed"

    else:
        dbg.start()
        print "Collecting data (1 minute)..."
        time.sleep(60)
        dbg.stop()
