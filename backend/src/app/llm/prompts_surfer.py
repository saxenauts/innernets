SYSTEM_PREAMBLE = (
    "You are InnerNets.SurferPlanner. "
    "Return ONLY a single valid JSON object that conforms to the provided schema—no prose."
)

GENERATE_SURFER_INSTRUCTION = (
    'MISSION:\n"{{mission}}"\n\n'
    "SOURCES HINTS (optional):\n{{sources_hints}}\n\n"
    "PRIOR CONTEXT (JSON):\n{{additional_context_json}}\n\n"
    "TASK:\n"
    "Draft a single, concise instruction for a web research agent that will: \n"
    "- explore and discover what MATTERS NOW for this mission,\n"
    "- prefer credible, canonical sources, and\n"
    "- avoid repeating previously surfaced items in PRIOR CONTEXT.\n\n"
    "Mention any key domains or constraints if important. Keep under 320 characters.\n\n"
    "Output JSON: { \"instruction\": \"...\" }"
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
