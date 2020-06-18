import os


REQUIRED = []
OPTIONAL = ['AUTH_TOKEN', 'API_URL']
DEFAULTS = {
    'AUTH_TOKEN': 'admin_token',  # test default
    'API_URL': 'http://localhost:5000',  # test default
}


def load_from_env(extra_required=None, extra_optional=None, prefix='RES_'):
    """Load all configuration vars from environment variables"""
    conf = dict(DEFAULTS)
    required = list(REQUIRED) + (extra_required or [])
    optional = list(OPTIONAL) + (extra_optional or [])
    for field in required + optional:
        var = prefix + field
        if var in os.environ:
            conf[field] = os.environ[var]
        elif field in required:
            print(f"Missing required env var: {var}")
            exit(1)
    return conf
