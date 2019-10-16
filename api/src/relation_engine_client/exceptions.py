import json


class REServerError(Exception):

    def __init__(self, resp):
        self.resp = resp

    def __str__(self):
        return (
            f"Relation engine API server error:\n"
            f"Request URL: {self.resp.method}\n"
            f"Response: {self.resp.json()}"
        )


class RERequestError(Exception):

    def __init__(self, resp):
        self.resp = resp

    def __str__(self):
        try:
            return (
                f"Relation engine API client request error:\n"
                f"Request URL: {self.resp.method}\n"
                f"Response: {json.dumps(self.resp.json(), indent=2)}"
            )
        except Exception as err:
            print(err)
            return self.resp.text


class RENotFound(Exception):

    def __init__(self, req_body, req_params):
        self.req_body = req_body
        self.req_params = req_params

    def __str__(self):
        return (
            f"Documents not found in the Relation Engine:\n"
            f"Request body: {self.req_body}\n"
            f"URL params: {self.req_params}"
        )
