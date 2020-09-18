import os
import requests
import tarfile
import tempfile
import shutil
import json
import glob
import yaml


from relation_engine_server.utils import arango_client
from relation_engine_server.utils.config import get_config

_CONF = get_config()


def download_specs(init_collections=True, release_url=None, reset=False):
    """Check and download the latest spec and extract it to the spec path."""
    if reset or not os.path.exists(_CONF['spec_paths']['root']):
        # Remove the spec directory, ignoring if it is already missing
        shutil.rmtree(_CONF['spec_paths']['root'], ignore_errors=True)
        # Directory to extract into
        temp_dir = tempfile.mkdtemp()
        # Download and extract a new release to /spec/repo
        if _CONF['spec_release_path']:
            _extract_tarball(_CONF['spec_release_path'], temp_dir)
        else:
            if _CONF['spec_release_url']:
                tarball_url = _CONF['spec_release_url']
            else:
                tarball_url = _fetch_github_release_url()
            resp = requests.get(tarball_url, stream=True)
            with tempfile.NamedTemporaryFile() as temp_file:
                # The temp file will be closed/deleted when the context ends
                # Download from the tarball url to the temp file
                _download_file(resp, temp_file.name)
                # Extract the downloaded tarball into the spec path
                _extract_tarball(temp_file.name, temp_dir)
        # At this point, the repo content is extracted into the temp directory
        # Get the top-level directory name from the tarball
        subdir = os.listdir(temp_dir)[0]
        # Move /tmp/temp_dir/x/spec into /spec
        shutil.move(os.path.join(temp_dir, subdir, 'spec'), _CONF['spec_paths']['root'])
        # Remove our temporary extraction directory
        shutil.rmtree(temp_dir)
    # Initialize all the collections
    if init_collections:
        do_init_collections()
        do_init_views()


def do_init_collections():
    """Initialize any uninitialized collections in the database from a set of collection schemas."""
    pattern = os.path.join(_CONF['spec_paths']['collections'], '**', '*.yaml')
    for path in glob.iglob(pattern):
        coll_name = os.path.basename(os.path.splitext(path)[0])
        with open(path) as fd:
            config = yaml.safe_load(fd)
        arango_client.create_collection(coll_name, config)


def do_init_views():
    """Initialize any uninitialized views in the database from a set of schemas."""
    pattern = os.path.join(_CONF['spec_paths']['views'], '**', '*.json')
    for path in glob.iglob(pattern):
        view_name = os.path.basename(os.path.splitext(path)[0])
        with open(path) as fd:
            config = json.load(fd)
        arango_client.create_view(view_name, config)


def _fetch_github_release_url():
    """Find the latest relation engine spec release using the github api."""
    # Download information about the latest release
    release_resp = requests.get(_CONF['spec_url'] + '/releases/latest')
    release_info = release_resp.json()
    if release_resp.status_code != 200:
        # This may be a github API rate usage limit, or some other error
        raise RuntimeError(release_info['message'])
    return release_info['tarball_url']


def _download_file(resp, path):
    """Download a streaming response as a file to path."""
    with open(path, 'wb') as tar_file:
        for chunk in resp.iter_content(chunk_size=1024):
            tar_file.write(chunk)


def _extract_tarball(tar_path, dest_dir):
    """Extract a gzipped tarball to a destination directory."""
    with tarfile.open(tar_path, 'r:gz') as tar:
        tar.extractall(path=dest_dir)


def _has_latest_spec(info):
    """Check if downloaded release info matches the latest downloaded spec."""
    release_id = str(info['id'])
    if os.path.exists(_CONF['spec_paths']['release_id']):
        with open(_CONF['spec_paths']['release_id'], 'r') as fd:
            current_release_id = fd.read()
        if release_id == current_release_id:
            return True
    return False


def _save_release_id(info):
    """Save a release ID as the latest downloaded spec."""
    release_id = str(info['id'])
    # Write the release ID to /spec/.release_id
    with open(_CONF['spec_release_id_path'], 'w') as fd:
        fd.write(release_id)


if __name__ == '__main__':
    download_specs()
