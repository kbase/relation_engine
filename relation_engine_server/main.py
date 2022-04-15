"""The main entrypoint for running the Flask server."""
import flask
import json
import os
from uuid import uuid4
import traceback
from jsonschema.exceptions import ValidationError

from relation_engine_server.api_versions.api_v1 import api_v1
from relation_engine_server.exceptions import (
    MissingHeader,
    UnauthorizedAccess,
    InvalidParameters,
    NotFound,
)
from relation_engine_server.utils.spec_loader import SchemaNonexistent
from relation_engine_server.utils import arango_client

app = flask.Flask(__name__)
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", True)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", str(uuid4()))
app.url_map.strict_slashes = False  # allow both `get /v1/` and `get /v1`
app.register_blueprint(api_v1, url_prefix="/api/v1")


def return_error(error_dict, code):
    """return the appropriate error structure and code

    Errors returned by the server have the basic format

    'error': {
        'message': <text explanation of error>,
    }

    The 'error' dictionary may have extra keys if there is additional information.

    This helper wraps the whole structure in an extra dict under the key 'error'.

    """
    return (flask.jsonify({"error": error_dict}), code)


@app.route("/", methods=["GET"])
def root():
    """Server status. develop is default branch"""
    if os.path.exists(".git/refs/heads/develop"):
        with open(".git/refs/heads/develop", "r") as fd:
            commit_hash = fd.read().strip()
    else:
        commit_hash = "unknown"
    arangodb_status = arango_client.server_status()
    repo_url = "https://github.com/kbase/relation_engine_api.git"
    body = {
        "arangodb_status": arangodb_status,
        "commit_hash": commit_hash,
        "repo_url": repo_url,
    }
    return flask.jsonify(body)


@app.errorhandler(json.decoder.JSONDecodeError)
def json_decode_error(err):
    """A problem parsing json."""
    resp = {
        "message": "Unable to parse JSON",
        "source_json": err.doc,
        "pos": err.pos,
        "lineno": err.lineno,
        "colno": err.colno,
    }
    return return_error(resp, 400)


@app.errorhandler(arango_client.ArangoServerError)
def arango_server_error(err):
    resp = {
        "message": str(err),
        "arango_message": err.resp_json["errorMessage"],
    }
    return return_error(resp, 400)


# Invalid request body json params or missing headers
@app.errorhandler(MissingHeader)
@app.errorhandler(InvalidParameters)
def generic_400(err):
    resp = {
        "message": str(err),
    }
    return return_error(resp, 400)


@app.errorhandler(ValidationError)
def validation_error(err):
    """Json Schema validation error."""
    # Refer to the documentation on jsonschema.exceptions.ValidationError:
    # https://python-jsonschema.readthedocs.io/en/stable/errors/
    resp = {
        "message": err.message,
        "failed_validator": err.validator,
        "value": err.instance,
        "path": list(err.absolute_path),
    }
    return return_error(resp, 400)


@app.errorhandler(UnauthorizedAccess)
def unauthorized_access(err):
    resp = {
        "message": "Unauthorized",
        "auth_url": err.auth_url,
        "auth_response": err.response,
    }
    return return_error(resp, 403)


@app.errorhandler(SchemaNonexistent)
def schema_does_not_exist(err):
    """General error cases."""
    resp = {
        "message": "Not found",
        "details": str(err),
        "name": err.name,
    }
    return return_error(resp, 404)


@app.errorhandler(NotFound)
@app.errorhandler(404)
def page_not_found(err):
    resp = {
        "message": "Not found",
    }
    if hasattr(err, "details"):
        resp["details"] = err.details
    return return_error(resp, 404)


@app.errorhandler(405)
def method_not_allowed(err):
    resp = {
        "message": "Method not allowed",
    }
    return return_error(resp, 405)


# Any other unhandled exceptions -> 500
@app.errorhandler(Exception)
@app.errorhandler(500)
def server_error(err):
    print("=" * 80)
    print("500 Unexpected Server Error")
    print("-" * 80)
    traceback.print_exc()
    print("=" * 80)
    resp = {"message": "Unexpected server error"}
    # TODO only set below two fields in dev mode
    resp["class"] = err.__class__.__name__
    resp["details"] = str(err)
    return return_error(resp, 500)


@app.after_request
def after_request(resp):
    # Log request
    print(" ".join([flask.request.method, flask.request.path, "->", resp.status]))
    # Enable CORS
    resp.headers["Access-Control-Allow-Origin"] = "*"
    env_allowed_headers = os.environ.get(
        "HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "Authorization, Content-Type"
    )
    resp.headers["Access-Control-Allow-Headers"] = env_allowed_headers
    # Set JSON content type and response length
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Content-Length"] = resp.calculate_content_length()
    return resp
