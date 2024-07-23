"""Contains the logger function
"""

import logging
import logging.config


def setup_logger(logger_config: str) -> logging.Logger:
    """Set up a logger using the given configuration path.
    :param logger_config: path to config file for logger
    :type logger_config: str
    :returns: the logger
    """
    logging.config.fileConfig(fname=logger_config, disable_existing_loggers=False)
    mupol_logger = logging.getLogger("MUPOL MPC logger")
    return mupol_logger
