import dataclasses
import os


def load_from_env(prefix='RES_'):
    """Load all configuration vars from environment variables"""
    kwargs = {}
    for field in dataclasses.fields(ImporterConfig):
        var = prefix + field.name
        if var in os.environ:
            kwargs[field.name] = os.environ[prefix + field.name]
        elif isinstance(field.default, dataclasses._MISSING_TYPE):  # no default
            print(f"Missing required env var: {var}")
            exit(1)
    return ImporterConfig(**kwargs)


@dataclasses.dataclass
class ImporterConfig:
    """Defaults use test values"""
    auth_token: str = 'admin_token'
    api_url: str = 'http://localhost:5000'
