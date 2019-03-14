"""
Load configuration data from environment variables.
"""
import os
from urllib.parse import urljoin


def get_config():
    """Load environment configuration data."""
    spec_path = os.environ.get('SPEC_PATH', '/spec')
    spec_repo_path = os.path.join(spec_path, 'repo')  # /spec/repo
    spec_schemas_path = os.path.join(spec_repo_path, 'schemas')  # /spec/repo/schemas
    spec_url = 'https://api.github.com/repos/kbase/relation_engine_spec'
    kbase_endpoint = os.environ.get('KBASE_ENDPOINT', 'https://ci.kbase.us/services')
    auth_url = os.environ.get('KBASE_AUTH_URL', urljoin(kbase_endpoint + '/', 'auth'))
    workspace_url = os.environ.get('KBASE_WORKSPACE_URL', urljoin(kbase_endpoint + '/', 'ws'))
    db_url = os.environ.get('DB_URL', 'http://localhost:8529')
    db_name = os.environ.get('DB_NAME', '_system')
    db_user = os.environ.get('DB_USER', 'root')
    db_pass = os.environ.get('DB_PASS', '')
    db_readonly_user = os.environ.get('DB_READONLY_USER', 'readonly')
    db_readonly_pass = os.environ.get('DB_READONLY_PASS', 'readonly')
    return {
        'auth_url': auth_url,
        'workspace_url': workspace_url,
        'kbase_endpoint': kbase_endpoint,
        'db_url': db_url,
        'db_name': db_name,
        'db_user': db_user,
        'db_pass': db_pass,
        'db_readonly_user': db_readonly_user,
        'db_readonly_pass': db_readonly_pass,
        'spec_url': spec_url,
        'spec_paths': {
            'release_id': os.path.join(spec_path, '.release_id'),
            'root': spec_path,
            'repo': spec_repo_path,
            'views': os.path.join(spec_repo_path, 'views'),
            'schemas': spec_schemas_path,
            'vertices': os.path.join(spec_schemas_path, 'vertices'),
            'edges': os.path.join(spec_schemas_path, 'edges')
        }
    }
