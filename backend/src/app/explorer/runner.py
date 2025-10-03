from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, Deque
import threading
from collections import deque

from app.config import settings
from app.clients import surfer_client

from .models import StepOutput, Memory, FilterOutput, CuratedReadingOutput
from .prompts import (
    STEP_SYSTEM,
    STEP_USER_TEMPLATE,
    MULTI_EXTRACT_SYSTEM,
    MULTI_EXTRACT_USER_TEMPLATE,
    SERP_FILTER_SYSTEM,
    SERP_FILTER_USER_TEMPLATE,
)
from .llm import get_openai_client, parse_with_schema
from .logger import ExplorerLogger
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import re


def render_template(tpl: str, variables: Dict[str, Any]) -> str:
    out = tpl
    for k, v in variables.items():
        out = out.replace(f"{{{{ {k} }}}}", str(v))
    return out


@dataclass
class ExplorerConfig:
    instruction: str
    artifacts_dir: Path
    headless: bool = True
    max_steps: int = 25
    # Parallelism controls (0 means unlimited)
    search_concurrency: int = 0
    read_concurrency: int = 0
    batch_size: int = 5
    max_depth: int = 3
    # Number of read batches to run in parallel per wave (0 = no limit)
    batch_concurrency: int = 0
    # Optional: opaque context string passed into LLM prompts only
    stream_context: Optional[str] = None


class Explorer:
    """AI Explorer — free-flow, multi-tab web exploration.

    Algorithm (high‑level)
    - Step LLM proposes ~3 Google queries per iteration (strict JSON schema).
    - For each query, GoogleAdapterRunner types the query on google.com using
      a shared Playwright harness attached over a single CDP. It captures the
      resulting SERP HTML and runs deterministic extraction (Crawl4AI raw HTML),
      then normalizes links.
    - Collected links feed breadth‑first reading waves (batch N, depth ≤ 3):
      each URL opens in its own tab; we capture HTML via TabPool (multi‑tab),
      generate Markdown (Crawl4AI), condense via Reading LLM, and queue next links.
    - Tabs stay open for the iteration and are closed in a tidy pass at the end.

    Concurrency & CDP
    - We attach once to a single CDP. All Playwright operations are serialized
      onto a single worker thread inside BrowserHarness; caller threads enqueue
      work with `harness.call(...)`. This avoids Playwright sync API thread‑
      safety violations while still driving multiple tabs.
    """
    def __init__(
        self,
        cfg: ExplorerConfig,
        *,
        cancel_event: threading.Event | None = None,
    ):
        self.cfg = cfg
        self._cancel_event = cancel_event
        self.client = get_openai_client()
        self.model = (
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            or os.getenv("OPENAI_MODEL")
            or settings.AZURE_OPENAI_DEPLOYMENT_NAME
        )
        if not self.model:
            raise RuntimeError("Missing Azure deployment name: set AZURE_OPENAI_DEPLOYMENT in .env")
        self.memory = Memory()
        # Pass-through stream context (no parsing; used only in prompts)
        try:
            self.stream_context = cfg.stream_context or ""
        except Exception:
            self.stream_context = ""
        self.artifacts_dir = cfg.artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        # Human‑readable current date for prompts (no time)
        try:
            self.today = dt.datetime.now().strftime("%B %d, %Y")
        except Exception:
            self.today = ""

        # SERP metadata cache for the current iteration (depth 1 pages)
        self.serp_meta: Dict[str, Dict[str, str]] = {}

        # Working state
        self.logger = ExplorerLogger()
        # Aggregate curations across all batches/waves/iterations for final output
        self.curation_batches: List[Dict[str, Any]] = []
        # Usage totals
        self.totals = {
            "iterations": 0,
            "step_tokens_in": 0,
            "step_tokens_out": 0,
            "read_tokens_in": 0,
            "read_tokens_out": 0,
            "step_cost_usd": 0.0,
            "read_cost_usd": 0.0,
            "total_cost_usd": 0.0,
        }

    def save_json(self, name: str, obj: Any):
        p = self.artifacts_dir / name
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        return p

    # Simplified workflow: no persistent catalog/indices
    def normalize_url(self, url: str) -> str:
        """Normalize URLs to reduce duplicates/noise."""
        try:
            s = (url or "").strip()
            if not s:
                return s
            # Drop fragment
            if "#" in s:
                s = s.split("#", 1)[0]
            # Strip trailing punctuation/brackets/quotes
            trailing = ")]}>,.;:!\'\""
            changed = True
            while changed and s:
                before = s
                s = s.rstrip(trailing)
                changed = (s != before)
            return s
        except Exception:
            return url

    def extract_http_urls(self, text: str) -> List[str]:
        if not text:
            return []
        pattern = re.compile(r"https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE)
        urls = pattern.findall(text)
        seen = set()
        out = []
        for u in urls:
            n = self.normalize_url(u)
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def plan_step(self) -> Tuple[StepOutput, Dict[str, Any]]:
        # Build compact memory view: only visited and findings
        mem_view = {
            "visited": list(self.memory.visited),
            "findings": "\n".join(self.memory.findings),
        }
        user = render_template(
            STEP_USER_TEMPLATE,
            {
                "instruction": self.cfg.instruction,
                "memory_json": json.dumps(mem_view, ensure_ascii=False),
                "today": self.today,
                "stream_context": self.stream_context,
            },
        )
        system_text = render_template(STEP_SYSTEM, {"today": self.today})
        self.logger.step_request(system_text, user, iter_no=self.memory.run_count)
        try:
            step, usage = parse_with_schema(
                self.client,
                self.model,
                system_text,
                user,
                StepOutput,
                reasoning_effort="low",
                text_verbosity="low",
            )
            try:
                self.logger.step_response(step.model_dump(), iter_no=self.memory.run_count)
            except Exception:
                pass
            return step, usage
        except Exception:
            # Graceful fallback: avoid aborting the run on refusals or non-JSON
            try:
                self.logger.info("Step fallback", "LLM returned non-JSON or refusal; exiting gracefully", iter_no=self.memory.run_count)
            except Exception:
                pass
            # Exit this exploration cleanly without proposing further queries
            fallback = StepOutput(
                planner="Fallback: planner refused or returned non-JSON. Ending exploration gracefully.",
                search_queries=[],
                confidence=0.0,
                stop=True,
            )
            usage = {"model": self.model, "input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0.0}
            try:
                self.logger.step_response(fallback.model_dump(), iter_no=self.memory.run_count)
            except Exception:
                pass
            return fallback, usage

    def run_search(self, query: str) -> List[Dict[str, Any]]:
        res: Dict[str, Any] = {}
        try:
            res = surfer_client.google_search(query=query, headless=self.cfg.headless)
        except Exception:
            res = {}
        raw_items = (((res or {}).get("result") or {}).get("items") or {}).get("serp", {}).get("items", [])
        items = list(raw_items)
        try:
            visited_norm = set(self.normalize_url(u) for u in self.memory.visited)
            filtered: List[Dict[str, Any]] = []
            for it in items:
                link = (it.get("link") or "").strip()
                if not link:
                    continue
                nu = self.normalize_url(link)
                if nu and nu in visited_norm:
                    continue
                filtered.append(it)
            items = filtered
        except Exception:
            pass
        if items:
            try:
                items = self.filter_serp_items(items, query)
            except Exception:
                items = list(raw_items)
        lines = []
        for it in items[:12]:
            link = (it.get("link") or "").strip()
            title = (it.get("title") or "").strip()
            body = (it.get("body") or it.get("snippet") or it.get("desc") or "").strip()
            if not link:
                continue
            host = urlparse(link).hostname or ""
            blurb = (" — " + body) if body else ""
            lines.append(f"{title} | {host}{blurb}\n{link}")
        try:
            self.logger.search_overview(query, lines, iter_no=self.memory.run_count)
        except Exception:
            pass
        ts = int(time.time() * 1000)
        try:
            self.save_json(f"serp_{ts}.json", items)
        except Exception:
            pass
        return items

    def filter_serp_items(self, items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        # Build LLM request with enumerated idx and available metadata
        enriched = []
        for i, it in enumerate(items):
            enriched.append(
                {
                    "idx": i,
                    "position": it.get("position"),
                    "title": it.get("title"),
                    "link": it.get("link"),
                    "raw_link": it.get("raw_link"),
                    "host": it.get("host"),
                    "snippet": it.get("snippet"),
                    "time": it.get("time"),
                }
            )
        user = render_template(
            SERP_FILTER_USER_TEMPLATE,
            {
                "instruction": self.cfg.instruction,
                "query": query,
                "items_json": json.dumps(enriched, ensure_ascii=False),
                "today": self.today,
                "stream_context": self.stream_context,
            },
        )
        filt, _usage = parse_with_schema(
            self.client,
            self.model,
            SERP_FILTER_SYSTEM,
            user,
            FilterOutput,
            reasoning_effort="minimal",
            text_verbosity="low",
        )
        idxs = [int(x) for x in getattr(filt, "choose_indices", []) if isinstance(x, int) or (isinstance(x, str) and str(x).isdigit())]
        choose = set(i for i in idxs if 0 <= i < len(items))
        # Fallback: if filter selected nothing, keep top 5 by position
        if not choose:
            choose = set(range(min(5, len(items))))
        return [items[i] for i in choose]

    def read_pages_batch(self, urls: List[str]) -> Tuple[CuratedReadingOutput, Dict[str, Any], Dict[int, str], List[Dict[str, Any]]]:
        self._check_cancel()
        pages_ctx: List[Dict[str, Any]] = []
        catalog: List[Dict[str, Any]] = []

        resp: Dict[str, Any] = {}
        try:
            resp = surfer_client.read_wave(
                urls=urls,
                headless=self.cfg.headless,
                citations=True,
                prune=False,
            )
        except Exception:
            resp = {}

        pages_raw = ((resp or {}).get("result") or {}).get("pages", [])
        for idx, raw in enumerate(pages_raw):
            input_url = urls[idx] if idx < len(urls) else ""
            try:
                final_url = (raw.get("url") or "").strip()
            except Exception:
                final_url = ""
            markdown = ""
            try:
                markdown = (raw.get("content") or "").strip()
            except Exception:
                markdown = ""
            references = (raw.get("references") or "").strip() if isinstance(raw, dict) else ""
            if references:
                markdown = (markdown.rstrip() + "\n\n" + references).strip()
            links = []
            try:
                links = list(raw.get("links") or [])
            except Exception:
                links = []
            if not links:
                links = self.extract_http_urls(markdown)[:200]
            meta = self.serp_meta.get(self.normalize_url(final_url)) or {}
            if not meta and isinstance(raw, dict):
                meta = {
                    "title": (raw.get("title") or "").strip(),
                    "snippet": (raw.get("snippet") or raw.get("desc") or raw.get("body") or "").strip(),
                    "time": (raw.get("time") or "").strip(),
                }
            target_url = final_url or input_url
            page_obj: Dict[str, Any] = {"url": target_url, "_links_raw": links, "markdown": markdown}
            if meta:
                st = str(meta.get("title") or "").strip()
                ss = str(meta.get("snippet") or "").strip()
                tt = str(meta.get("time") or "").strip()
                if st:
                    page_obj["serp_title"] = st
                if ss:
                    page_obj["serp_snippet"] = ss
                if tt:
                    page_obj["serp_time"] = tt
            pages_ctx.append(page_obj)

        # Now assign a global, per-batch index to every link deterministically
        idx_counter = 0
        for page in pages_ctx:
            links = page.pop("_links_raw", []) or []
            indices: List[int] = []
            # Keep top 30 reference URLs per page
            for link in links[:30]:
                catalog.append({"idx": idx_counter, "url": link})
                indices.append(idx_counter)
                idx_counter += 1
            page["indices_on_page"] = indices

        # Build XML-like pages text blocks (IDs: page_1, page_2, …) in async completion order
        idx_to_url_temp = {int(e["idx"]): str(e["url"]) for e in catalog if "idx" in e and "url" in e}
        blocks: List[str] = []
        batch_pages: List[Dict[str, Any]] = []
        for i, page in enumerate(pages_ctx, start=1):
            pid = f"page_{i}"
            lines: List[str] = []
            lines.append(f"<page {pid}>")
            lines.append(f"url: {page.get('url', '')}")
            st = str(page.get("serp_title") or "").strip()
            ss = str(page.get("serp_snippet") or "").strip()
            tt = str(page.get("serp_time") or "").strip()
            if st:
                lines.append(f"serp_title: {st}")
            if ss:
                lines.append(f"serp_snippet: {ss}")
            if tt:
                lines.append(f"serp_time: {tt}")
            lines.append("")
            lines.append("<markdown content>")
            lines.append(page.get("markdown", ""))
            lines.append("</markdown content>")
            lines.append("")
            lines.append("<reference index>")
            # Only include up to 30 indices per page; map to URLs
            for idx in list(page.get("indices_on_page", []) or [])[:30]:
                url_val = idx_to_url_temp.get(int(idx), "")
                if url_val:
                    lines.append(f"{idx} {url_val}")
            lines.append("</reference index>")
            lines.append(f"</page {pid}>")
            blocks.append("\n".join(lines))
            batch_pages.append({"id": pid, "url": page.get("url", ""), **({"serp_title": st} if st else {}), **({"serp_snippet": ss} if ss else {}), **({"serp_time": tt} if tt else {})})

        pages_text = "\n\n".join(blocks)

        mem_read = {"findings": "\n".join(self.memory.findings)}
        user = render_template(
            MULTI_EXTRACT_USER_TEMPLATE,
            {
                "instruction": self.cfg.instruction,
                "memory_json": json.dumps(mem_read, ensure_ascii=False),
                "pages_text": pages_text,
                "today": self.today,
                "stream_context": self.stream_context,
            },
        )
        try:
            self.logger.reading_batch_request(MULTI_EXTRACT_SYSTEM, user, iter_no=self.memory.run_count)
        except Exception:
            pass
        combined, usage = parse_with_schema(
            self.client,
            self.model,
            MULTI_EXTRACT_SYSTEM,
            user,
            CuratedReadingOutput,
            reasoning_effort="minimal",
            text_verbosity="medium",
        )
        try:
            self.logger.reading_batch_response(combined.model_dump(), iter_no=self.memory.run_count)
        except Exception:
            pass
        # Build idx → url map to let caller resolve choose_indices
        idx_to_url = {int(e["idx"]): str(e["url"]) for e in catalog if "idx" in e and "url" in e}
        return combined, usage, idx_to_url, batch_pages

    def run(self) -> Dict[str, Any]:
        step_count = 0
        report_links: List[Dict[str, str]] = []
        plan_log: List[str] = []
        while True:
            self._check_cancel()
            step_count += 1
            if step_count > self.cfg.max_steps:
                break

            # Mark run boundary and increment run counter; add separator to findings
            self.memory.run_count += 1
            self.memory.findings.append(f"-------- FINDINGS RUN {self.memory.run_count} -------")

            # Ask Step for search queries
            step, step_usage = self.plan_step()
            if getattr(step, "planner", None):
                plan_log.append(step.planner)

            # Persist memory snapshot
            mem_dump = self.memory.model_dump()
            self.save_json("memory.json", mem_dump)
            try:
                self.logger.memory_full(mem_dump, iter_no=self.memory.run_count)
            except Exception:
                pass

            if step.stop:
                break

            # 1) Run searches in parallel and collect seed URLs
            queries = [q.strip() for q in getattr(step, "search_queries", []) if q and q.strip()]
            searches_run = 0
            seed_urls: List[str] = []
            if queries:
                max_workers = len(queries) if int(self.cfg.search_concurrency) <= 0 else min(len(queries), int(self.cfg.search_concurrency))
                with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
                    futs = {ex.submit(self.run_search, q): q for q in queries}
                    for fut in as_completed(futs):
                        try:
                            items = fut.result() or []
                            searches_run += 1
                            for it in items[:20]:
                                link = (it.get("link") or "").strip()
                                if link:
                                    nu = self.normalize_url(link)
                                    seed_urls.append(nu)
                                    # Capture SERP metadata for Reader context (depth 1 pages)
                                    self.serp_meta[nu] = {
                                        "title": str(it.get("title") or ""),
                                        "snippet": str(it.get("snippet") or it.get("desc") or it.get("body") or ""),
                                        "time": str(it.get("time") or ""),
                                    }
                        except Exception:
                            continue

            # 2) Reading waves: breadth-first up to max_depth, batches of N
            visited_set = set(self.memory.visited)
            frontier: Deque[Tuple[str, int]] = deque()
            pushed: set[str] = set()
            for u in seed_urls:
                if u and u not in visited_set and u not in pushed:
                    frontier.append((u, 1))
                    pushed.add(u)

            pages_read = 0
            waves = 0
            total_read_usage = {"input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0.0}
            while frontier:
                self._check_cancel()
                # Build all batches for current wave
                batches: List[Tuple[List[str], int]] = []  # (urls, depth)
                while frontier and len(batches) < 100000:  # soft cap
                    batch: List[str] = []
                    depth = 0
                    while frontier and len(batch) < int(self.cfg.batch_size or 5):
                        u, d = frontier.popleft()
                        depth = max(depth, d)
                        if d > int(self.cfg.max_depth or 3):
                            continue
                        if u in visited_set:
                            continue
                        batch.append(u)
                    if batch:
                        batches.append((batch, depth))
                if not batches:
                    break
                # Log batches
                try:
                    for urls, depth in batches:
                        self.logger.read_batch_overview(urls, depth=depth, iter_no=self.memory.run_count)
                except Exception:
                    pass
                # Execute batches in parallel
                max_workers = len(batches) if int(self.cfg.batch_concurrency) <= 0 else min(len(batches), int(self.cfg.batch_concurrency))
                results: List[Tuple[List[str], int, Optional[CuratedReadingOutput], Dict[str, Any], Dict[int, str], List[Dict[str, Any]]]] = []
                from concurrent.futures import ThreadPoolExecutor as _TP, as_completed as _ac
                with _TP(max_workers=max(1, max_workers)) as ex:
                    futs = {ex.submit(self.read_pages_batch, urls): (urls, depth) for (urls, depth) in batches}
                    for fut in _ac(futs):
                        self._check_cancel()
                        urls, depth = futs[fut]
                        try:
                            combined, read_usage, idx_to_url, batch_pages = fut.result()
                        except Exception:
                            combined, read_usage, idx_to_url, batch_pages = None, {}, {}, []
                        results.append((urls, depth, combined, read_usage, idx_to_url, batch_pages))
                # Merge results
                for urls, depth, combined, read_usage, idx_to_url, batch_pages in results:
                    # Collect curated findings into memory (summaries only)
                    if combined and getattr(combined, "curations", None):
                        for cur in (combined.curations or []):
                            try:
                                if cur.summary:
                                    self.memory.findings.append(cur.summary)
                            except Exception:
                                continue
                    # Aggregate curations + batch page mapping for final run output
                    if combined:
                        try:
                            self.curation_batches.append({
                                "pages": batch_pages,
                                "curations": [
                                    {"summary": c.summary, "pages": list(c.pages or [])}
                                    for c in (combined.curations or [])
                                ],
                            })
                        except Exception:
                            pass
                    # Next links: indices only → map to URLs via idx_to_url
                    indices = list(getattr(combined, "choose_indices", []) or []) if combined else []
                    # Normalize and map indices to URLs
                    picks_urls: List[str] = []
                    for x in indices:
                        try:
                            i = int(x)
                        except Exception:
                            continue
                        u = idx_to_url.get(i)
                        if not u:
                            continue
                        picks_urls.append(u)
                    for url_s in picks_urls:
                        nu = self.normalize_url(str(url_s))
                        if not nu:
                            continue
                        if nu in visited_set or nu in pushed:
                            continue
                        frontier.append((nu, depth + 1))
                        pushed.add(nu)
                    # Mark visited for batch
                    for u in urls:
                        if u not in visited_set:
                            visited_set.add(u)
                            self.memory.visited.append(u)
                            pages_read += 1
                            report_links.append(
                                {
                                    "url": u,
                                    "title": (self.memory.findings[-1] or "").split(". ")[0][:120] if self.memory.findings else "",
                                    "host": urlparse(u).hostname or "",
                                    "reason": "read batch findings",
                                }
                            )
                    waves += 1
                    if read_usage:
                        total_read_usage["input_tokens"] += int(read_usage.get("input_tokens", 0))
                        total_read_usage["output_tokens"] += int(read_usage.get("output_tokens", 0))
                        total_read_usage["total_cost_usd"] += float(read_usage.get("total_cost_usd", 0.0))

            # Update totals and print iteration summary
            self.totals["iterations"] += 1
            # Step usage
            if step_usage:
                si = int(step_usage.get("input_tokens", 0)); so = int(step_usage.get("output_tokens", 0))
                sc = float(step_usage.get("total_cost_usd", 0.0))
                self.totals["step_tokens_in"] += si
                self.totals["step_tokens_out"] += so
                self.totals["step_cost_usd"] += sc
                self.totals["total_cost_usd"] += sc
            # Read usage (sum across waves)
            ri = int(total_read_usage.get("input_tokens", 0)); ro = int(total_read_usage.get("output_tokens", 0))
            rc = float(total_read_usage.get("total_cost_usd", 0.0))
            self.totals["read_tokens_in"] += ri
            self.totals["read_tokens_out"] += ro
            self.totals["read_cost_usd"] += rc
            self.totals["total_cost_usd"] += rc

            self.logger.iteration_summary(
                iter_no=self.memory.run_count,
                searches_run=searches_run,
                pages_read=pages_read,
                waves=waves,
                visited_len=len(self.memory.visited),
                step_usage=step_usage,
                read_usage=total_read_usage,
                totals=self.totals,
            )

        # Print final run summary
        try:
            self.logger.run_summary(self.totals)
        except Exception:
            pass

        # Print final curated results
        try:
            self.logger.run_results(self.curation_batches)
        except Exception:
            pass

        return {
            "findings": self.memory.findings,
            "visited": self.memory.visited,
            "top_links": report_links,
            "curations_batches": self.curation_batches,
            "plan_log": plan_log,
            "confidence": (self.memory.findings and 0.8) or 0.5,
            "artifacts_dir": str(self.artifacts_dir),
        }

    def _check_cancel(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise RuntimeError("explorer job canceled")
