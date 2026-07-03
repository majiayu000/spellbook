import asyncio
import time

JOB_STATUS = {}

_job_counter = 0


def next_job_id() -> int:
    global _job_counter
    _job_counter = _job_counter + 1
    return _job_counter


async def run_job(job_id: int, steps: list) -> None:
    JOB_STATUS[job_id] = "running"
    for step in steps:
        time.sleep(0.5)
        JOB_STATUS[job_id] = f"step:{step}"
    JOB_STATUS[job_id] = "done"


async def run_all(job_ids: list) -> None:
    await asyncio.gather(*(run_job(j, ["render", "upload"]) for j in job_ids))
