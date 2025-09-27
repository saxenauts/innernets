Status: Legacy — This document describes the earlier Exa-first, search-only MVP. The product now uses the Surfer agent as the default for Streams. Keep this for historical context and pricing notes. For the current system, see `docs/architecture-runs-scheduler.md` and `docs/integration.md`.

Got it. Here’s a copy-pasteable doc that corrects the Exa pricing details, answers the “Contents \$1/1–100?” confusion, and locks the plan to a **two-step, search-only** loop with **Exa** as the sole provider.

---

# InnerNets — Search-Only Plan (Exa-first, Two-Step)

**Objective.** Ship a reliable search-only pipeline (no crawler, no Playwright yet) that produces high-quality Streams using Exa’s **search + contents**, under **\$100/mo**, with a per-run latency budget ≤ **5 minutes**.
**Assumption.** 10 streams daily ⇒ \~**300 runs/month**.

---

## 0) Exa pricing (what we actually pay)

**Search (per 1k requests)**

* **Keyword** (SERP-style): **\$2.50 / 1k** (1–100 results) → **\$0.0025/query**
* **Neural** (semantic) or **Auto**: **\$5.00 / 1k** (1–25 results) → **\$0.005/query**
  (If you request **26–100** results with Neural/Auto, it jumps to **\$25 / 1k** → avoid by keeping `numResults ≤ 25`.)

**Contents (per 1k pages)**

* **Text**, **Highlights**, **Summary**: **\$1.00 / 1k pages** each → **\$0.001 per page per content type**
  → If you ask for **text + highlights** on the same page, that’s **\$0.002** for that page; **text + summary** = **\$0.002**, etc.

> **Clarification of the “1–100 = \$1” line:** It’s **not** \$1 per page. It’s **\$1 per 1,000 pages** (i.e., **\$0.001/page**). The 1–100 label is just the band label; you still pay per page. Exa also returns `costDollars` per call with a breakdown, so you can meter per run.

We will **not** use Exa “Answer/Research” SKUs in this MVP.

---

## 1) Loop (per Stream, per run)

**Two steps, LLM-guided. All queries are natural-language.**

LLM invocation: function-first via the adapter (OpenAI tool schema). We avoid chat; each step calls a specific function with JSON-schema parameters.

1. **Assimilate → RunBrief (LLM).** Understand mission + “Sources & Creators” + memory (opened/saved/hidden, seen domains, novelty slice).
2. **Step A — Plan & Search.** LLM emits **3–4 NL queries** (mix of Now / On-ramps / Context / People/Places / Adjacent as helpful). Function: `generate_search_queries(context, hints?)`.
   Call **`POST /search`** with `type: "keyword"` for most, `type: "neural"` for 1–2 novelty queries, **`numResults ≤ 25`**.
3. **Selective Read.** LLM flags promising candidates; request **contents: { text: true }** for only those.
   **Default: request `text` only** (skip highlights/summary to avoid double-charging).
4. **Step B — Sharpened Search.** From skimmed texts, LLM proposes **3–4** sharper queries; fetch again (same search types), and **read** a smaller slice of promising pages (`text: true`).
5. **Compose.** LLM selects **\~10–14** items, dedupes, writes **hook** (≤120 chars) + **reason** (≤90; “why this, for you, now”), and marks **New since last run**. Update memory. Function: `compose_stream_items(candidates, target, context?)`.

**Caps (per run, enforce in code):**

* **Queries ≤ 8** total (Step A 3–4, Step B 3–4).
* **Reads 18–40 pages** total (LLM-gated).
* **Neural share ≤ 30%** of queries.
* **`numResults ≤ 25`** for Neural/Auto to stay in the cheap tier.

---

## 2) Cost model (10 streams daily ⇒ 300 runs/mo)

**Unit costs:**

* Keyword query = **\$0.0025**
* Neural/Auto (≤25 results) = **\$0.0050**
* One page **text** read = **\$0.0010**

**Per-run scenarios (aligned to your two-step plan):**

* **Baseline (cheap):** 6 queries (5 Keyword + 1 Neural), **18** page reads

  * Search = (5×0.0025) + (1×0.0050) = **\$0.0175**
  * Contents = 18×0.0010 = **\$0.0180**
  * **Total/run = \$0.0355 → \$10.65/mo**

* **Median:** 8 queries (6 Keyword + 2 Neural), **25** page reads

  * Search = (6×0.0025) + (2×0.0050) = **\$0.0250**
  * Contents = 25×0.0010 = **\$0.0250**
  * **Total/run = \$0.0500 → \$15.00/mo**

* **Upper (still fine):** 8 queries (6 Keyword + 2 Neural), **40** page reads

  * Search = **\$0.0250**
  * Contents = **\$0.0400**
  * **Total/run = \$0.0650 → \$19.50/mo**

Even at the upper case, we sit far under the **\$100/mo** ceiling.

> If you ever flip **Neural** queries to **Auto**, assume the ≤25 tier price (**\$0.005/query**) unless you explicitly raise `numResults`. Keep it ≤25.

---

## 3) Calling Exa (minimal contract)

* Prefer **`searchAndContents`** / **`/search` with `contents: { text: true }`** for the subset of IDs you select (saves a second trip).
* Set **`numResults`** explicitly (≤25 for Neural/Auto).
* Pass **`type: "keyword"`** for most queries, **`"neural"`** for novelty/semantic jumps.
* Optional: **`text: { maxCharacters: <cap> }`** to keep response size/token use in check (e.g., a few thousand chars).
* Do **not** request highlights/summary by default (they each add **\$0.001/page**).

**Telemetry:** read `costDollars` from each response; persist `queries`, `reads`, `finalItems` for per-run auditing.

---

## 4) Micro-prompts (drop-in)

**Assimilator**
“Summarize the mission and named sources. From memory, note what we showed, what the user engaged with, and gaps to close. Propose a novelty slice (\~20%). Output a short `RunBrief`.”

**Planner**
“From `RunBrief`, propose **3–4 natural-language queries** that best move the mission now. Blend the user’s sources/creators into phrasing. Include media words (‘podcast’, ‘playlist’, ‘paper’) only if helpful.”

**Reader (Gap-finder)**
“Given titles/snippets and selected page **texts**, list what’s missing or biased. Propose **3–4** sharper follow-up queries to widen/deepen.”

**Composer**
“Select \~12 items that best serve the mission. Dedupe. For each: `title`, `url`, `hook` (≤120), `reason` (≤90: ‘why this, for you, now’). Include video/podcast/code/paper only when useful.”

---

## 5) Guardrails & defaults

* **Results cap:** `numResults ≤ 25` on Neural/Auto to avoid the expensive tier; Keyword can go up to 100 for the same price—but keep payloads modest.
* **Reads discipline:** default to **text only**; avoid double-charging (no highlights/summary unless you have a structured extraction need).
* **Dedupe:** canonical URL hashing; favor domain diversity.
* **Latency:** 5-minute budget is fine; the LLM must justify Step-B queries from Step-A reads.
* **Frequency:** hourly runs supported; costs remain low with these caps.

---

## 6) What’s explicitly later

* **Own fetcher + Playwright (Crawl4AI)** for dynamic pages.
* **Creator/source index + polling** (RSS/Substack/YouTube/podcasts).
* Any additional providers.

---

## 7) Why this works now

* One vendor, one API, simple math. **Search + contents** lets the LLM compose real hooks/reasons without a crawler.
* Contents is **cheap** when you’re selective (**\$0.001/page**).
* The two-step plan (3–4 queries each) keeps quality high while costs stay in the **\$11–\$20/mo** range for 10 daily streams—even at upper bounds.
