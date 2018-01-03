import logging
from config import get_config
from functools import lru_cache


@lru_cache(maxsize=8)
def get_logger(name, log_level=None):
    assert log_level, "Please specify log level. (i.e. getlogger(__name__, log_level=(ANALYZER, LOGLEVEL)))"
    config = get_config()
    logger = logging.getLogger(name)
    log_format = "[%(asctime)s] [%(name)s:%(lineno)s] [%(levelname)s]\n%(message)s"
    logging.basicConfig(filename="diagnosis/logs/diagnosis", format=log_format)
    # handler = logging.StreamHandler()
    # logger.addHandler(handler)

    log_level = getattr(logging, config.get(*log_level))
    logger.setLevel(log_level)
    # handler.setLevel(log_level)

    return logger
