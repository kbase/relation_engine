"""
Make ajax requests to the ArangoDB server.
"""
import sys
import os
import requests
import json

from relation_engine_server.utils.config import get_config

_CONF = get_config()
adb_url = _CONF["api_url"]
auth = (_CONF["db_user"], _CONF["db_pass"])


def adb_request(req_method, url_append, **kw):
    """Make HTTP request to ArangoDB server"""
    resp = req_method(
        adb_url + url_append,
        auth=auth,
        **kw,
    )
    if not resp.ok or resp.json()["error"]:
        raise ArangoServerError(resp.text)
    return resp.json()


def server_status():
    """Get the status of our connection and authorization to the ArangoDB server."""
    auth = (_CONF["db_user"], _CONF["db_pass"])
    adb_url = f"{_CONF['api_url']}/version"
    try:
        resp = requests.get(adb_url, auth=auth)
    except requests.exceptions.ConnectionError:
        return "no_connection"
    if resp.ok:
        return "connected_authorized"
    elif resp.status_code == 401:
        return "unauthorized"
    else:
        return "unknown_failure"


def run_query(
    query_text=None, cursor_id=None, bind_vars=None, batch_size=10000, full_count=False
):
    """Run a query using the arangodb http api. Can return a cursor to get more results."""
    url = _CONF["api_url"] + "/cursor"
    req_json = {
        "batchSize": min(5000, batch_size),
        "memoryLimit": 16000000000,  # 16gb
    }
    if cursor_id:
        method = "PUT"
        url += "/" + cursor_id
    else:
        method = "POST"
        req_json["count"] = True
        req_json["query"] = query_text
        if full_count:
            req_json["options"] = {"fullCount": True}
        if bind_vars:
            req_json["bindVars"] = bind_vars
    # Run the query as the readonly user
    resp = requests.request(
        method,
        url,
        data=json.dumps(req_json),
        auth=(_CONF["db_readonly_user"], _CONF["db_readonly_pass"]),
    )
    resp_json = resp.json()
    if not resp.ok or resp_json["error"]:
        raise ArangoServerError(resp.text)
    return {
        "results": resp_json["result"],
        "count": resp_json["count"],
        "has_more": resp_json["hasMore"],
        "cursor_id": resp_json.get("id"),
        "stats": resp_json["extra"]["stats"],
    }


def get_all_collections():
    """
    Fetch information for all existing non-system collections

    Resp to GET /_api/collection is
    {
        "error": False,
        "code": 200,
        "result": [
            {
                "id": str of int,
                "name": str,
                "status": int,
                "type": int,
                "isSystem": bool,
                "globallyUniqueId": str,
            },
            ...
        ]
    }
    """
    resp_json = adb_request(
        req_method=requests.get,
        url_append="/collection",
        # ---
        params={"excludeSystem": True},
    )
    return resp_json


def create_collection(name, config):
    """
    Create a single collection by name using some basic defaults.
    We ignore duplicates. For any other server error, an exception is thrown.
    Shard the new collection based on the number of db nodes (10 shards for each).
    """
    is_edge = config["type"] == "edge"
    num_shards = int(os.environ.get("SHARD_COUNT", 30))
    url = _CONF["api_url"] + "/collection"
    # collection types:
    #   2 is a document collection
    #   3 is an edge collection
    collection_type = 3 if is_edge else 2
    print(f"Creating collection {name} (edge: {is_edge})")
    data = json.dumps(
        {
            "keyOptions": {"allowUserKeys": True},
            "name": name,
            "type": collection_type,
            "numberOfShards": num_shards,
            "waitForSync": True,
        }
    )
    resp = requests.post(url, data, auth=(_CONF["db_user"], _CONF["db_pass"]))
    resp_json = resp.json()
    if not resp.ok:
        if "duplicate" not in resp_json["errorMessage"]:
            # Unable to create a collection
            raise ArangoServerError(resp.text)
    print(f"Successfully created collection {name}")
    if config.get("indexes"):
        _create_indexes(name, config)


def get_all_indexes():
    """
    Fetch all existing indexes for all non-system collections

    Returns
    {
        "coll_name_0":
            [
                {
                    "deduplicate" : true,
                    "estimates" : true,
                    "fields" : [
                        "price"
                    ],
                    "id" : "products/68128",
                    "name" : "idx_1721606625944403968",
                    "selectivityEstimate" : 1,
                    "sparse" : true,
                    "type" : "skiplist",
                    "unique" : false
                },
                ...
            ],
        ...
    }
    """
    coll_names = [coll["name"] for coll in get_all_collections()["result"]]
    all_indexes = {}
    for coll_name in coll_names:
        all_indexes[coll_name] = _get_coll_indexes(coll_name)
    return all_indexes


def _get_coll_indexes(coll_name):
    """
    Fetch existing indexes for a collection
    Resp to GET /_api/index is
    {
        "error" : False,
        "code" : 200,
        "indexes" : [
            {
                "deduplicate" : true,
                "estimates" : true,
                "fields" : [
                    "price"
                ],
                "id" : "products/68128",
                "name" : "idx_1721606625944403968",
                "selectivityEstimate" : 1,
                "sparse" : true,
                "type" : "skiplist",
                "unique" : false
            },
            ...
        ],
        ...
    }
    """
    resp_json = adb_request(
        req_method=requests.get,
        url_append="/index",
        params={"collection": coll_name},
    )
    return resp_json["indexes"]


def _create_indexes(coll_name, config):
    """Create indexes for a collection"""
    url = _CONF["api_url"] + "/index"
    indexes = _get_coll_indexes(coll_name)
    for idx_conf in config["indexes"]:
        idx_type = idx_conf["type"]
        idx_url = url + "#" + idx_type
        if _index_exists(idx_conf, indexes):
            # POSTing again would not overwrite anyway
            continue
        print(f"Creating {idx_type} index for collection {coll_name}: {idx_conf}")
        resp = requests.post(
            idx_url,
            params={"collection": coll_name},
            data=json.dumps(idx_conf),
            auth=(_CONF["db_user"], _CONF["db_pass"]),
        )
        if not resp.ok:
            raise RuntimeError(resp.text)
        print(
            f'Successfully created {idx_type} index on {idx_conf["fields"]} for {coll_name}.'
        )


def _index_exists(idx_conf, indexes):
    """
    Check if an index for a collection was already created in the database.
    idx_conf - index config object from a collection schema
    indexes - result of request to arangodb's /_api/index?collection=coll_name
    """
    for idx in indexes:
        if idx_conf["fields"] == idx["fields"] and idx_conf["type"] == idx["type"]:
            return True
    return False


def import_from_file(file_path, query):
    """Import documents from a file."""
    with open(file_path, "rb") as file_desc:
        resp = requests.post(
            _CONF["api_url"] + "/import",
            data=file_desc,
            auth=(_CONF["db_user"], _CONF["db_pass"]),
            params=query,
        )
    if not resp.ok:
        raise ArangoServerError(resp.text)
    resp_json = resp.json()
    if resp_json.get("errors", 0) > 0:
        err_msg = f"{resp_json['errors']} errors creating documents\n"
        sys.stderr.write(err_msg)
        details = resp_json.get("details")
        if details:
            sys.stderr.write(f"Error details:\n{details[0]}\n")
    return resp_json


def get_all_views():
    """
    Fetch all existing views from server

    Resp to GET /_api/view is
    {
        "error": false,
        "code": 200,
        "result": [
            {"id": str, "name": str, "type": str},
            ...
        ]
    }

    Resp to GET /_api/view/{view_name}/properties is
    {
        "error" : false,
        "code" : 200,
        "writebufferIdle" : 64,
        "type" : "arangosearch",
        "writebufferSizeMax" : 33554432,
        "consolidationPolicy" : {
            "type" : "tier",
            "segmentsBytesFloor" : 2097152,
            "segmentsBytesMax" : 5368709120,
            "segmentsMax" : 10,
            "segmentsMin" : 1,
            "minScore" : 0
        },
        "name" : "products",
        "primarySort" : [ ],
        "globallyUniqueId" : "hA5F3C05BE80C/68910",
        "id" : "68910",
        "storedValues" : [ ],
        "writebufferActive" : 0,
        "consolidationIntervalMsec" : 1000,
        "cleanupIntervalStep" : 2,
        "commitIntervalMsec" : 1000,
        "links" : {
        },
        "primarySortCompression" : "lz4"
    }

    Returns
    [
        {},
        {},
        ...
    ]
    where each item is the properties dict (from above)
    """
    resp_json = adb_request(
        req_method=requests.get,
        url_append="/view",
    )
    view_names = [view["name"] for view in resp_json["result"]]

    view_properties = []
    for view_name in view_names:
        resp_json = adb_request(
            req_method=requests.get,
            url_append=f"/view/{view_name}/properties",
        )
        view_properties.append(resp_json)

    return view_properties


def create_view(name, config):
    """
    Create a view by name, ignoring duplicates.
    For any other server error, an exception is thrown.
    """

    url = _CONF["api_url"] + "/view#arangosearch"

    if "name" not in config:
        config["name"] = name
    if "type" not in config:
        config["type"] = "arangosearch"
    print(f"Creating view {name}")
    data = json.dumps(config)
    resp = requests.post(url, data, auth=(_CONF["db_user"], _CONF["db_pass"]))
    resp_json = resp.json()
    if not resp.ok:
        if "duplicate" not in resp_json["errorMessage"]:
            # Unable to create the view
            raise ArangoServerError(resp.text)


def get_all_analyzers():
    """
    Fetch all existing analyzers from server
    Resp to GET /_api/analyzer is
    {
        "error" : false,
        "code" : 200,
        "result" : [
            {
                "name" : "text_pt",
                "type" : "text",
                "properties" : {
                    "locale" : "pt.utf-8",
                    "case" : "lower",
                    "stopwords" : [ ],
                    "accent" : false,
                    "stemming" : true
                },
                "features" : [
                    "frequency",
                    "norm",
                    "position"
                ]
            },
            ...
        ]
    }

    Returns
    [
        { ... }
    ]
    """
    resp = requests.get(
        url=_CONF["api_url"] + "/analyzer",
        auth=(_CONF["db_user"], _CONF["db_pass"]),
    )
    if not resp.ok:
        raise RuntimeError(resp.text)
    analyzers = resp.json()["result"]
    return analyzers


def create_analyzer(name, config):
    print(f"Creating analyzer {name}")
    resp = requests.post(
        url=_CONF["api_url"] + "/analyzer",
        data=json.dumps(config),
        auth=(_CONF["db_user"], _CONF["db_pass"]),
    )
    if not resp.ok:
        if "duplicate" not in resp.json()["errorMessage"]:
            raise ArangoServerError(resp.text)


class ArangoServerError(Exception):
    """A request to the ArangoDB server has failed (non-2xx)."""

    def __init__(self, resp_text):
        self.resp_text = resp_text
        self.resp_json = json.loads(resp_text)

    def __str__(self):
        return "ArangoDB server error."
