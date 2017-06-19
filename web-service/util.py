from flask.json import JSONEncoder
from bson.objectid import ObjectId
from pymongo.cursor import Cursor


class JSONEncoderWithMongo(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Cursor):
            return list(obj)
        elif isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)
