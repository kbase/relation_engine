import sys
import os
import yaml
import json
import shutil
import warnings

"""
python3 scripts/prepare_ontology.py scripts/test/data/data_sources.json fake_ontology
"""

PLACEHOLDER = "__NAME__"
BIN_PATH = os.path.dirname(os.path.abspath(__file__))
COLLECTIONS_PATH = os.path.join(BIN_PATH, "../spec/collections")
DATASOURCES_PATH = os.path.join(BIN_PATH, "../spec/data_sources")
DATAFILES_PATH = os.path.join(BIN_PATH, "data")
COLLECTIONS_DATAFILES = ["terms", "edges", "merges"]


def main():
    if len(sys.argv) <= 2:
        raise ValueError("data_source and/or namespace are missing")

    datasource = parse_input(sys.argv[1], sys.argv[2])

    prepare_collections_file(datasource, COLLECTIONS_PATH)
    prepare_data_sources_file(datasource, DATASOURCES_PATH)
    return


def parse_input(input, name):
    with open(input) as file:
        for d in json.load(file):
            if d.get("ns") == name:
                return d
        raise ValueError("no namespace: " + name)


def prepare_collections_file(datasource, collections_path):
    if not os.path.exists(collections_path):
        raise FileNotFoundError(collections_path + " doesn't exists")
    name, type = parse_namespace(datasource["ns"])
    target_dir = os.path.join(collections_path, name.upper())
    os.makedirs(target_dir, exist_ok=True)
    for f in COLLECTIONS_DATAFILES:
        source_file = os.path.join(DATAFILES_PATH, f + ".yaml")
        target_file = os.path.join(target_dir, name.upper() + "_" + f + ".yaml")
        data = ""
        with open(source_file, "r") as source:
            data = yaml.safe_load(source.read().replace(PLACEHOLDER, name.upper()))
        if not os.path.exists(target_file):
            with open(target_file, "w") as target:
                yaml.dump(data, target)
        else:
            warnings.warn(target_file + " exists")
    return target_dir


def prepare_data_sources_file(datasource, datasources_path):
    if not os.path.exists(datasources_path):
        raise FileNotFoundError(datasources_path + " doesn't exists")
    name, type = parse_namespace(datasource["ns"])
    target_file = os.path.join(datasources_path, datasource["ns"] + ".yaml")
    data = {
        "name": datasource["ns"],
        "category": type,
        "title": datasource["title"],
        "home_url": datasource["home_url"],
        "data_url": datasource["data_url"],
    }
    if not os.path.exists(target_file):
        with open(target_file, "w") as target:
            yaml.dump(data, target)
    else:
        warnings.warn(target_file + " exists")
    return target_file


def parse_namespace(ns):
    return tuple(ns.split("_"))


def clean_up_data(path):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)


if __name__ == "__main__":
    main()
