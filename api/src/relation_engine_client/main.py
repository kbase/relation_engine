import os
import json
import requests
from typing import Optional, List, Dict, Union
from dataclasses import dataclass

from src.relation_engine_client.exceptions import REServerError, RERequestError, RENotFound

_QUERY_METHOD = 'POST'
_QUERY_ENDPOINT = '/api/v1/query_results'
_SAVE_METHOD = 'PUT'
_SAVE_ENDPOINT = '/api/v1/documents'


@dataclass
class REClient:
    # The `api_url` can be set with the RE_API_URL env var if provided.
    # We can also use the KBASE_ENDPOINT env var (eg. "https://ci.kbase.us/services/").
    api_url: Optional[str] = None
    # Set to the KBASE_TOKEN env var if not provided
    token: Optional[str] = None

    def __post_init__(self):
        if self.token is None:
            self.token = os.environ.get('KBASE_TOKEN')
        if self.api_url is None:
            if 'RE_API_URL' in os.environ:
                self.api_url = os.environ['RE_API_URL']
            elif 'KBASE_ENDPOINT' in os.environ:
                # eg. https://ci.kbase.us/services/
                # Remove any trailing slash and append the RE API service name
                self.api_url = os.environ['KBASE_ENDPOINT'].strip('/') + '/relation_engine_api'
        if not self.api_url:
            raise RuntimeError("The Relation Engine API URL was not provided. "
                               "Set the `api_url` constructor parameter, the "
                               "RE_API_URL environment variable, or the "
                               "KBASE_ENDPOINT environment variable.")
        # Remove any trailing slash
        self.api_url = self.api_url.strip('/')

    def admin_query(self, query: str, bind_vars: dict, raise_not_found=False):
        """
        Run an ad-hoc query using admin privs.
        Params:
            query - string - AQL query to execute
            bind_vars - dict - JSON serializable bind variables for the query
            raise_not_found - bool - Whether to raise an error if there are zero results. Defaults to False
        Exceptions raised:
            REParamError - raised on invalid parameters to the RE API
            REServerError - raised on a 500 from the RE API
            RENotFound - raised when raise_not_found is True and there are 0 results
        """
        req_body = dict(bind_vars)
        req_body['query'] = query
        url = str(self.api_url) + _QUERY_ENDPOINT
        resp = self._make_request(
            method=_QUERY_METHOD,
            url=url,
            data=json.dumps(req_body),
            params={},
            raise_not_found=raise_not_found)
        return resp

    def stored_query(self, stored_query: str, bind_vars: dict, raise_not_found=False):
        """
        Run a stored query.
        Params:
            stored_query - string - name of the stored query to execute
            bind_vars - JSON serializable - bind variables for the query (JSON serializable)
            raise_not_found - bool - Whether to raise an error if there are zero results. Defaults to False
        Exceptions raised:
            REParamError - raised on invalid parameters to the RE API
            REServerError - raised on a 500 from the RE API
            RENotFound - raised when raise_not_found is True and there are 0 results
        """
        req_body = dict(bind_vars)
        url = str(self.api_url) + _QUERY_ENDPOINT
        return self._make_request(
            method=_QUERY_METHOD,
            url=url,
            data=json.dumps(req_body),
            params={'stored_query': stored_query},
            raise_not_found=raise_not_found)

    def save_docs(
            self,
            coll: str,
            docs: Union[Dict, List[Dict]],
            on_duplicate: Optional[str] = None,
            overwrite=False,
            display_errors=False):
        """
        Save documents to a collection in the relation engine.
        Params:
            coll - str - collection name to save to
            docs - a single dict or list of dicts - json-serializable documents to save
            on_duplicate - str (defaults to 'error') - what to do when a provided document
                already exists in the collection. See options here:
                https://github.com/kbase/relation_engine_api#put-apiv1documents
            overwrite - bool (defaults to False) - whether to overwrite
                everything in the collection (ie. remove all contents of the
                collection before writing new documents)
            display_errors - bool (defaults to False) - whether to respond with
                document save errors (the response will give you an error for every
                document that failed to save).
        Exceptions raised:
            REServerError - 500 from the RE API
            RERequestError - 400 from the RE API (client error)
        """
        if isinstance(docs, dict):
            docs = [docs]
        if not docs:
            raise TypeError("No documents provided to save")
        params = {'collection': coll}
        if display_errors:
            params['display_errors'] = '1'
        if overwrite:
            params['overwrite'] = '1'
        params['on_duplicate'] = on_duplicate or 'error'
        req_body = '\n'.join(json.dumps(d) for d in docs)
        url = str(self.api_url) + _SAVE_ENDPOINT
        return self._make_request(
            method=_SAVE_METHOD,
            url=url,
            data=req_body,
            params=params,
            raise_not_found=False)

    def _make_request(self, method, url, data, params, raise_not_found):
        """
        Internal utility to make a generic request to the RE API and handle the
        response.
        """
        headers = {}
        if self.token:
            headers['Authorization'] = self.token
        resp = requests.request(method=method, url=url, data=data, params=params, headers=headers)
        if resp.status_code >= 500:
            # Server error
            raise REServerError(resp)
        elif resp.status_code >= 400 and resp.status_code < 500:
            # Client error
            raise RERequestError(resp)
        elif not resp.ok:
            raise RuntimeError(
                f"Unknown RE API error:\nURL: {resp.url}\nMethod: {method}\n{resp.text}")
        resp_json = resp.json()
        if raise_not_found and not len(resp_json['results']):
            # Results were required to be non-empty
            raise RENotFound(req_body=data, req_params=params)
        return resp_json
