"""
Loads data sources into RE.

This is a simple importer, as the data_sources load data is quite simple,
and also very similar to its ultimate form, requiring little transformation.

Note that the schema files are located in two places:
- spec/datasets/data_sources/definitions.yaml - reference types
- spec/datasets/data_sources/data_sources_nodes.yaml - definition of each data_source
      being loaded as a DataSource object
- spec/collections/data_sources/data_sources_nodes.yaml - replication of the DataSource
      object with the addition of a  _key property; all fields by reference to the
      definigions in spec/datasets/data_sources

TODO: A DRYer design would be for the schemas in spec/collections to use an allOf to
extend the base DataSource type in spec/datasets.
However, the schema for collection definition files located in spec/collections
expects that the schemas in spec/collections be be an object.
I expect, though, that in many cases the collection and import data will be different
enough that there will be less overlap between the collections and import data than in
this case.
"""
import argparse
import json
import os
import sys
import traceback
import requests
import importers.utils.config as config
from relation_engine_server.utils.json_validation import (
    get_schema_validator,
)


def get_dataset_schema_dir():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(
        dir_path, "../", "../", "spec", "datasets", "data_sources"
    )


def get_relative_dir(path):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path = [dir_path] + [path]
    return os.path.join(*path)


def note(type, message):
    icon = ''
    if type == 'info':
        icon = 'ℹ'
    elif type == 'success':
        icon = '✓'
    elif type == 'warning':
        icon = '⚠';
    elif type == 'error':
        icon = '🐛'
    else:
        icon = '?'
    print(f'[importer] {icon} {message}')


class Importer(object):
    def __init__(self):
        pass

    def get_config_or_fail(self, key):
        if not hasattr(self, "_config"):
            self._configure()

        if key not in self._config:
            raise KeyError(f'No such config key: "{key}"')

        return self._config[key]

    def get_config(self, key, default_value):
        if not hasattr(self, "_config"):
            self._configure()

        if key not in self._config:
            return default_value

        return self._config[key]

    def _configure(self):
        self._config = config.load_from_env(extra_optional=["ROOT_DATA_PATH"])
        return self._config

    def load_data(self, dry_run=False):
        note('info', 'Loading data')
        note('info', 'Parameters:')
        note('info', f'     API_URL: {self.get_config_or_fail("API_URL")}')
        note('info', f'     dry run: {dry_run}')

        is_error = False

        # TODO: just get all files in the directory
        default_data_dir = get_relative_dir('data')
        env_data_dir = self.get_config('ROOT_DATA_PATH', None)
        if env_data_dir is not None:
            note('info', '     (Taking data dir from environment variable "RES_ROOT_DATA_PATH")')
            data_dir = env_data_dir
        else:
            note('info', '     (Taking data dir from default)')
            data_dir = default_data_dir
        note('info', f'     data_dir: "{data_dir}"')

        # The save_dataset method expects a list of documents
        # to save, so we are already set!
        schema_file = os.path.join(get_dataset_schema_dir(), "data_sources_nodes.yaml")
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
            if dry_run:
                note('error', 'Dry run completed with errors')
            else:
                note('error', 'Due to errors, data will not be loaded')
            return False

        note('success', 'Data loaded and validated successfully')

        # if there are no errors then save the dataset unless this is a dry run
        if dry_run:
            note('success', 'Dry run completed successfully')
            note('warning', 'REMEMBER: Data not loaded')
        else:
            self.save_docs('data_sources_nodes', data_sources_to_save)
        return True

    def save_docs(self, collection, docs, on_duplicate="update"):
        """  Saves the source_data docs via into the RE database via the RE api"""
        resp = requests.put(
            f'{self.get_config_or_fail("API_URL")}/api/v1/documents',
            params={
                "collection": collection,
                "on_duplicate": on_duplicate
            },
            headers={
                "Authorization": self.get_config_or_fail("AUTH_TOKEN")
            },
            data="\n".join(json.dumps(d) for d in docs),
        )
        if not resp.ok:
            raise RuntimeError(resp.text)

        note('success', f"Saved docs to collection {collection}!")
        for key, value in resp.json().items():
            note('info', f'     {key}: {value}')
        return resp


def do_import(dry_run=False):
    note('info', 'Starting Import')
    importer = Importer()
    try:
        importer.load_data(dry_run=dry_run)
    except Exception as err:
        note('error', "Unhandled exception:")
        note('error', str(err))
        note('error', traceback.format_exc())
        sys.exit(1)
    finally:
        note('info', 'Finished Import')


def get_args():
    argparser = argparse.ArgumentParser(description="Load data_sources data")
    argparser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Perform all actions of the importer, except loading the data.",
    )
    return argparser.parse_args()


def main():
    args = get_args()
    do_import(args.dry_run)
    sys.exit(0)


def init():
    if __name__ == "__main__":
        main()


init()
