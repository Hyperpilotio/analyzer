from concurrent.futures import ProcessPoolExecutor

class FuncArgs():
    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs

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

# Worker pool that is dedicated to each Bayesian optimizer session.
# The pool assumes each session has one or more stages, and it only expects one stage to run at a time;
# if a task is submitted while the previous stage is still running, an error is returned.
class SessionWorkerPool():
    def __init__(self, workers):
        # Map for storing the future objects for python concurrent tasks
        self.future_list = []
        # Pool of worker processes for handling jobs
        self.worker_pool = ProcessPoolExecutor(max_workers=workers)

    def submit_data(self, function, data, *args, **kwargs):
        if self.get_status().status == Status.RUNNING:
            return SessionStatus(Status.BAD_REQUEST, "Session has work in progress; submit task later")

        self.future_list = [self.worker_pool.submit(
            function, i) for i in data]
        return SessionStatus(Status.SUBMITTED)

    def submit_funcs(self, funcargs_list):
        if self.get_status().status == Status.RUNNING:
            return SessionStatus(Status.BAD_REQUEST, "Session has work in progress; submit task later")

        self.future_list = [self.worker_pool.submit(
            f.function, *f.args, **f.kwargs) for f in funcargs_list]
        return SessionStatus(Status.SUBMITTED)

    def get_status(self):
        if not self.future_list:
            return SessionStatus(Status.BAD_REQUEST, "Session has no work in progress")

        if all([future.done() for future in self.future_list]):
            data = [future.result() for future in self.future_list]
            return SessionStatus(Status.DONE, data)
        elif any([future.cancelled() for future in self.future_list]):
            return SessionStatus(status=Status.SERVER_ERROR, error="At least one task was cancelled")
        else:
            # Future in running or pending state
            return SessionStatus(Status.RUNNING)
