
import os
import logging
import traceback

import config_utils
import dynamic_module_load

# Helper plugins
import comms_thread
import spark_interface
import twilio_interface
import message_broadcast

logger = logging.getLogger('allspark.object_group')

CONFIG_SEC_NAME = "general"

THIS_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join( THIS_SCRIPT_DIR, "..", "plugins" )

plugin_dir_classes = dynamic_module_load.get_classes_from_folder(PLUGINS_DIR)
plugin_classes = []

# Create a list of classes that have a name ending with "Plugin"
for (class_name, class_instance) in plugin_dir_classes:
    if class_name.endswith("Plugin"):
        plugin_classes.append( (class_name, class_instance) )


class ObjectGroup:
    def __init__(self, config):
        self._initialized = False
        self._running = False

        self._plugins = []

        # Load helper objects
        # TODO: remove this somehow, possibly make them plugins also?

        ############################################################################
        # Spark Interface
        ############################################################################
        if not config_utils.check_config_section(config, CONFIG_SEC_NAME):
            return

        spark_auth_filename = \
            config_utils.get_config_param( config, CONFIG_SEC_NAME, "spark_auth_file", logger)
        if spark_auth_filename is None:
            return

        self.spark = spark_interface.SparkInterface(spark_auth_filename)

        if not self.spark.is_initialized():
            logger.error( "Failed to create spark interface" )
            return

        ############################################################################
        # Comms Thread
        ############################################################################
        self.comms = comms_thread.CommsThread(port = 5555)

        if not self.comms.is_initialized():
            logger.error( "Failed to create comms thread" )
            return

        ############################################################################
        # Twilio
        ############################################################################
        self.twilio = twilio_interface.TwilioInterface(config = config)

        if not self.twilio.is_initialized():
            logger.warning( "Failed to create twilio interface" )
            return

        ############################################################################
        # UDP Multicast
        ############################################################################
        self.broadcast = message_broadcast.MessageBroadcast()

        if not self.broadcast.is_initialized():
            logger.warning( "Failed to create broadcast interface" )
            return

        ############################################################################
        # Load all Plugin classes defined in the plugins directory
        ############################################################################

        ordered_plugins = self.check_dependencies( plugin_classes )

        if ordered_plugins is None:
            logger.error("DEPENDENCY ERROR")
            return

        # Load each of the plugin classes
        for (plugin_class_name, plugin_class_instance) in ordered_plugins:

            try:
                # Make sure its dependencies loaded ok
                all_dependencies_met = True
                for dependency in plugin_class_instance.get_dependencies():
                    dependency_ok = False
                    for loaded_plugin in self._plugins:
                        if loaded_plugin.__class__.__name__ == dependency and \
                                loaded_plugin.is_initialized() and \
                                loaded_plugin.is_enabled():
                            dependency_ok = True
                            break

                    if not dependency_ok:
                        all_dependencies_met = False
                        break

                if not all_dependencies_met:
                    logger.warning("Failed to load Plugin: " + plugin_class_name + " dependencies not met")
                    continue

                # Dependencies met, continue to load this plugin
                plugin = plugin_class_instance( self, config )

                # Add the plugin as an attribute to this class by name
                setattr(self, plugin.get_name(), plugin)

                # Add the plugin to the list of plugins
                self._plugins.append( plugin )

                # Report status
                if plugin.is_initialized():
                    logger.info("Loaded Plugin: " + plugin.get_name())
                elif not plugin.is_enabled():
                    logger.info("Plugin disabled: " + plugin_class_name)
                else:
                    logger.warning("Failed to load Plugin: " + plugin_class_name)

            except TypeError as te:
                traceback.print_exc()
                logger.error("Failed to load Plugin: " + plugin_class_name + "  " + te.message)
                return

        # Register the set_point callback
        if hasattr(self, "set_point"):
            set_p = getattr(self, "set_point")
            if hasattr(set_p, "parse_set_point_message"):
                self.comms.register_callback("set_point", set_p.parse_set_point_message)

        self._initialized = True

    def is_initialized(self):
        return self._initialized

    def is_running(self):
        return self._running

    def get_plugins(self):
        return self._plugins

    def start(self):
        if self.is_initialized() and not self.is_running():
            for plugin in self.get_plugins():
                if plugin.is_initialized() and hasattr(plugin, 'start') and callable(getattr(plugin, 'start')):
                    plugin.start()

            self._running = True

    def stop(self):
        if self.is_initialized() and self.is_running():
            for plugin in self.get_plugins():
                if hasattr(plugin, 'stop') and callable(getattr(plugin, 'stop')):
                    plugin.stop()

            self._running = False

    def get_javascript(self):
        result = ""
        for plugin in self.get_plugins():
            if hasattr(plugin, 'get_javascript') and callable(getattr(plugin, 'get_javascript')):
                result += plugin.get_javascript()
        return result

    def get_html(self):
        result = ""
        for plugin in self.get_plugins():
            if hasattr(plugin, 'get_html') and callable(getattr(plugin, 'get_html')):
                result += plugin.get_html()
        return result

    @staticmethod
    def check_dependencies(classes_to_sort):

        num_classes = len(classes_to_sort)
        ordered_classes = []

        # First pass, add plugins with no dependencies
        for plugin_name, plugin_class in classes_to_sort:
            if len(plugin_class.get_dependencies()) == 0:
                ordered_classes.append( (plugin_name, plugin_class) )
                logger.debug( "P0: " + plugin_name + " " + str( plugin_class.get_dependencies() ) )

        # Remaining passes, determine the order of the remaining classes
        num_classes_remaining = num_classes - len(ordered_classes)
        for pass_num in range(num_classes_remaining):
            for plugin_name, plugin_class in classes_to_sort:

                # skip the already sorted items
                if (plugin_name, plugin_class) in ordered_classes:
                    continue

                dependencies = plugin_class.get_dependencies()

                dependencies_met = True
                for dependency in dependencies:
                    if dependency not in [ c for (c, _) in ordered_classes ]:
                        dependencies_met = False
                        break

                if dependencies_met:
                    ordered_classes.append( (plugin_name, plugin_class) )
                    logger.debug( "P" + str(pass_num + 1) + ": " +
                                  plugin_name + " " +
                                  str( plugin_class.get_dependencies() ))

                if len(ordered_classes) == len(classes_to_sort):
                    return ordered_classes

        if len(ordered_classes) != len(classes_to_sort):
            return []

    @staticmethod
    def get_template_config(config):
        for plugin_class in plugin_classes:
            if hasattr(plugin_class, 'get_template_config') and callable(getattr(plugin_class, 'get_template_config')):
                config = plugin_class.get_template_config(config)
        return config


if __name__ == '__main__':
    import ConfigParser

    cfg = ConfigParser.ConfigParser()
    cfg.read(os.path.join(THIS_SCRIPT_DIR, "..", "data", "config.cfg"))

    og = ObjectGroup( cfg )
