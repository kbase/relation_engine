import sys
import os
import yaml
import json

"""
python3 scripts/prepare_ontology.py scripts/test/data_sources.json gaz_ontology
"""

__NAME = "__NAME__"
__BIN_PATH = os.path.dirname(os.path.abspath(__file__))
__COLLECTIONS_PATH = os.path.join(__BIN_PATH, "../spec/collections")
__DATASOURCES_PATH = os.path.join(__BIN_PATH, "../spec/data_sources")
__DATAFILES_PATH = os.path.join(__BIN_PATH, "data")
__COLLECTIONS_DATAFILES = ["terms", "edges", "merges"]


def main():
    input = sys.argv[1]
    ns = sys.argv[2]
    datasource = parse_input(input, ns)

    prepare_collections_file(datasource, __COLLECTIONS_PATH)
    prepare_data_sources_file(datasource, __DATASOURCES_PATH)

    return


def parse_input(input, name):
    with open(input) as file:
        for d in json.load(file):
            if d.get("ns") == name:
                return d


def prepare_collections_file(datasource, collections_path):
    name, type = parse_namespace(datasource["ns"])
    target_dir = os.path.join(collections_path, name.upper())
    os.makedirs(target_dir, exist_ok=True)
    for f in __COLLECTIONS_DATAFILES:
        source_file = os.path.join(__DATAFILES_PATH, f + ".yaml")
        target_file = os.path.join(target_dir, name.upper() + "_" + f + ".yaml")
        data = ""
        with open(source_file, "r") as source:
            data = yaml.safe_load(source.read().replace(__NAME, name.upper()))
        if not os.path.exists(target_file):
            with open(target_file, "w") as target:
                yaml.dump(data, target)
    return


def prepare_data_sources_file(datasource, datasources_path):
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
    return


def parse_namespace(ns):
    return tuple(ns.split("_"))


if __name__ == "__main__":
    main()
