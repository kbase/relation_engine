import os
import requests
import tarfile
import tempfile
import shutil

from . import arango_client, spec_loader

_spec_dir = os.environ.get('SPEC_PATH', '/spec')
_api_url = 'https://api.github.com/repos/kbase/relation_engine_spec'
_release_id_path = os.path.join(_spec_dir, '.release_id')


def download_latest(reset=False, init_collections=True):
    """Check and download the latest spec and extract it to the spec path."""
    if reset and os.path.exists(_spec_dir):
        shutil.rmtree(_spec_dir)
    os.makedirs(_spec_dir, exist_ok=True)
    # Download and extract a new release to /spec/repo
    spec_repo_path = os.path.join(_spec_dir, 'repo')
    if 'SPEC_RELEASE_PATH' in os.environ:
        _extract_tarball(os.environ['SPEC_RELEASE_PATH'], _spec_dir)
    else:
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
            _extract_tarball(temp_file.name, _spec_dir)
    # The files will be extracted into a directory like /spec/kbase-relation_engine_spec-xyz
    # We want to move that to /spec/repo
    _rename_directories(_spec_dir, spec_repo_path)
    # Initialize all the collections
    if init_collections:
        schemas = spec_loader.get_schema_names()
        arango_client.init_collections(schemas)


def _fetch_github_release_url():
    # Download information about the latest release
    release_resp = requests.get(_api_url + '/releases/latest')
    release_info = release_resp.json()
    if release_resp.status_code != 200:
        # This may be a github API rate usage limit, or some other error
        raise Exception(release_info['message'])
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
    release_id = str(info['id'])
    if os.path.exists(_release_id_path):
        with open(_release_id_path, 'r') as fd:
            current_release_id = fd.read()
        if release_id == current_release_id:
            return True
    return False


def _save_release_id(info):
    """Save a release ID as the latest downloaded spec."""
    release_id = str(info['id'])
    # Write the release ID to /spec/.release_id
    with open(_release_id_path, 'w') as fd:
        fd.write(release_id)
