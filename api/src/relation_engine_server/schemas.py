"""Fetch schemas for the API."""

# An AQL stored query
view = {
    'type': 'object',
    'required': ['name'],
    'description': 'Stored query for use in fetching graph data.',
    'properties': {
        'name': {
            'type': 'string',
            'description': 'Unique name of the view'
        },
        'source': {
            'type': 'string',
            'description': 'AQL source code for this schema (if requested).'
        }
    }
}

# An error response (any non-2xx)
error = {
    'type': 'object',
    'required': ['error', 'request_id', 'error_code'],
    'properties': {
        'error': {
            'type': 'string',
            'description': 'Error message.'
        },
        'error_code': {
            'type': 'string',
            'description': 'Code representing the error type.'
        },
        'request_id': {
            'type': 'string',
            'description': 'Unique ID of the request, used in fetching error logs.'
        }
    }
}

# Results from running a query
query_results = {
    'description': 'Resulting status and data from running a query.',
    'type': 'object',
    'required': ['has_more', 'data', 'count', 'cursor_id'],
    'properties': {
        'has_more': {
            'type': 'boolean',
            'description': 'Whether there are more results in the query. If so, use the cursor ID to fetch them.'
        },
        'data': {
            'type': 'array',
            'description': 'Array of result data, up to a maximum of 100 results.',
            'item': {'type': 'object'}
        },
        'count': {
            'type': 'integer',
            'description': 'Total count of resulting documents.'
        },
        'cursor_id': {
            'type': 'string',
            'description': ('If has_more is true, then this is set to an ID that you can use'
                            ' to fetch additional results.')
        }
    }
}

# Results from bulk-saving documents
document_save_results = {
    'description': 'Result info after bulk-saving documents in the database.',
    'type': 'object',
    'properties': {
        'created': {
            'type': 'integer',
            'description': 'Number of documents created.'
        },
        'updated': {
            'type': 'integer',
            'description': 'Number of documents updated.'
        },
        'replaced': {
            'type': 'integer',
            'description': 'Number of documents replaced.'
        }
    }
}

# Schema inception ^_^
schema = {
    'description': 'A stored schema that describes the validation for a collection in the database.',
    'type': 'object',
    'required': ['name'],
    'properties': {
        'name': {
            'type': 'string',
            'description': 'Unique name of the schema (maps to a name of a collection, such as "genes").'
        },
        'source': {
            'type': 'object',
            'description': 'JSON schema object used for validating a collection of documents in the database.'
        }
    }
}
