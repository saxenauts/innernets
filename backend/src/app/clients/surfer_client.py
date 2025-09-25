from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import time
import httpx

from app.config import settings


class SurferError(Exception):
    pass


def _headers() -> Dict[str, str]:
    h = {"content-type": "application/json"}
    if settings.SURFER_API_KEY:
        h["authorization"] = f"Bearer {settings.SURFER_API_KEY}"
    return h


def _base() -> str:
    return settings.SURFER_BASE_URL.rstrip("/")


def explorer_submit(
    instruction: str,
    *,
    stream_context: Optional[str] = None,
    headless: Optional[bool] = None,
    max_steps: Optional[int] = None,
    use_mock: Optional[bool] = None,
    sync: bool = False,
) -> Dict[str, Any]:
    """Submit an explorer job (async by default).

    Returns either 202-accepted job descriptor or, if sync=True, a result payload.
    """
    headless = settings.SURFER_HEADLESS if headless is None else bool(headless)
    max_steps = settings.SURFER_MAX_STEPS if max_steps is None else int(max_steps)
    use_mock = settings.SURFER_USE_MOCK if use_mock is None else bool(use_mock)

    url = f"{_base()}/api/explorer/jobs"
    if sync:
        url = f"{_base()}/api/explorer?sync=true"
    if use_mock and not sync:
        # Keep mock slow enough to simulate long-running tasks (>=10s)
        url = f"{_base()}/api/explorer/mock?delay_s=10"

    payload: Dict[str, Any] = {
        "instruction": instruction,
        "headless": headless,
        "max_steps": max_steps,
    }
    if stream_context:
        payload["stream_context"] = stream_context

    with httpx.Client(timeout=60.0) as cli:
        resp = cli.post(url, headers=_headers(), json=payload)
        if resp.status_code not in {200, 202}:
            raise SurferError(f"Submit failed: HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def job_status(job_id: str) -> Dict[str, Any]:
    url = f"{_base()}/api/jobs/{job_id}"
    with httpx.Client(timeout=30.0) as cli:
        resp = cli.get(url, headers=_headers())
        if resp.status_code != 200:
            raise SurferError(f"Status failed: HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def job_result(job_id: str) -> Dict[str, Any]:
    url = f"{_base()}/api/jobs/{job_id}/result"
    with httpx.Client(timeout=60.0) as cli:
        resp = cli.get(url, headers=_headers())
        if resp.status_code == 409:
            raise SurferError("Result not ready (409)")
        if resp.status_code != 200:
            raise SurferError(f"Result failed: HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def wait_for_result(job_id: str, *, poll_interval_s: Optional[int] = None, max_wait_s: Optional[int] = None) -> Dict[str, Any]:
    """Poll job status until completed/failed or timeout, then fetch results.

    Returns result JSON (curations list) on success. Raises SurferError on failure/timeout.
    """
    poll = settings.SURFER_POLL_INTERVAL_S if poll_interval_s is None else int(poll_interval_s)
    maxw = settings.SURFER_MAX_WAIT_S if max_wait_s is None else int(max_wait_s)
    start = time.time()
    last_state = None
    while True:
        st = job_status(job_id)
        state = (st.get("state") or "").lower()
        last_state = state
        if state in {"completed"}:
            break
        if state in {"failed", "canceled"}:
            raise SurferError(f"Job {job_id} ended as {state}")
        if time.time() - start > maxw:
            raise SurferError(f"Timeout waiting for job {job_id}; last_state={last_state}")
        time.sleep(max(1, poll))

    # Fetch result (may still 409 if race)
    deadline = time.time() + 60.0
    while True:
        try:
            return job_result(job_id)
        except SurferError as e:
            if "409" not in str(e):
                raise
            if time.time() > deadline:
                raise
            time.sleep(1.0)
