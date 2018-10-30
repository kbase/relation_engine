"""
Collection of exception classes for the Relation Engine server.
"""


class MissingHeader(Exception):

    def __init__(self, header_name):
        self.header_name = header_name

    def __str__(self):
        return "Missing header: " + self.header_name


class UnauthorizedAccess(Exception):

    def __init__(self, auth_url):
        self.auth_url = auth_url
