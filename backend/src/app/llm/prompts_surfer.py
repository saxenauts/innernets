SYSTEM_PREAMBLE = (
    "You are InnerNets.SurferPlanner. "
    "Return ONLY a single valid JSON object that conforms to the provided schema—no prose."
)

GENERATE_SURFER_INSTRUCTION = (
    "<task>\n"
    "You are planning a long-running web exploration that powers a user-facing feed.\n"
    "Your goal: add meaningful new value to the feed by finding the latest updates and complementary perspectives—\n"
    "not repeating prior items.\n\n"
    "Browser agent behavior (design for this loop):\n"
    "- It will take your instruction and generate search queries.\n"
    "- It will read the top results and also follow salient links inside those pages.\n"
    "- It will use the findings to generate new follow-up queries.\n"
    "- It will iterate this loop 3 times to produce fresh, high-signal curations.\n\n"
    "What you must produce:\n"
    "(1) instruction — a concise multi-sentence paragraph (2–4 sentences) that tells the agent WHAT to search (keywords),\n"
    "    WHERE to look (domains/sources), and WHY (purpose), with guidance that maintains novelty and avoids repeats across iterations.\n"
    "(2) context — a compact, multi-paragraph synthesis of what is already known (from the prior context) and the specific gaps/targets\n"
    "    to pursue next so each iteration trends toward newer information and alternative perspectives.\n"
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
