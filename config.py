import os
from configparser import ConfigParser
from functools import lru_cache

@lru_cache(maxsize=1)
def get_config():
    config = EnvironInterpolatedConfigParser()
    config.read("config.ini")
    return config

class EnvironInterpolatedConfigParser(ConfigParser):
    def get(self, section, option, **kwargs):
        return os.environ.get(
            f"{section}_{option}".upper(),
            default=super().get(section, option, **kwargs)
        )
