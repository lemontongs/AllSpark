
import logging

logger = logging.getLogger('allspark.config_utils')

def check_config_section( config, config_sec ):
    if config_sec not in config.sections():
        if len( logger.handlers ):
            logger.warning(config_sec + " section missing from config file")
        else:
            print config_sec + " section missing from config file"
        return False
    return True

def get_config_param( config, config_sec, param ):
    if param not in config.options(config_sec):
        if len( logger.handlers ):
            logger.warning( param + " property missing from " + config_sec + " section" )
        else:
            print param + " property missing from " + config_sec + " section"
        return None
    return config.get( config_sec, param )
        