"""
Make ajax requests to the ArangoDB server.
"""
import sys
import os
import requests
import json

from relation_engine_server.utils.config import get_config

_CONF = get_config()


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


def _create_indexes(coll_name, config):
    """Create indexes for a collection"""
    url = _CONF["api_url"] + "/index"
    # Fetch existing indexes
    auth = (_CONF["db_user"], _CONF["db_pass"])
    resp = requests.get(url, params={"collection": coll_name}, auth=auth)
    if not resp.ok:
        raise RuntimeError(resp.text)
    indexes = resp.json()["indexes"]
    for idx_conf in config["indexes"]:
        if _index_exists(idx_conf, indexes):
            continue
        idx_type = idx_conf["type"]
        idx_url = url + "#" + idx_type
        idx_conf["type"] = idx_type
        print(f"Creating {idx_type} index for collection {coll_name}: {idx_conf}")
        resp = requests.post(
            idx_url,
            params={"collection": coll_name},
            data=json.dumps(idx_conf),
            auth=auth,
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


class ArangoServerError(Exception):
    """A request to the ArangoDB server has failed (non-2xx)."""

    def __init__(self, resp_text):
        self.resp_text = resp_text
        self.resp_json = json.loads(resp_text)

    def __str__(self):
        return "ArangoDB server error."
