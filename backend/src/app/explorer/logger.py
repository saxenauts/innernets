from __future__ import annotations

import json
from typing import Any, Dict, List

from .ansi import bold, cyan_bright, gray, block_bg


def _pp_json_full(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


class ExplorerLogger:
    def __init__(self) -> None:
        self._alt = False  # toggle background per section

    def _frame(self, title: str, body: str, *, iter_no: int | None = None) -> None:
        header = f"◆ {title}"
        if iter_no is not None:
            header = f"[Iter {iter_no}] {header}"
        print(bold(cyan_bright(header)))
        print(block_bg(body, alt=self._alt))
        self._alt = not self._alt

    def info(self, label: str, text: str, *, iter_no: int | None = None) -> None:
        body = f"{label}: {text}"
        self._frame("Info", body, iter_no=iter_no)

    def step_request(self, system_text: str, user_text: str, *, iter_no: int) -> None:
        sys_body = f"system →\n{system_text.strip()}\n\nuser →\n{user_text.strip()}"
        self._frame("Step LLM Request", sys_body, iter_no=iter_no)

    def step_response(self, step_json: Dict[str, Any], *, iter_no: int) -> None:
        self._frame("Step LLM Response (StepOutput)", _pp_json_full(step_json), iter_no=iter_no)


    def search_overview(self, query: str, lines: List[str], *, iter_no: int) -> None:
        body = f"query: {query}\n" + "\n".join(lines)
        self._frame("Search (Google)", body, iter_no=iter_no)

    def read_batch_overview(self, urls: list[str], *, depth: int, iter_no: int) -> None:
        lines = [f"depth: {depth}"]
        for u in urls:
            lines.append(f"- {u}")
        self._frame("Read Batch", "\n".join(lines), iter_no=iter_no)

    def memory_full(self, memory: Dict[str, Any], *, iter_no: int) -> None:
        self._frame("Memory (Full)", _pp_json_full(memory), iter_no=iter_no)


    def reading_batch_response(self, reading_json: Dict[str, Any], *, iter_no: int) -> None:
        self._frame("Reading LLM Response (Batch)", _pp_json_full(reading_json), iter_no=iter_no)

    def reading_batch_request(self, system_text: str, user_text: str, *, iter_no: int) -> None:
        sys_body = f"system →\n{system_text.strip()}\n\nuser →\n{user_text.strip()}"
        self._frame("Reading LLM Request (Batch)", sys_body, iter_no=iter_no)

    def iteration_summary(
        self,
        *,
        iter_no: int,
        searches_run: int,
        pages_read: int,
        waves: int,
        visited_len: int,
        step_usage: Dict[str, Any] | None = None,
        read_usage: Dict[str, Any] | None = None,
        totals: Dict[str, Any] | None = None,
    ) -> None:
        lines: List[str] = []
        lines.append(f"searches: {searches_run}")
        lines.append(f"pages_read: {pages_read} (waves: {waves})")
        lines.append(f"visited: {visited_len}")
        if step_usage:
            lines.append(
                "step tokens: in="
                f"{step_usage.get('input_tokens', 0)} out={step_usage.get('output_tokens', 0)} "
                f"cost=${step_usage.get('total_cost_usd', 0):.6f}"
            )
        if read_usage:
            lines.append(
                "read tokens: in="
                f"{read_usage.get('input_tokens', 0)} out={read_usage.get('output_tokens', 0)} "
                f"cost=${read_usage.get('total_cost_usd', 0):.6f}"
            )
        if totals:
            lines.append(
                "totals: step_in="
                f"{totals.get('step_tokens_in', 0)} step_out={totals.get('step_tokens_out', 0)} "
                f"read_in={totals.get('read_tokens_in', 0)} read_out={totals.get('read_tokens_out', 0)} "
                f"cost=${totals.get('total_cost_usd', 0.0):.6f}"
            )
        self._frame("Iteration Summary", "\n".join(lines), iter_no=iter_no)

    def run_summary(self, totals: Dict[str, Any]) -> None:
        lines: List[str] = []
        lines.append(f"iterations: {totals.get('iterations', 0)}")
        lines.append(
            "step tokens: in="
            f"{totals.get('step_tokens_in', 0)} out={totals.get('step_tokens_out', 0)} "
            f"cost=${totals.get('step_cost_usd', 0.0):.6f}"
        )
        lines.append(
            "read tokens: in="
            f"{totals.get('read_tokens_in', 0)} out={totals.get('read_tokens_out', 0)} "
            f"cost=${totals.get('read_cost_usd', 0.0):.6f}"
        )
        lines.append(f"total cost: ${totals.get('total_cost_usd', 0.0):.6f}")
        self._frame("Run Summary", "\n".join(lines), iter_no=None)

    def run_results(self, curations_batches: list[dict]) -> None:
        lines: list[str] = []
        total_curations = 0
        for b_idx, batch in enumerate(curations_batches or [], start=1):
            pages = batch.get("pages") or []
            curations = batch.get("curations") or []
            page_map = {str(p.get("id")): str(p.get("url")) for p in pages if p.get("id") and p.get("url")}
            for c_idx, c in enumerate(curations, start=1):
                total_curations += 1
                summary = str(c.get("summary") or "").strip()
                pg_ids = [str(x) for x in (c.get("pages") or [])]
                lines.append(f"Curation {total_curations}: {summary}")
                if pg_ids:
                    for pid in pg_ids:
                        url = page_map.get(pid, "")
                        if url:
                            lines.append(f"  - {pid}: {url}")
                        else:
                            lines.append(f"  - {pid}")
                lines.append("")
        if not lines:
            lines.append("(no curations)")
        self._frame("Run Results (Curations)", "\n".join(lines).rstrip(), iter_no=None)
