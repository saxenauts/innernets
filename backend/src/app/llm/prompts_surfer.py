SYSTEM_PREAMBLE = (
    "You are InnerNets.SurferPlanner. "
    "Return ONLY a single valid JSON object that conforms to the provided schema—no prose."
)

GENERATE_SURFER_INSTRUCTION = (
    "<task>\n"
    "You are planning a long-running web exploration that powers a user-facing feed.\n"
    "Your goal: add meaningful new value to the feed by finding the latest updates and complementary perspectives—\n"
    "not repeating prior items. Design BOTH: (1) a concise multi-sentence instruction (2–4 sentences) that tells a browser agent\n"
    "WHAT to search (keywords), WHERE to look (domains/sources), and WHY (purpose); and (2) a compact, multi-paragraph context\n"
    "that summarizes what’s already known and identifies specific gaps or targets to pursue next.\n"
    "Keep the instruction crisp; let the context carry rich details.\n"
    "</task>\n\n"
    "<mission>\n{{mission}}\n</mission>\n\n"
    "<sources>\n{{sources_text}}\n</sources>\n\n"
    "<prior_context>\n{{prior_context_str}}\n</prior_context>\n\n"
    "Return ONLY JSON: {\n"
    "  \"instruction\": string,\n"
    "  \"context\": string\n"
    "}"
)

REMIX_CURATIONS = (
    'MISSION:\n"{{mission}}"\n\n'
    "RAW CURATIONS (JSON from surfer: [{summary,links:[{title,url,domain?}]}]):\n{{raw_curations_json}}\n\n"
    "TASK:\n"
    "Create 2-5 headline-worthy curations tailored to the mission. Each curation should:\n"
    "- Combine one or more of the RAW CURATIONS into a cohesive theme.\n"
    "- Provide a sharp title (<=120 chars) and hook (<=160 chars) that explains why it matters now.\n"
    "- Include 1-4 links pulled ONLY from the provided RAW CURATIONS (never fabricate or alter URLs).\n"
    "- Prefer mixing complementary sources (different domains) when it strengthens the story.\n"
    "Rules:\n"
    "- You may reuse a link in multiple curated items only if it delivers distinct value.\n"
    "- Preserve the original `url`. You may adjust the link title for clarity (<=80 chars).\n"
    "- If RAW CURATIONS is empty, return an empty `curations` array.\n\n"
    "Output JSON: { \n  \"curations\": [\n    {\n      \"title\": \"...\",\n      \"hook\": \"...\",\n      \"links\": [ { \"url\": \"...\", \"title\": \"...\" }, ... ]\n    }, ...\n  ]\n}\n"
)
