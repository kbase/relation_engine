import os
import requests
import tarfile
import tempfile
import shutil

from . import arango_client
from .config import get_config


def download_specs(init_collections=True, release_url=None):
    """Check and download the latest spec and extract it to the spec path."""
    config = get_config()
    # Remove the spec directory, ignoring if it is already missing
    shutil.rmtree(config['spec_paths']['root'], ignore_errors=True)
    # Recreate the spec directory so we have a clean slate, avoiding name conflicts
    os.makedirs(config['spec_paths']['root'])
    # Download and extract a new release to /spec/repo
    if 'SPEC_RELEASE_PATH' in os.environ:
        _extract_tarball(os.environ['SPEC_RELEASE_PATH'], config['spec_paths']['root'])
    else:
        if release_url:
            tarball_url = release_url
        if 'SPEC_RELEASE_URL' in os.environ:
            tarball_url = os.environ['SPEC_RELEASE_URL']
        else:
            tarball_url = _fetch_github_release_url()
        resp = requests.get(tarball_url, stream=True)
        with tempfile.NamedTemporaryFile() as temp_file:
            # The temp file will be closed/deleted when the context ends
            # Download from the tarball url to the temp file
            _download_file(resp, temp_file.name)
            # Extract the downloaded tarball into the spec path
            _extract_tarball(temp_file.name, config['spec_paths']['root'])
    # The files will be extracted into a directory like /spec/kbase-relation_engine_spec-xyz
    # We want to move that to /spec/repo
    _rename_directories(config['spec_paths']['root'], config['spec_paths']['repo'])
    # Initialize all the collections
    if init_collections:
        arango_client.init_collections()


def _fetch_github_release_url():
    """Find the latest relation engine spec release using the github api."""
    config = get_config()
    # Download information about the latest release
    release_resp = requests.get(config['spec_url'] + '/releases/latest')
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


def _rename_directories(dir_path, dest_path):
    """
    Rename directories under a path.
    The files will be extracted into a directory like /spec/kbase-relation_engine_spec-xyz
    We want to move it to /spec/repo.
    This could probably be improved to be less confusing.
    """
    for file_name in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file_name)
        if os.path.isdir(file_path):
            os.rename(file_path, dest_path)


def _has_latest_spec(info):
    """Check if downloaded release info matches the latest downloaded spec."""
    config = get_config()
    release_id = str(info['id'])
    if os.path.exists(config['spec_paths']['release_id']):
        with open(config['spec_paths']['release_id'], 'r') as fd:
            current_release_id = fd.read()
        if release_id == current_release_id:
            return True
    return False


def _save_release_id(info):
    """Save a release ID as the latest downloaded spec."""
    release_id = str(info['id'])
    config = get_config()
    # Write the release ID to /spec/.release_id
    with open(config['spec_release_id_path'], 'w') as fd:
        fd.write(release_id)
