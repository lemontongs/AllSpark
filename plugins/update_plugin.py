
import requests
import subprocess
import time
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
        self.current_version_time = self.get_version_time(self.current_version)

        self.logger.info("Current version: " + self.current_version + " time: " + str(self.current_version_time) )

        self.latest = ""

        self._initialized = True

    @staticmethod
    def get_template_config(config):
        config.add_section(PLUGIN_NAME)
        config.set(PLUGIN_NAME, "enabled", "true")
        config.set(PLUGIN_NAME, "check_every_seconds", "86400")

    def get_version_time(self, version):
        try:
            subprocess.call(["git", "remote", "update"])
            return int(subprocess.check_output(["git", "log", "-1", "--pretty=tformat:%%at", version]))
        except Exception as e:
            self.logger.error(e)
            return 0

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
        subprocess.call(["git", "checkout", self.latest])

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
            self.logger.info("Checking for update")
            res = requests.get("http://www.lemontongs.com/allspark_latest")

            if res.status_code == 200:
                self.latest = res.text

                new_version_time = self.get_version_time( self.latest )

                if new_version_time > self.current_version_time:
                    self.perform_update()

        except requests.RequestException as re:
            print re

        for _ in range(10):
            if self._running:
                time.sleep(1)

    def private_run_cleanup(self):
        pass

if __name__ == "__main__":
    import ConfigParser
    import logging

    logging.getLogger('').handlers = []
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    cfg = ConfigParser.ConfigParser()
    UpdateThreadPlugin.get_template_config(cfg)

    class TempOG:

        def __init__(self):
            pass

        @staticmethod
        def get_plugins():
            return []


    update = UpdateThreadPlugin( TempOG(), cfg )

    if update.is_initialized():
        update.start()

        time.sleep(10)

        update.stop()
    else:
        update.logger.error("Failed to initialize UpdateThreadPlugin")
