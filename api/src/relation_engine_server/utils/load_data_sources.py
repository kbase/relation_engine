"""
Load the `data_sources` info from the relation engine spec.

The spec holds some information about some of the source data for the RE, such
as NCBI taxonomy, Gene Ontology, etc. This info may be used in the UI.
"""
import yaml
import os
import glob

from src.relation_engine_server.utils.config import get_config
from src.relation_engine_server.exceptions import NotFound

_CONF = get_config()
_PATH = _CONF['spec_paths']['data_sources']
print('_PATH is', _PATH)


def list_all():
    """
    List the names of all data sources.
    """
    names = []
    for path in glob.iglob(os.path.join(_PATH + '/*.yaml')):
        with open(path) as fd:
            contents = yaml.safe_load(fd)
            names.append(contents['name'])
    return names


def fetch_one(name):
    # Try .yaml or .yml
    try:
        with open(os.path.join(_PATH, f"{name}.yaml")) as fd:
            contents = yaml.safe_load(fd)
    except FileNotFoundError:
        raise NotFound(f"The data source with name '{name}' does not exist.")
    # Append the logo root url to be the ui-assets server url with the correct environment
    contents['logo_url'] = _CONF['kbase_endpoint'] + '/ui-assets' + contents['logo_path']
    del contents['logo_path']
    return contents
