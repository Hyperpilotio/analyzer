import bson
from flask.json import JSONEncoder
from flask import jsonify
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


def ensure_document_found(document, **kwargs):
    if document is None:
        response = jsonify(error="Document not found")
        response.status_code = 404
        return response
    else:
        if kwargs:
            document = {
                new_key: document[original_key]
                for new_key, original_key in kwargs.items()
            }
        return jsonify(document)


def shape_service_placement(deploy_json):
    result = {}
    result["name"] = deploy_json["name"]
    result["nodeMapping"] = []
    for task in deploy_json["kubernetes"]["taskDefinitions"]:
        if task["deployment"]["metadata"].get("namespace", "default") == "default":
            task["deployment"]["metadata"]["namespace"] = "default"
            for mapping in deploy_json["nodeMapping"]:
                if mapping["task"] == task["family"]:
                    result["nodeMapping"].append(mapping)

    nodes_in_default = set(map(lambda m: m["id"], result["nodeMapping"]))
    result["clusterDefinition"] = {
        "nodes": [node for node in deploy_json["clusterDefinition"]["nodes"]
                  if node["id"] in nodes_in_default]
    }
    return result
