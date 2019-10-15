
class REServerError(Exception):

    def __init__(self, resp):
        self.resp = resp

    def __repr__(self):
        return (
            f"Relation engine API server error:\n"
            f"Request URL: {self.resp.method}\n"
            f"Response: {self.resp.json()}"
        )


class RERequestError(Exception):

    def __init__(self, resp):
        self.resp = resp

    def __repr__(self):
        return (
            f"Relation engine API client request error:\n"
            f"Request URL: {self.resp.method}\n"
            f"Response: {self.resp.json()}"
        )


class RENotFound(Exception):

    def __init__(self, req_body, req_params):
        self.req_body = req_body
        self.req_params = req_params

    def __repr__(self):
        return (
            f"Documents not found in the Relation Engine:\n"
            f"Request body: {self.req_body}\n"
            f"URL params: {self.req_params}"
        )
