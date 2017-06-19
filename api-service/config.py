from configparser import ConfigParser
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_config():
    config = ConfigParser()
    config.read(Path(__file__).absolute().parent.parent / "config.ini")
    return config
