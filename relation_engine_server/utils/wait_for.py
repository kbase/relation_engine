"""
Block until all dependent services come online.
"""
import requests
import time
import sys
from relation_engine_server.utils.config import get_config
from typing import List

_CONF = get_config()


def get_service_conf():
    return {
        "arangodb": {
            "url": _CONF["api_url"] + "/collection",
            "callback": _assert_json_content,
            "raise_for_status": True,
        },
        "auth": {
            "url": _CONF["auth_url"],
        },
        "workspace": {
            "url": _CONF["workspace_url"],
        },
        "localhost": {
            "url": "http://127.0.0.1:5000",
            "raise_for_status": True,
        },
    }


def wait_for_service(service_list: List[str]) -> None:
    """wait for a service or list of services to start up"""
    timeout = int(time.time()) + 60
    services_pending = set(service_list)
    service_conf = get_service_conf()
    while services_pending:
        still_pending = set()
        for name in services_pending:
            try:
                conf = service_conf[name]
                auth = (_CONF["db_user"], _CONF["db_pass"])
                print("auth is", auth)
                resp = requests.get(conf["url"], auth=auth)
                if conf.get("raise_for_status"):
                    resp.raise_for_status()
                if conf.get("callback") is not None:
                    conf["callback"](resp)
                # The service is up
            except Exception as err:
                print(f"Still waiting for {name} to start...")
                if int(time.time()) > timeout:
                    raise RuntimeError(
                        f"Timed out waiting for {name} to start with error: {err}"
                    )
                still_pending.add(name)
                time.sleep(3)
        services_pending = still_pending
    print(f"{', '.join(service_list)} started!")


def wait_for_arangodb():
    """wait for arangodb to be ready"""
    wait_for_service(["arangodb"])


def wait_for_services():
    """wait for the workspace, auth, and arango to start up"""
    wait_for_service(["auth", "workspace", "arangodb"])


def wait_for_api():
    """wait for the workspace, auth, arango, AND localhost:5000 to start up"""
    wait_for_services()
    wait_for_service(["localhost"])


def _assert_json_content(resp: requests.models.Response) -> None:
    """Assert that a response body has non-empty JSON content."""
    if len(resp.content) == 0:
        raise RuntimeError("No content in response")
    resp.json()


if __name__ == "__main__":
    if sys.argv[1] == "services":
        wait_for_services()
    elif sys.argv[1] == "api":
        wait_for_api()
