"""Fetch documentation for the API."""
import flask

from . import schemas

docs = flask.Blueprint('docs', __name__)


@docs.route('/', methods=['GET'])
def root():
    """API documentation."""
    return flask.jsonify({
        'info': {
            'name': 'Relation Engine API',
            'description': 'Interface for updating or querying data in the KBase Relation Engine graph database.'
        },
        'api_prefix': '/api',
        'actions': {
            '/views GET': {
                'description': 'Fetch view names and (optionally) their AQL source code.',
                'auth': 'public',
                'query': {
                    'show_sources': {
                        'type': 'boolean',
                        'default': False,
                        'description': 'Whether to show the AQL source code for each view.'
                    }
                },
                'responses': {
                    '200': {
                        'schema': ['view'],
                        'description': 'A list of views with names and (optionally) AQL source.'
                    },
                    'not_ok': {'schema': 'error'}
                }
            },
            '/query POST': {
                'description': 'Execute a view as a query against the database.',
                'auth': 'bearer',
                'query': {
                    'view_name': {
                        'description': 'Name of the view that we want to use for the query.',
                        'type': 'string'
                    }
                },
                'body': {
                    'description': 'Arguments for the query. These go into the bind variables in the AQL.',
                    'type': 'object'
                },
                'responses': {
                    '200': {
                        'schema': 'query_results',
                        'description': 'Resulting data from running the query'
                    },
                    'not_ok': {'schema': 'error'}
                }
            },
            '/schemas GET': {
                'description': 'Fetch available schema names and optionally their JSON sources.',
                'auth': 'public',
                'query': {
                    'show_sources': {
                        'type': 'boolean',
                        'description': 'Whether to show the JSON source for each schema.'
                    }
                },
                'responses': {
                    '200': {
                        'schema': {
                            'type': 'array',
                            'item': {'schema': 'view'}
                        },
                        'description': 'Array of schema name and (optionally) schema content.'
                    },
                    'not_ok': {'schema': 'error'}
                }
            },
            '/documents PUT': {
                'description': 'Create, update, or replace documents in the database in a certain collection.',
                'auth': 'bearer',
                'query': {
                    'on_duplicate': {
                        'description': 'How to handle duplicate documents based on a "_key" match.',
                        'type': 'string',
                        'enum': ['error', 'update', 'replace', 'ignore']
                    }
                },
                'responses': {
                    '200': {'description': 'Successful save.'},
                    'not_ok': {'schema': 'error'}
                }
            }
        },
        'schemas': {
                'error': schemas.error,
                'view': schemas.view,
                'query_results': schemas.query_results,
                'document_save_results': schemas.document_save_results
        }
    })
