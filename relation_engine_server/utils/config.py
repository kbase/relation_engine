"""
Load configuration data from environment variables.
"""
import os
import functools
from urllib.parse import urljoin


@functools.lru_cache(maxsize=1)
def get_config():
    """Load environment configuration data."""
    spec_path = os.environ.get('SPEC_PATH', '/spec')  # /spec
    spec_repo_path = os.path.join(spec_path, 'repo')  # /spec/repo

    spec_url = 'https://api.github.com/repos/kbase/relation_engine'
    spec_release_url = os.environ.get('SPEC_RELEASE_URL')
    spec_release_path = os.environ.get('SPEC_RELEASE_PATH')

    kbase_endpoint = os.environ.get('KBASE_ENDPOINT', 'https://ci.kbase.us/services')
    auth_url = os.environ.get('KBASE_AUTH_URL', urljoin(kbase_endpoint + '/', 'auth'))
    workspace_url = os.environ.get('KBASE_WORKSPACE_URL', urljoin(kbase_endpoint + '/', 'ws'))

    db_url = os.environ.get('DB_URL', 'http://arangodb:8529')
    db_name = os.environ.get('DB_NAME', '_system')
    db_user = os.environ.get('DB_USER', 'root')
    db_pass = os.environ.get('DB_PASS', '')
    db_readonly_user = os.environ.get('DB_READONLY_USER', db_user)
    db_readonly_pass = os.environ.get('DB_READONLY_PASS', db_pass)
    api_url = db_url + '/_db/' + db_name + '/_api'

    return {
        'auth_url': auth_url,
        'workspace_url': workspace_url,
        'kbase_endpoint': kbase_endpoint,
        'db_url': db_url,
        'api_url': api_url,
        'db_name': db_name,
        'db_user': db_user,
        'db_pass': db_pass,
        'db_readonly_user': db_readonly_user,
        'db_readonly_pass': db_readonly_pass,
        'spec_url': spec_url,
        'spec_release_url': spec_release_url,
        'spec_release_path': spec_release_path,
        'spec_paths': {
            'root': spec_path,  # /spec
            'release_id': os.path.join(spec_path, '.release_id'),
            'repo': spec_repo_path,  # /spec/repo
            'collections': os.path.join(spec_repo_path, 'spec', 'collections'),  # /spec/repo/spec/collections
            'datasets': os.path.join(spec_repo_path, 'spec', 'datasets'),
            'data_sources': os.path.join(spec_repo_path, 'spec', 'data_sources'),
            'stored_queries': os.path.join(spec_repo_path, 'spec', 'stored_queries'),
            'views': os.path.join(spec_repo_path, 'spec', 'views'),
        }
    }
