
def check_config_section( config, config_sec, logger=None ):
    if config_sec not in config.sections():
        if logger is not None:
            logger.warning(config_sec + " section missing from config file")
        else:
            print config_sec + " section missing from config file"
        return False
    return True


def get_config_param( config, config_sec, param, logger=None ):
    if param not in config.options(config_sec):
        if logger is not None:
            logger.warning( param + " property missing from " + config_sec + " section" )
        return None
    return config.get( config_sec, param )
