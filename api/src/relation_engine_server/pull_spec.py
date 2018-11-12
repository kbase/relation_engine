import os
import subprocess  # nosec

from . import arango_client, spec_loader

_spec_dir = os.environ.get('SPEC_PATH', '/spec')


def pull_spec():
    """Download the spec repo to get any updates."""
    # This always git-pulls no matter what. We may want to throttle or change this in the future.
    subprocess.check_output(['git', '-C', _spec_dir, 'pull', 'origin', 'master'])  # nosec
    # Initialize any collections
    arango_client.init_collections(spec_loader.get_schema_names())


# Run from bash with `python -m src.relation_engine_server.pull_spec`
if __name__ == '__main__':
    print('Pulling relation engine spec..')
    pull_spec()
    print('..done.')
