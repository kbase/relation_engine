"""
Loads data sources into RE.
This is a simple importer, as the data source load data is quite simple, 
and also in it's ultimate form, requiring no transformation.
All that is required is to:
- read in the source  data json
- uses the source_data schema to validate
- save as separate files, one  per node
- load and import those nodes 
- using the same source_data schema to validate
"""
import argparse
import json
import os
import traceback
import requests
import importers.utils.config as config
from relation_engine_server.utils.json_validation import (
    get_schema_validator,
)


def get_relative_dir(path):
    dir_path = os.path.dirname(os.path.realpath(__file__))

    if isinstance(path, str):
        path = [path]

    path = [dir_path] + path
    return os.path.join(*path)


def get_dataset_schema_dir():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # TODO:  factor out "data_sources"
    return os.path.join(
        dir_path, "../", "../", "spec", "datasets", "data_sources"
    )


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
        print('[importer] Loading data')
        print('[importer] Parameters:')
        print(f'[importer]     API_URL: {self.get_config_or_fail("API_URL")}')
        print(f'[importer]     dry run: {dry_run}')

        # TODO: just get all files in the directory
        default_data_dir = get_relative_dir('data')
        env_data_dir = self.get_config('ROOT_DATA_PATH', None)
        if env_data_dir is not None:
            print('[importer]     (Taking data dir from environment variable "RES_ROOT_DATA_PATH")')
            data_dir = env_data_dir
        else:
            print('[importer]     (Taking data dir from default)')
            data_dir = default_data_dir
        print(f'[importer]     data_dir: "{data_dir}"')

        # The save_dataset method expects a list of documents
        # to save, so we are already set!
        schema_file = os.path.join(get_dataset_schema_dir(), "data_sources_nodes.yaml")
        validator = get_schema_validator(schema_file=schema_file)

        file_path = os.path.join(data_dir, 'data_sources.json')
        with open(file_path, 'r') as data_file:
            data_sources = json.load(data_file)
            for data_source in data_sources:
                if not validator.is_valid(data_source):
                    for e in sorted(validator.iter_errors(data_source), key=str):
                        print(f'[importer] Validation error: {e.message}')
                        return

            print('[importer] Data loaded and validated successfully')

            # if there are no errors then save the dataset unless this is a dry run
            if dry_run:
                print('[importer] Dry run completed successfully')
                print('[importer] REMEMBER: Data not loaded')
            else:
                self.save_docs('data_sources_nodes', data_sources)

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

        print(f"[importer] Saved docs to collection {collection}!")
        for key, value in resp.json().items():
            print(f'[importer]     {key}: {value}')
        return resp


def main():
    argparser = argparse.ArgumentParser(description="Load data_sources data")
    argparser.add_argument(
        "--dry-run",
        dest="dry",
        action="store_true",
        help="Perform all actions of the parser, except loading the data.",
    )
    argparser.add_argument(
        "--output",
        default="text",
        help="Specify the format of any output generated. (text or json)",
    )
    args = argparser.parse_args()
    importer = Importer()
    try:
        importer.load_data(dry_run=args.dry)
    except Exception as err:
        print("[importer] Unhandled exception", err)
        print(traceback.format_exc())
        exit(1)
    finally:
        print('[importer] Done')


if __name__ == "__main__":
    main()
