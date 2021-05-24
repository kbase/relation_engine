"""
Validate everything in this repo, such as syntax, structure, etc.
"""
import sys
import os
import glob
import requests
import json
from jsonschema.exceptions import ValidationError

from relation_engine_server.utils.config import get_config
from relation_engine_server.utils.wait_for import wait_for_arangodb
from relation_engine_server.utils.json_validation import run_validator

_CONF = get_config()
_BASE_DIR = "/app/spec"

_VALID_SCHEMA_TYPES = {
    "data_source": {
        "file": os.path.join(_BASE_DIR, "data_source_schema.yaml"),
        "plural": "data_sources",
    },
    "stored_query": {
        "file": os.path.join(_BASE_DIR, "stored_query_schema.yaml"),
        "plural": "stored_queries",
    },
    "collection": {
        "file": os.path.join(_BASE_DIR, "collection_schema.yaml"),
        "plural": "collections",
    },
    "view": {
        "file": os.path.join(_BASE_DIR, "view_schema.yaml"),
        "plural": "views",
    },
}


def validate_all(schema_type, directory=None):
    """
    Validate the syntax of all schemas of type schema_type in a specified directory

    :param schema_type: (string)  the schema type to validate
    :param directory:   (string)  the directory to look in.
                                  If not specified, the default directory for the schema_type
                                  will be used.
    """
    if schema_type not in _VALID_SCHEMA_TYPES.keys():
        raise ValueError(f"No validation schema found for '{schema_type}'")

    err_files = []
    n_files = 0
    names = set()  # type: set
    if directory is None:
        type_dir_name = _VALID_SCHEMA_TYPES[schema_type]["plural"]
        directory = _CONF["spec_paths"][type_dir_name]

    print(f"Validating {schema_type} schemas in {directory}...")

    for path in glob.iglob(os.path.join(directory, "**", "*.*"), recursive=True):
        if path.endswith(".yaml") or path.endswith(".json"):
            n_files += 1
            try:
                data = validate_schema(path, schema_type)
                # Check for any duplicate schema names
                name = data["name"]
                if name in names:
                    raise ValueError(f"Duplicate queries named '{name}'")
                else:
                    names.add(name)

            except Exception as err:
                print(f"✕ {path} failed validation")
                print(err)
                err_files.append([path, err])

    if not n_files:
        print("No schema files found")
        return

    if err_files:
        err_file_str = "\n".join([i[0] for i in err_files])
        raise ValidationError(
            f"{directory} failed validation\n" f"files with errors:\n" f"{err_file_str}"
        )

    # all's well
    print("...all valid.")
    return


def validate_all_by_type(validation_base_dir=None):
    """
    Validate the syntax of all schemas of all types in validation_base_dir

    Assumes that the schemas will be set up in parent directories named with the plural form
    of the schema type name, i.e. all collection schemas in the 'collections' dir, all views
    in the 'views' dir, etc.

    :param validation_base_dir:   (string) the directory to look in.
                                  If not specified, the default directory from the config
                                  will be used

    :return n_errors:             (int) the number of errors encountered

    """

    n_errors = []
    print(f'validate_all_by_type, {validation_base_dir}')
    for schema_type in sorted(_VALID_SCHEMA_TYPES.keys()):
        try:
            if validation_base_dir is None:
                validate_all(schema_type)
            else:
                directory = os.path.join(
                    validation_base_dir, _VALID_SCHEMA_TYPES[schema_type]["plural"]
                )
                validate_all(schema_type, directory)
        except Exception as err:
            n_errors.append(err)
        print("\n")

    if n_errors:
        print("Validation failed!\n")
        print("\n\n".join([str(n) for n in n_errors]))
    else:
        print("Validation succeeded!")

    return len(n_errors)


def validate_schema(path, schema_type):
    """Validate a single file against its schema"""

    if schema_type not in _VALID_SCHEMA_TYPES.keys():
        raise ValueError(f"No validation schema found for '{schema_type}'")

    return globals()["validate_" + schema_type](path)


def validate_collection(path):
    print(f"  validating {path}..")

    # JSON schema for vertex and edge collection schemas found in /schema
    collection_schema_file = _VALID_SCHEMA_TYPES["collection"]["file"]
    data = run_validator(schema_file=collection_schema_file, data_file=path)
    namecheck_schema(path, data)

    # Make sure it can be used as a JSON schema
    # If the schema is invalid, a SchemaError will get raised
    # Otherwise, the schema will work and a ValidationError will get raised (what we want)
    try:
        run_validator(data={}, schema=data["schema"])
    except ValidationError:
        pass
    except Exception as err:
        print("=" * 80)
        print("Unable to load schema in " + path)
        raise err

    required = data["schema"].get("required", [])

    # Edges must require _from and _to while vertices must require _key
    has_edge_fields = "_from" in required and "_to" in required
    has_delta_edge_fields = "from" in required and "to" in required

    if data["type"] == "edge" and data.get("delta") and not has_delta_edge_fields:
        raise ValidationError(
            'Time-travel edge schemas must require "from" and "to" attributes in '
            + path
        )
    elif data["type"] == "edge" and not data.get("delta") and not has_edge_fields:
        raise ValidationError(
            'Edge schemas must require "_from" and "_to" attributes in ' + path
        )
    elif data["type"] == "vertex" and data.get("delta") and "id" not in required:
        raise ValidationError(
            'Time-travel vertex schemas must require the "id" attribute in ' + path
        )
    elif data["type"] == "vertex" and not data.get("delta") and "_key" not in required:
        raise ValidationError(
            'Vertex schemas must require the "_key" attribute in ' + path
        )

    print(f"✓ {path} is valid.")
    return data


def validate_data_source(path):
    print(f"  validating {path}..")

    # JSON schema for data source files in /data_sources
    data_source_schema_file = _VALID_SCHEMA_TYPES["data_source"]["file"]
    data = run_validator(schema_file=data_source_schema_file, data_file=path)
    namecheck_schema(path, data)

    print(f"✓ {path} is valid.")
    return data


def validate_stored_query(path):
    print(f"  validating {path}..")

    stored_queries_schema_file = _VALID_SCHEMA_TYPES["stored_query"]["file"]
    data = run_validator(schema_file=stored_queries_schema_file, data_file=path)
    namecheck_schema(path, data)

    # Make sure `params` can be used as a JSON schema
    if data.get("params"):
        # If the schema is invalid, a SchemaError will get raised
        # Otherwise, the schema will work and a ValidationError will get raised
        try:
            run_validator(data={}, schema=data["params"])
        except ValidationError:
            pass

    # check that the query is valid AQL
    validate_aql_on_arango(data)

    print(f"✓ {path} is valid.")
    return data


def validate_view(path):
    """Validate the structure and syntax of an arangodb view"""
    print(f"  validating {path}..")

    # JSON schema for /views
    view_schema_file = _VALID_SCHEMA_TYPES["view"]["file"]
    data = run_validator(data_file=path, schema_file=view_schema_file)
    namecheck_schema(path, data)

    print(f"✓ {path} is valid.")
    return data


def namecheck_schema(path, data):
    """Ensure that the schema "name" is the same as the file name minus extensions"""
    name = data["name"]
    filename = os.path.splitext(os.path.basename(path))[0]
    if name != filename:
        raise ValueError(f"Name key should match filename: {name} vs {filename}")


def validate_aql_on_arango(data):
    """Validate a string as valid AQL syntax by running it on the ArangoDB"""
    query = data.get("query_prefix", "") + " " + data["query"]
    url = _CONF["db_url"] + "/_api/query"
    auth = (_CONF["db_user"], _CONF["db_pass"])

    resp = requests.post(url, data=json.dumps({"query": query}), auth=auth)
    parsed = resp.json()
    if parsed["error"]:
        raise ValueError(parsed["errorMessage"])
    query_bind_vars = set(parsed["bindVars"])
    params = set(data.get("params", {}).get("properties", {}).keys())
    if params != query_bind_vars:
        raise ValueError(
            "Bind vars are invalid.\n"
            + f"  Extra vars in query: {query_bind_vars - params}.\n"
            + f"  Extra params in schema: {params - query_bind_vars}"
        )


if __name__ == "__main__":

    validation_base_dir = None
    if len(sys.argv) > 1:
        validation_base_dir = sys.argv[1]

    wait_for_arangodb()
    n_errors = validate_all_by_type(validation_base_dir)
    exit_code = 0 if not n_errors else 1
    sys.exit(exit_code)
