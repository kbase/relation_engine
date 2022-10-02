import os
import requests
import tarfile
import tempfile
import shutil
import json
import yaml
from typing import Optional

from relation_engine_server.utils import arango_client
from relation_engine_server.utils.config import get_config
from relation_engine_server.utils.ensure_specs import ensure_all
from spec.validate import get_schema_type_paths

_CONF = get_config()


def download_specs(
    init_collections: bool = True,
    release_url: Optional[str] = None,
    reset: bool = False,
) -> Optional[str]:
    """
    Check and download the latest spec and extract it to the spec path.
    Returns:
        The name or path of the release used to update the specs
    """
    update_name: Optional[str] = None
    if reset or not os.path.exists(_CONF["spec_paths"]["root"]):
        # Remove the spec directory, ignoring if it is already missing
        shutil.rmtree(_CONF["spec_paths"]["root"], ignore_errors=True)
        # Directory to extract into
        temp_dir = tempfile.mkdtemp()
        # Download and extract a new release to /spec/repo
        if _CONF["spec_release_path"]:
            update_name = _CONF["spec_release_path"]
            _extract_tarball(_CONF["spec_release_path"], temp_dir)
        else:
            if _CONF["spec_release_url"]:
                tarball_url = _CONF["spec_release_url"]
            else:
                tarball_url = _fetch_github_release_url()
            update_name = tarball_url
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
        shutil.move(os.path.join(temp_dir, subdir, "spec"), _CONF["spec_paths"]["root"])
        # Remove our temporary extraction directory
        shutil.rmtree(temp_dir)
    # Initialize all the collections
    if init_collections:
        do_init_collections()
        do_init_views()
        do_init_analyzers()
    # Check that local specs have matching server specs
    # Necessary because creating resources like indexes
    # does not overwrite any pre-existing indexes
    failed_names = ensure_all()
    if any([name for schema_type, names in failed_names.items() for name in names]):
        raise RuntimeError(
            "Some local specs have no matching server specs:"
            "\n" + json.dumps(failed_names, indent=4)
        )
    return update_name


def do_init_collections():
    """Initialize any uninitialized collections in the database from a set of collection schemas."""
    for path in get_schema_type_paths("collection"):
        coll_name = os.path.basename(os.path.splitext(path)[0])
        with open(path) as fd:
            config = yaml.safe_load(fd)
        arango_client.create_collection(coll_name, config)


def do_init_views():
    """Initialize any uninitialized views in the database from a set of schemas."""
    for path in get_schema_type_paths("view"):
        view_name = os.path.basename(os.path.splitext(path)[0])
        with open(path) as fd:
            config = json.load(fd)
        arango_client.create_view(view_name, config)


def do_init_analyzers():
    for path in get_schema_type_paths("analyzer"):
        analyzer_name = os.path.basename(os.path.splitext(path)[0])
        with open(path) as fd:
            config = json.load(fd)
        arango_client.create_analyzer(analyzer_name, config)


def _fetch_github_release_url():
    """Find the latest relation engine spec release using the github api."""
    # Download information about the latest release
    release_resp = requests.get(_CONF["spec_repo_url"] + "/releases/latest")
    release_info = release_resp.json()
    if release_resp.status_code != 200:
        # This may be a github API rate usage limit, or some other error
        raise RuntimeError(release_info["message"])
    return release_info["tarball_url"]


def _download_file(resp, path):
    """Download a streaming response as a file to path."""
    with open(path, "wb") as tar_file:
        for chunk in resp.iter_content(chunk_size=1024):
            tar_file.write(chunk)


def _extract_tarball(tar_path, dest_dir):
    """Extract a gzipped tarball to a destination directory."""
    with tarfile.open(tar_path, "r:gz") as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner) 
            
        
        safe_extract(tar, path=dest_dir)


def _has_latest_spec(info):
    """Check if downloaded release info matches the latest downloaded spec."""
    release_id = str(info["id"])
    if os.path.exists(_CONF["spec_paths"]["release_id"]):
        with open(_CONF["spec_paths"]["release_id"], "r") as fd:
            current_release_id = fd.read()
        if release_id == current_release_id:
            return True
    return False


def _save_release_id(info):
    """Save a release ID as the latest downloaded spec."""
    release_id = str(info["id"])
    # Write the release ID to /spec/.release_id
    with open(_CONF["spec_release_id_path"], "w") as fd:
        fd.write(release_id)


if __name__ == "__main__":
    download_specs()
