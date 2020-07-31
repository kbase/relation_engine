import json
import flask


def get_json_body():
    """
    Parse json out of a request body, if present.
    If the request body is empty, we return None rather than throwing any parsing errors.
    """
    json_body = None  # type: ignore
    req_data = flask.request.get_data()
    if req_data:
        json_body = json.loads(req_data)
    return json_body
