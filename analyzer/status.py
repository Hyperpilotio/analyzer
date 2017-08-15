from enum import Enum

class Status():
    SUBMITTED = "submitted"
    RUNNING = "running"
    DONE = "done"
    SERVER_ERROR = "server_error"
    BAD_REQUEST = "bad_request"

class SessionStatus():
    def __init__(self, status, data=None, error=None):
        self.status = status
        self.data = data
        self.error = error

    def to_dict(self):
        return {
            "status": self.status,
            "error": self.error,
            "data": self.data
        }
