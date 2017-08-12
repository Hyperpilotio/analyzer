from configparser import ConfigParser, NoOptionError
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def get_config():
    return Config()

class Config():
    def __init__():
        self._config = ConfigParser().read(Path(__file__).absolute().parent / "config.ini")

    def get(self, section, option, default=None):
        value = None
        try:
            value = config.get(section, option)
        except NoOptionError:
            pass

        if value is None:
            return default

        return value
