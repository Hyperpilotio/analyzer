import logging
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from .config import get_config


config = get_config()

client = MongoClient(
    host=config["MONGODB"]["HOST"],
    port=config["MONGODB"].getint("PORT"),
)

class Database(object):
    def __init__(self, name):
        self.name = name
        self.auth = (config["MONGODB"]["USERNAME"],
                     config["MONGODB"]["PASSWORD"])
        self._database = None

    def _get_database(self):
        if self._database is not None:
            return self._database
        db = client.get_database(self.name)
        db.authenticate(*self.auth)
        return db

    def __getitem__(self, collection):
        return self._get_database().get_collection(collection)

    def __getattribute__(self, attribute):
        try:
            return super().__getattribute__(attribute)
        except AttributeError:
            return getattr(self._get_database(), attribute)

configdb = Database(config["ANALYZER"]["CONFIGDB_NAME"])
metricdb = Database(config["ANALYZER"]["METRICDB_NAME"])
