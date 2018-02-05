import logging
from pprint import pformat
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pymongo import monitoring
from logger import get_logger
from config import get_config
config = get_config()
logger = get_logger(__name__, log_level=("MONGODB", "LOGLEVEL"))

class CommandLogger(monitoring.CommandListener):
    def started(self, event):
        dbname = event.database_name
        request_id = event.request_id
        if event.command_name == "find":
            collection = event.command["find"]
            filter_ = event.command.get("filter", {})
            projection = event.command.get("projection", {})
            if event.command.get("singleBatch", False):
                command = "find_one"
            else:
                command = "find"
            logger.debug(f"[{request_id}] {dbname}.{collection}.{command}({filter_}, {projection})")

    def succeeded(self, event):
        if event.command_name == "find":
            result = pformat(event.reply["cursor"]["firstBatch"])
            logger.debug(f"[{event.request_id}] Result:\n{result}")

    def failed(self, event):
        logger.error("Command {0.command_name} with request id "
                     "{0.request_id} on server {0.connection_id} "
                     "failed in {0.duration_micros} "
                     "microseconds".format(event))

monitoring.register(CommandLogger())

client = MongoClient(
    host=config.get("MONGODB", "HOST"),
    port=config.getint("MONGODB", "PORT"),
    serverSelectionTimeoutMS=5000,
    socketTimeoutMS=5000,
)


class Database(object):
    def __init__(self, name):
        self.name = name
        self.auth = (config.get("MONGODB", "USERNAME"),
                     config.get("MONGODB", "PASSWORD"))
        self._database = None

    def _get_database(self):
        if self._database is not None:
            return self._database
        db = client.get_database(self.name)
        logger.debug("Authenticating database: %s", self.name)
        res = db.authenticate(*self.auth)
        logger.debug("Database authenticated: %s, output: %s", self.name, res)
        self._database = db
        return db

    def __getitem__(self, collection):
        return self._get_database().get_collection(collection)

    def __getattribute__(self, attribute):
        try:
            return super().__getattribute__(attribute)
        except AttributeError:
            return getattr(self._get_database(), attribute)

configdb = Database(config.get("ANALYZER", "CONFIGDB_NAME"))
metricdb = Database(config.get("ANALYZER", "METRICDB_NAME"))
resultdb = Database(config.get("ANALYZER", "RESULTDB_NAME"))
jobdb = Database(config.get("ANALYZER", "JOBDB_NAME"))
