
import requests
import subprocess
from utilities.thread_base import ThreadedPlugin

PLUGIN_NAME = "update_thread"


class UpdateThreadPlugin(ThreadedPlugin):

    @staticmethod
    def get_dependencies():
        return []

    def __init__(self, object_group, config):
        ThreadedPlugin.__init__(self, config=config, object_group=object_group, plugin_name=PLUGIN_NAME)

        if not self.enabled:
            return

        if "check_every_seconds" not in config.options(PLUGIN_NAME):
            self.check_every_seconds = 86400
        else:
            self.check_every_seconds = int(config.get(PLUGIN_NAME, "check_every_seconds", True))

        self.current_version = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        self.latest = ""

        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "enabled", "false")
        config.set(PLUGIN_NAME, "check_every_seconds", "86400")

    def get_html(self):
        html = ""

        if self.is_initialized():

            html = """
            """

        return html

    def get_javascript(self):
        jscript = ""

        if self.is_initialized():
            jscript = ""

        return jscript

    def perform_update(self):

        # Do the update
        self.logger.info("Updating to version: " + self.latest)
        subprocess.call(["git", "pull"])

        # Schedule a reboot
        subprocess.call(["shutdown", "-r", "+5"])

        # Shutdown all the plugins (except this one)
        plugins = self.og.get_plugins()
        for plugin in plugins:
            if plugin.get_name() != PLUGIN_NAME:
                plugin.stop()

        # Signal this plugin to stop
        self._running = False

    def private_run(self):

        try:
            res = requests.get("www.lemontongs.com/allspark_latest")
            if res.status_code == 200:
                self.latest = res.text

                if self.latest != self.current_version:
                    self.perform_update()

        except requests.RequestException:
            pass

    def private_run_cleanup(self):
        pass
