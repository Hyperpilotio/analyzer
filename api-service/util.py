import bson
from flask.json import JSONEncoder
from pymongo.cursor import Cursor
from werkzeug.routing import BaseConverter, ValidationError


class JSONEncoderWithMongo(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Cursor):
            return list(obj)
        elif isinstance(obj, bson.ObjectId):
            return str(obj)
        return super().default(obj)


class ObjectIdConverter(BaseConverter):

    def to_python(self, value):
        if not bson.ObjectId.is_valid(value):
            raise ValidationError()
        else:
            return bson.ObjectId(value)

    def to_url(self, value):
        return str(value)
