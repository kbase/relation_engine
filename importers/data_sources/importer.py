"""
Loads canonical (defined in the codebase) or separate (defined elsewhere) 
documents into the data_sources collection in the Relation Engine (RE).

This is a simple importer, as the data_sources load data is quite simple,
and also very similar to its ultimate form, requiring little transformation.

Note that the schema files are located in two places:
- spec/datasets/data_sources/definitions.yaml - reference types
- spec/datasets/data_sources/data_sources_nodes.yaml - definition of each data_source
      being loaded as a DataSource object
- spec/collections/data_sources/data_sources_nodes.yaml - replication of the DataSource
      object with the addition of a  _key property; all fields by reference to the
      definitions in spec/datasets/data_sources
"""
import argparse
import json
import os
import sys
import traceback
import requests
from relation_engine_server.utils.json_validation import (
    get_schema_validator,
)

QUIET = False


def get_default_dataset_schema_dir():
    """
    Returns the canonical location for the data_sources collection
    schema files.
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(
        dir_path, "../", "../", "spec", "datasets", "data_sources"
    )


def get_relative_dir(relative_path):
    """
    Utility function to return the full path for a given sub-path
    relative to the directory this source file resides in.
    """
    this_dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(this_dir_path, relative_path)


def note(note_type, message):
    """
    Print a nice message to the console, with an icon prefixing the given message.
    """
    if QUIET:
        return

    if note_type == 'info':
        icon = 'ℹ'
    elif note_type == 'success':
        icon = '✓'
    elif note_type == 'warning':
        icon = '⚠'
    elif note_type == 'error':
        icon = '🐛'
    else:
        icon = '?'
    print(f'[importer] {icon} {message}')


class Importer(object):
    def __init__(self, re_api_url=None, data_dir=None, dry_run=False, auth_token=False):
        if re_api_url is None:
            raise ValueError('The "re_api_url" parameter is required')
        self.re_api_url = re_api_url

        if auth_token is None:
            raise ValueError('The "auth_token" parameter is required')
        self.auth_token = auth_token

        self.dry_run = dry_run
        self.data_dir = data_dir

    def load_data(self):
        """
        Load the data_sources source data files located in `ROOT_DATA_PATH` via the 
        RE API located at `RE_API_URL`. Data files are validated with the jsonschema
        located in the path returned by `get_default_dataset_schema_dir()` defined
        above.

        The `dry_run` parameter will cause the loading process to stop just shy of 
        calling the RE API to store the data in the database. This is a useful for
        validating the data before actual loading, because the loading process is not
        transactional -- any documents loaded before an error is encountered will 
        be stored, leaving the collection in an inconsistent state.
        """
        note('info', 'Loading data')
        note('info', 'Parameters:')
        note('info', f'    re-api-url: {self.re_api_url}')
        note('info', f'    data-dir: {self.data_dir}')
        note('info', f'    dry-run: {self.dry_run}')

        is_error = False

        default_data_dir = get_relative_dir('data')
        # env_data_dir = self.get_config('ROOT_DATA_PATH', None)
        if self.data_dir is not None:
            note('info',
                 '     (using provided data dir')
            data_dir = self.data_dir
        else:
            note('info', '     (Taking data dir from default)')
            data_dir = default_data_dir
        note('info', f'     data_dir: "{data_dir}"')

        if not os.path.isdir(data_dir):
            raise Exception(f'data directory does not exist: {data_dir}')

        # The save_dataset method expects a list of documents
        # to save, so we are already set!
        schema_file = os.path.join(get_default_dataset_schema_dir(),
                                   'data_sources_nodes.yaml')
        validator = get_schema_validator(schema_file=schema_file)

        file_path = os.path.join(data_dir, 'data_sources.json')

        try:
            with open(file_path, 'r') as data_file:
                data_sources = json.load(data_file)
        except OSError as ose:
            note('error', 'Error loading import data file')
            return False

        data_sources_to_save = []
        for data_source in data_sources:
            if not validator.is_valid(data_source):
                for e in sorted(validator.iter_errors(data_source), key=str):
                    is_error = True
                    note('error', f'Validation error: {e.message}')
                continue
            else:
                data_source['_key'] = data_source['ns']
                data_sources_to_save.append(data_source)

        if is_error:
            note('error', 'Data did not validate')
            if self.dry_run:
                note('error', 'Dry run completed with errors')
            else:
                note('error', 'Due to errors, data will not be loaded')
            return False

        note('success', 'Data loaded and validated successfully')

        # if there are no errors then save the dataset unless this is a dry run
        if self.dry_run:
            note('success', 'Dry run completed successfully')
            note('warning', 'REMEMBER: Data not loaded')
        else:
            self.save_docs('data_sources_nodes', data_sources_to_save)
        return True

    def save_docs(self, collection, docs, on_duplicate="update"):
        """
        Saves the source_data docs into the RE database via the RE api
        """
        resp = requests.put(
            f'{self.re_api_url}/api/v1/documents',
            params={
                "collection": collection,
                "on_duplicate": on_duplicate
            },
            headers={
                "Authorization": self.auth_token
            },
            data="\n".join(json.dumps(d) for d in docs),
        )
        if not resp.ok:
            raise RuntimeError(resp.text)

        note('success', f"Saved docs to collection {collection}!")
        for key, value in resp.json().items():
            note('info', f'     {key}: {value}')
        return resp


def do_import(dry_run, data_dir, re_api_url, auth_token):
    """
    Wraps the loading process, passing the `dry_run` parameter to the 
    `load_data()` method. It traps exceptions, displaying them and exiting with
    the exit status code 1.
    """
    note('info', 'Starting Import')
    importer = Importer(dry_run=dry_run, data_dir=data_dir, re_api_url=re_api_url,
                        auth_token=auth_token)
    try:
        if not importer.load_data():
            sys.exit(1)
    except Exception as err:
        note('error', "Unhandled exception:")
        note('error', str(err))
        note('error', traceback.format_exc())
        sys.exit(1)
    finally:
        note('info', 'Finished Import')


def get_args():
    """
    Convenience function to define and parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Load data_sources data")

    # Required arguments
    required = parser.add_argument_group('required named arguments')
    required.add_argument(
        "--re-api-url",
        type=str,
        help="URL to an instance of Relation Engine",
        required=True
    )
    required.add_argument(
        "--auth-token",
        type=str,
        help="A KBase auth token",
        required=True
    )

    # Optional arguments; they have sensible defaults
    optional = parser.add_argument_group('optional named arguments')
    optional.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all actions of the importer, except loading the data.",
    )
    optional.add_argument(
        "--quiet",
        action="store_true",
        help="Shh, run quietly; do not print notes",
    )
    optional.add_argument(
        "--data-dir",
        type=str,
        help="Path to the import data file(s)",
    )

    return parser.parse_args()


def main():
    """
    The canonical main function is the interface between command line usage and 
    the import process defined above.
    """
    global QUIET
    args = get_args()
    QUIET = args.quiet
    do_import(dry_run=args.dry_run, data_dir=args.data_dir, re_api_url=args.re_api_url,
              auth_token=args.auth_token)
    sys.exit(0)


def init():
    """
    The init function wraps the standard `main` invocation method, rather than have
    the code exist out in the open. (Allows for testing of this logic.)
    """
    if __name__ == "__main__":
        main()


init()
