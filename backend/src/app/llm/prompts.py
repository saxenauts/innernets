GENERATE_SEARCH_QUERIES = (
    "You are generating 3–4 high-quality web search queries."
    " Use concise phrasing, include operators like site:, filetype, inurl when helpful,"
    " and balance recency with foundational context. Return only the fields defined in the schema."
)

EVALUATE_CANDIDATES = (
    "Given candidate titles/snippets/domains, score for fit, credibility, and novelty."
    " Use an integer 0–100 scale for the overall score (no decimals)."
    " Mark promising items for reading. Return only the schema fields."
)

PROPOSE_FOLLOWUPS = (
    "Given observed gaps or bias, propose up to six follow-up query schemas to widen or deepen coverage."
    " Use diverse angles. Return only the schema fields."
)

COMPOSE_STREAM_ITEMS = (
    "Select ~10–14 items that best serve the mission now. Dedupe near-duplicates,"
    " write a short hook (<=120 chars) and a reason (<=90) for each."
    " Return only the schema fields."
)
