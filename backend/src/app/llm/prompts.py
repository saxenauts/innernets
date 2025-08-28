SYSTEM_PREAMBLE = (
    "You are InnerNets.StreamAgent. "
    "Return ONLY a single valid JSON object that conforms to the provided schema—no prose, no markdown, no comments. "
    "Never invent fields or IDs. When asked to select links, select ONLY from the provided `id` values (e.g., \"01\",\"02\"). "
    "Keep outputs minimal. If unsure, return an empty array rather than fabricating."
)

# 1) Generate Search Queries (10)
GENERATE_SEARCH_QUERIES = (
    'MISSION:\n"{{mission}}"\n\n'
    "CONTEXT (JSON):\n{{additional_context_json}}\n\n"
    "TASK:\n"
    "Plan exactly 10 concise web search queries that best advance the mission right now.\n"
    "Blend: \n"
    "- Now (what changed recently), \n"
    "- Context (explainers/backfile if learner), \n"
    "- People/Sources (named creators/outlets), \n"
    "- Adjacent sparks (neighbor ideas), \n"
    "- Practical/How-to if relevant.\n"
    "Use site: / filetype: / quoted phrases when it helps precision.\n\n"
    "For each query choose:\n"
    "- \"keyword\" for precise lookups, named entities, site: scoping, regulations, or exact phrases.\n"
    "- \"neural\" for broad/adjacent concept discovery or when novelty is desired.\n\n"
    "Honor user taste from CONTEXT (domains pinned/muted, novelty target). Avoid duplicates and near-synonyms. \n"
    "Return JSON: { \"queries\": [ { \"query\": \"...\", \"query_type\": \"keyword|neural\" }, ... ] } (10 items)."
)

# 3) Filter Candidates → 2–3 IDs
FILTER_CANDIDATES = (
    'MISSION:\n"{{mission}}"\n\n'
    "CANDIDATES (JSON array of {id,title,snippet,domain,published_at?}):\n{{candidates_json}}\n\n"
    "CONTEXT (JSON):\n{{additional_context_json}}\n\n"
    "TASK:\n"
    "Select ONLY the 2–3 candidates to READ IN FULL now. \n"
    "Rules:\n"
    "- Prefer high-signal sources, recency (if tracking), or canonical explainers (if learning).\n"
    "- Remove near-duplicates: if multiple items cover the SAME thing, pick the single best (credibility, freshness, clarity).\n"
    "- Include at most one from the same domain unless both are uniquely valuable.\n"
    "- Do NOT invent IDs. Choose strictly from the provided `id` values.\n"
    "Output JSON: { \"selected_ids\": [\"..\",\"..\"] }"
)

# 5) Propose Followups (3–6)
PROPOSE_FOLLOWUPS = (
    'MISSION:\n"{{mission}}"\n\n'
    "INITIAL QUERIES (JSON):\n{{initial_queries_json}}\n\n"
    "READ (JSON array of {id,title,domain,summary}):\n{{read_summaries_json}}\n\n"
    "STREAM CONTEXT (JSON):\n{{additional_context_json}}\n\n"
    "PRIOR SURFACED (optional JSON of {url,title}):\n{{prior_urls_json}}\n\n"
    "TASK:\n"
    "Identify gaps, blind spots, or biases in what we just covered. Propose 3–6 **follow-up** queries that either:\n"
    "- add perspective diversity (regions, methods, credible contrarians),\n"
    "- deepen specifics (methods, data, benchmarks, case studies),\n"
    "- explore adjacent sparks likely to delight the user.\n\n"
    "Routing:\n"
    "- \"keyword\" for precise entities, site: scoping, regulations, exact titles.\n"
    "- \"neural\" for broader conceptual or adjacent exploration.\n\n"
    "Return JSON: { \"followups\": [ { \"query\": \"...\", \"query_type\": \"keyword|neural\" }, ... ] }"
)

# 7) Consolidate Curations (2–6 curations)
CONSOLIDATE_CURATIONS = (
    'MISSION:\n"{{mission}}"\n\n'
    "ITEMS (JSON array of {id,title,domain,snippet_or_summary}):\n{{all_items_json}}\n\n"
    "STREAM CONTEXT (JSON):\n{{additional_context_json}}\n\n"
    "TASK:\n"
    "Cluster items discussing the SAME development/theme into **curations**. \n"
    "For each curation:\n"
    "- Choose a clear, compact title (≤120 chars).\n"
    "- Write a hook (≤140 chars) that explains why this cluster matters \"for you, now\".\n"
    "- Include 3–4 `link_ids` that are genuinely about the same thing. \n"
    "Rules:\n"
    "- No duplicate IDs across curations.\n"
    "- Prefer canonical/original sources; mix voices when useful (not all from the same domain).\n"
    "- Do NOT invent IDs.\n\n"
    "Output JSON: { \n  \"curations\":[\n    {\"title\":\"...\", \"hook\":\"...\", \"link_ids\":[\"..\",\"..\",\"..\"]},\n    ...\n  ]\n}"
)

# (no legacy prompts)
