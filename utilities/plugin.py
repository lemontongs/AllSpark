
import logging
from utilities import config_utils


class Plugin:
    def __init__(self, plugin_name, config=None, object_group=None):
        self._initialized = False
        self.name = plugin_name
        self.og = object_group
        self.logger = logging.getLogger('AllSpark.' + plugin_name)
        self.config = config

        # Modified in config
        self._enabled = True

        if config is not None:
            self.verify_common_plugin_config_items()

    def verify_common_plugin_config_items(self):

        if not config_utils.check_config_section(self.config, self.name, self.logger):
            self._enabled = False
        else:
            enabled = config_utils.get_config_param(self.config, self.name, "enabled", self.logger)
            if enabled is None:
                self.logger.warning("Section: '" + self.name + "' is missing the 'enabled' property in the config file")
                self._enabled = False
            elif enabled.lower() != "true":
                self._enabled = False

    def is_initialized(self):
        return self._initialized

    def is_enabled(self):
        return self._enabled

    def get_name(self):
        return self.name

    # Must be overridden!
    @staticmethod
    def get_dependencies():
        raise NotImplementedError
