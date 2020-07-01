"API User resource."

import http.client

import flask
from flask_cors import CORS

import datagraphics.user
from datagraphics import constants
from datagraphics import utils

blueprint = flask.Blueprint("api_user", __name__)

CORS(blueprint, supports_credentials=True)

@blueprint.route("/")
def all():
    "Information about all users."
    if not flask.g.am_admin:
        flask.abort(http.client.FORBIDDEN)
    users = [get_user_basic(u) for u in datagraphics.user.get_users()]
    return utils.jsonify({"users": users})

@blueprint.route("/<name:username>")
def display(username):          # XXX change to 'serve'
    "Information about the given user."
    user = datagraphics.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    # XXX Use 'allow' function
    if not datagraphics.user.am_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    user.pop("password", None)
    user.pop("apikey", None)
    set_links(user)
    return utils.jsonify(user)

@blueprint.route("/<name:username>/logs")
def logs(username):
    "Return all log entries for the given user."
    user = datagraphics.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    # XXX Use 'allow' function
    if not datagraphics.user.am_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    entity = {"type": "user"}
    entity.update(get_user_basic(user))
    return utils.jsonify({"entity": entity,
                          "logs": utils.get_logs(user["_id"])},
                         schema_url=flask.url_for("api_schema.logs",
                                                  _external=True))

def set_links(user):
    "Set the links in the user object."
    user["logs"] = {"href": flask.url_for(".logs", 
                                          username=user["username"],
                                          _external=True)}

def get_user_basic(user):
    "Return the basic JSON data for a user."
    return {"username": user["username"],
            "href": flask.url_for(".display",
                                  username=user["username"],
                                  _external=True)}

schema = {
    "$schema": constants.JSON_SCHEMA_URL,
    "title": "JSON Schema for API User resource.",
    "type": "object",
    "properties": {
        "$id": {"type": "string", "format": "uri"},
        "timestamp": {"type": "string", "format": "date-time"},
        "iuid": {"type": "string", "pattern": "^[0-9a-f]{32,32}$"},
        "created": {"type": "string", "format": "date-time"},
        "modified": {"type": "string", "format": "date-time"},
        "status": {
            "type": "string",
            "enum": ["pending", "enabled", "disabled"]
        },
        "username": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "role": {"type": "string", "enum": ["admin", "user"]},
        "logs": {
            "type": "object",
            "properties": {
                "href": {"type": "string", "format": "uri"}
            },
            "required": ["href"],
            "additionalProperties": False,
        }
    }
}
