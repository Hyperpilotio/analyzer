from configparser import ConfigParser, NoOptionError
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def get_config():
    return Config()

class Config():
    def __init__(self):
        config = ConfigParser()
        config.read(Path(__file__).absolute().parent / "config.ini")
        self._config = config

    def get(self, section, option, default=None):
        value = None
        try:
            value = self._config.get(section, option)
        except NoOptionError:
            pass

        if value is None:
            return default

        return value

    def getint(self, *args):
        return int(self.get(*args))

    def getfloat(self, *args):
        return float(self.get(*args))
