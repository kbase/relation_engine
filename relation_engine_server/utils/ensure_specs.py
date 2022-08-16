"""
Ensure that all the specs in the spec/**/*.json and spec/**/*.yaml are
present in the server, with the top-level fields of the local specs being
a subset of the top-level fields of the server specs
"""
from typing import Union, Callable

from relation_engine_server.utils.json_validation import load_json_yaml
from relation_engine_server.utils import arango_client
from spec.validate import get_schema_type_paths


def match(spec_local, specs_server):
    for spec_server in specs_server:
        if is_obj_subset_rec(spec_local, spec_server):
            return True
    return False


def get_local_coll_indexes():
    """
    Read all schemas for the collection schema type
    Return just collection name and indexes
    """
    coll_spec_paths = []
    coll_name_2_indexes = {}
    for coll_spec_path in get_schema_type_paths("collection"):
        coll = load_json_yaml(coll_spec_path)
        if "indexes" not in coll:
            continue
        coll_spec_paths.append(coll_spec_path)
        coll_name_2_indexes[coll["name"]] = coll["indexes"]
    return coll_spec_paths, coll_name_2_indexes


def get_local_views():
    view_spec_paths = get_schema_type_paths("view")
    view_specs = [load_json_yaml(view_spec_path) for view_spec_path in view_spec_paths]
    return view_spec_paths, view_specs


def get_local_analyzers():
    analyzer_spec_paths = get_schema_type_paths("analyzer")
    analyzer_specs = [
        load_json_yaml(analyzer_spec_path) for analyzer_spec_path in analyzer_spec_paths
    ]
    return analyzer_spec_paths, analyzer_specs


def ensure_indexes():
    """
    Returns tuple
    First item is list of borked index names, e.g.
    [
        "coll_name_3/fulltext/['scientific_name']",
        "coll_name_4/persistent/['id', 'key']",
    ]
    Second item is struct of failed indexes, e.g.,
    {
        coll_name_3: [
            {"type": "fulltext", "fields": ["scientific_name"] ...}
        ],
        coll_name_4: [
            {"type": "persistent", "fields": ["id", "key"] ...}
        ]
    }
    """
    coll_name_2_indexes_server = arango_client.get_all_indexes()
    coll_spec_paths, coll_name_2_indexes_local = get_local_coll_indexes()

    failed_specs = {}
    for coll_spec_path, (coll_name, indexes_local) in zip(
        coll_spec_paths, coll_name_2_indexes_local.items()
    ):
        print(f"Ensuring indexes for {coll_spec_path}")
        if coll_name not in coll_name_2_indexes_server:
            failed_specs[coll_name] = indexes_local
            continue
        else:
            failed_specs[coll_name] = []
        indexes_server = coll_name_2_indexes_server[coll_name]
        for index_local in indexes_local:
            if not match(index_local, indexes_server):
                failed_specs[coll_name] = index_local

    failed_specs = {
        k: v for k, v in failed_specs.items() if v
    }  # filter out 0-failure colls
    if failed_specs:
        print_failed_specs("indexes", failed_specs)
    else:
        print("All index specs ensured")

    return get_names(failed_specs, "indexes"), failed_specs


def ensure_views():
    """
    Returns tuple
    First item is list of failed view names, e.g.,
    [
       "Compounds/arangosearch"
    ]
    Second item is list of failed specs, e.g.,
    [
        {"name": "Compounds", "type": "arangosearch", ...}
    ]
    """
    all_views_server = arango_client.get_all_views()
    mod_obj_literal(all_views_server, float, round_float)

    failed_specs = []
    for view_spec_path, view_local in zip(*get_local_views()):
        print(f"Ensuring view {view_spec_path}")
        if not match(view_local, all_views_server):
            failed_specs.append(view_local)

    if failed_specs:
        print_failed_specs("views", failed_specs)
    else:
        print("All view specs ensured")

    return get_names(failed_specs, "views"), failed_specs


def ensure_analyzers():
    """
    Returns tuple
    First item is list of failed view names, e.g.,
    [
       "icu_tokenize/text"
    ]
    Second item is list of failed specs, e.g.,
    [
        {"name": "icu_tokenize", "type": "text", ...}
    ]
    """
    all_analyzers_server = arango_client.get_all_analyzers()
    mod_obj_literal(all_analyzers_server, str, excise_namespace)

    failed_specs = []
    for analyzer_spec_path, analyzer_local in zip(*get_local_analyzers()):
        print(f"Ensuring analyzer {analyzer_spec_path}")
        if not match(analyzer_local, all_analyzers_server):
            failed_specs.append(analyzer_local)

    if failed_specs:
        print_failed_specs("analyzers", failed_specs)
    else:
        print("All analyzer specs ensured")

    return get_names(failed_specs, "analyzers"), failed_specs


def ensure_all():
    """
    Return names of failed specs if any, e.g.,
    {
        "indexes": [
        ],
        "views": [
            "Coumpounds/arangosearch",
            "Reactions/arangosearch",
        ],
        "analyzers": [
            "icu_tokenize/text",
        ],
    }
    """
    failed_indexes_names, _ = ensure_indexes()
    failed_views_names, _ = ensure_views()
    failed_analyzers_names, _ = ensure_analyzers()

    return {
        "indexes": failed_indexes_names,
        "views": failed_views_names,
        "analyzers": failed_analyzers_names,
    }


def get_names(specs, schema_type):
    """
    Given views/analyzers/collections, collate names using required properties
    """
    names = []
    if schema_type in ["views", "analyzers"]:
        for spec in specs:
            names.append(f"{spec['name']}/{spec['type']}")
    elif schema_type in ["indexes"]:
        for coll_name, indexes in specs.items():
            for index in indexes:
                names.append(f"{coll_name}/{index['type']}/{index['fields']}")
    else:
        raise RuntimeError(f'Unknown schema type "{schema_type}"')
    return names


def print_failed_specs(schema_type, failed_specs):
    """
    Print message with names of failed local specs
    """

    fail_msg = (
        "\n"
        f"----------> {len(failed_specs)} {schema_type} failed ---------->"
        "\n"
        f"----------> names: {get_names(failed_specs, schema_type)} ---------->"
        "\n"
        f"----------> Please compare local/server specs ---------->"
    )

    print(fail_msg)


def round_float(num: float) -> float:
    """
    For round-off error in floats
    Arbitrarily chose 7 places
    """
    return round(num, 7)


def excise_namespace(analyzer_name: str) -> str:
    """
    Remove namespace prefix, e.g.,
    namespace::thing -> thing
    """
    return analyzer_name.split("::")[-1]


def is_obj_subset_rec(
    left: Union[dict, list, float, str, int],
    right: Union[dict, list, float, str, int],
):
    """
    Compare two JSON objects, to see if, essentially, left <= right
    If comparing dicts, recursively compare
    If comparing lists, shallowly compare. For now, YAGN more
    """
    if isinstance(left, dict) and isinstance(right, dict):
        return all(
            [
                k in right.keys() and is_obj_subset_rec(left[k], right[k])
                for k in left.keys()
            ]
        )  # ignore: typing
    elif isinstance(left, list) and isinstance(right, list):
        return all([le in right for le in left])
    else:
        return left == right


def mod_obj_literal(
    spec_unit: Union[list, dict],
    literal_type: type,
    func: Callable[[Union[float, str]], Union[float, str]],
) -> None:
    """
    Modify dict in-place recursively
    Some specs won't match because of
    * round-off error in floats
    * namespacing in analyzers, e.g., "_system::icu_tokenize"

    Parameters
    ----------
    spec_unit -     recursively accessed data structure unit of JSON obj
    literal_type -  str or float
    func -          function called to modify that str or float in-place
    """
    if isinstance(spec_unit, dict):
        for k, v in spec_unit.items():
            if isinstance(v, dict) or isinstance(v, list):
                mod_obj_literal(v, literal_type, func)
            elif isinstance(v, literal_type):
                spec_unit[k] = func(v)  # type: ignore
    elif isinstance(spec_unit, list):
        for i, v in enumerate(spec_unit):
            if isinstance(v, dict) or isinstance(v, list):
                mod_obj_literal(v, literal_type, func)
            elif isinstance(v, literal_type):
                spec_unit[i] = func(v)  # type: ignore
