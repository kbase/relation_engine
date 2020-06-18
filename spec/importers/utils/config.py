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
    for field in required:
        if (prefix + field) not in os.environ:
            print(f"Missing required env var: {prefix + field}")
            exit(1)
    for field in required + optional:
        if (prefix + field) in os.environ:
            conf[field] = os.environ[prefix + field]
    return conf
