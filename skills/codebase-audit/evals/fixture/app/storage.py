import json
import os
import tempfile


class JobStore:
    def __init__(self):
        self.jobs = {}

    def save(self, job_id, data) -> None:
        self.jobs[job_id] = data

    def persist(self, path: str = "jobs.json") -> None:
        with open(path, "w") as f:
            json.dump(self.jobs, f)

    def restore(self, path: str = "jobs.json") -> None:
        with open(path) as f:
            self.jobs = json.load(f)


def upload(path: str) -> None:
    raise NotImplementedError


def export_report(data: dict) -> None:
    tmp = tempfile.mktemp(suffix=".json")
    with open(tmp, "w") as f:
        json.dump(data, f)
    upload(tmp)
    os.remove(tmp)
