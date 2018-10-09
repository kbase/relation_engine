"""The primary router for the Biochem API v1."""
import flask

api_v1 = flask.Blueprint('api_v1', __name__)


@api_v1.route('/', methods=['GET'])
def root():
    """Root route for the API which lists all paths."""
    return flask.jsonify({'test': True})
