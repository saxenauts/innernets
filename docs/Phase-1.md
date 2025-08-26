# InnerNets — Search‑Only MVP Spec ("Streams")

## 0) One‑liner

Right information for the right person at the right time in the right format — delivered as **Streams**: a living, link‑first space that pulls you into new angles on the missions you care about.

---

## 1) Vision & Mission

**Vision.** Give every curious person an internet that *works with them*: widening perspective, deepening understanding, and staying out of the way.

**Mission.** Build a proactive, receipts‑light, **search‑only** system that composes multi‑angle, browseable outputs from the open web, learns your taste over time, and remains portable (shareable/RSS) rather than chat‑locked.

---

## 2) Pain Points We Solve

* \*\*Doom Scrolling \*\*

* \*\*Cross Web Multi Modal Inputs in one feed \*\*

* **Chat‑locked reports.** Current schedulers (ChatGPT Tasks, Yutori Scouts) produce long, memo‑like posts in chat; they don’t feel like a place to *surf*.

* **Shallow perspective.** One voice dominates. Users want credible *angles* (support, skepticism, history, adjacent fields) without babysitting query design.

* **Not source‑shaped.** Hard to steer toward YouTube/podcasts/papers/code, or to favor/avoid specific sources.

* **Hard to share.** Useful findings remain trapped in a chat thread.

---

## 3) Why Now / What the Internet Enables

* **LLM can understand humans with reasoning.** Think of a kid from India who wants to get into hardware and is inspired by it, but has no local ecosystem, internet is his only hope. And today's web will suck away his attention into identity and culture wars, and the web will fail him. The earlier web used to be great, but the new web is parasitic, and this needs fixing and the information streaming needs to get decentralized and community oriented and help the kid make better progress with learning hardware with a more proactive AI that can understand the kid's context and can add more to it. 

- **LLM + search** can *compose* angles from titles/snippets/metadata without owning a crawler.
- **Grounded search APIs** (Bing grounding) provide high‑quality, fresh candidates.
- **Lightweight memory** (seen titles/domains/authors) enables delta‑only updates and novelty without tracking users deeply.
- **Portable outputs** (public pages/RSS/email) turn personal research into networked knowledge.

---

## 4) Differentiation vs ChatGPT Tasks & Yutori Scouts

* **Format:** Not a chat report. **Currents** are link‑first, browseable, and public by default (share/RSS).
* **Angles by default:** Every run mixes **Consensus, Skeptic, Methods, History, Adjacent, Market/Policy** as needed (generative, not rigid).
* **In‑run branching:** Mid‑run discoveries spawn *wider and deeper* queries in the same run (Yutori tends to go deeper only).
* **Media‑aware:** Guaranteed slots for **Watch/Listen/Read/Code** so it feels like surfing, not memo‑reading.
* **Minimal receipts:** Only “New since last run” + tiny info popover (queries run); no score dumps.
* **Open‑web posture:** We push people to original links, not a walled chat.

---

## 5) Principles for Our Persona (self‑directed explorers)

1. **Link‑first.** The web is the product; we add orientation, not enclosure.
2. **Angles over rankings.** Teach the landscape, not a scoreboard.
3. **Serendipity with guardrails.** Always reserve a novelty slice; keep it credible.
4. **Frictionless steering.** Mention sources inline in the mission text (e.g., “favor arXiv, Substacks A/B, YouTube C”) — no settings labyrinth.
5. **Minimal memory.** Remember seen titles/domains/authors and quick feedback (Save / More‑like‑this / Less‑like‑this). That’s enough for delta + taste.
6. **Portable by default.** Every Current has a public URL/RSS/email; cloning/forking later.
7. **Quiet craft.** No levels, streaks, or gamified noise.

---

## 6) Neuroscience & Psychology → Design Heuristics

* **Information‑gap (Loewenstein):** Use one‑line *hooks* that highlight a precise missing piece (“What flaw did GTPO fix?”) to trigger curiosity.
* **Intermediate uncertainty (Kidd & Hayden):** Mix familiar and novel; keep novelty \~10–20% per run so users aren’t lost or bored.
* **Curiosity–memory link (Gruber & Ranganath):** Prompt micro‑predictions before opening a link (“Expect: training method tweak”) to boost later recall.
* **Diversive vs epistemic curiosity (Berlyne):** Media lanes (videos/podcasts) scratch diversive; angle sections feed epistemic. Show both together.
* **Cognitive load:** Cluster by angle; reduce hard context switches; progressive disclosure (details expand on demand).
* **Closure:** End each run with a short “You’ve got the picture → open 1 now, save 2 for later” moment to avoid endless scroll.

---

## 7) What We Ship **Today** (search‑only)

**Objects**

* **Stream : { mission\_text, cadence, seen\_titles/domains/authors, source hints (inline), public\_slug }**
* **Run Output:** Angled sections + media lanes, each with link cards and one‑line hooks; “New since last run” markers.
* **Memory:** simple sets + lightweight preferences (saved/hidden sources).

**Delivery**

* Web page for each Stream (public URL), RSS feed, and email digest.
* No chat interface; optional tiny popover with the queries run.

---

## 8) Search Loop (per Stream, per run) — **AI‑forward** (Bing Grounding + LLM)

**Goal:** produce a Stream that feels intelligent and alive. No rigid categories or per‑modality quotas. The LLM plans and adapts the search strategy each run using context from the Stream and lightweight memory.

**Inputs**

* `mission_text` (natural language; may include inline source hints like “favor arXiv; avoid listicles; Mumbai/Pune”).
* `stream_context` (summary of last runs; items opened/saved/hidden; seen\_url\_hashes; seen\_domains; followed/muted creators; novelty\_budget; cadence).
* `supply_context` (what we already index for this topic; known useful surfaces; geo/price constraints if any; cost/latency budget).

**Loop**

1. **Assimilate context (LLM).** Create a brief internal summary: what we’ve already covered, what the user engaged with, and gaps (missing creators/mediums/regions; “starter” needs if beginner).
2. **Plan the run (LLM).** Draft a *search plan* for this run only: target outcomes (e.g., “what changed in 7d”, “starter library”, “hands‑on kits < ₹3000”, “local communities”), suggested modalities (text/video/audio/code) *only if helpful*, recency window, and constraints (site filters, geo, price, language).
3. **Generate query schemas (LLM).** Produce diverse schemas with operators (`site:`, `inurl:pdf`, filetype, price/geo), plus 15–20% exploration beyond known domains.
4. **Make concrete queries (LLM) & **Fetch** (Bing Grounding).** For each schema, emit concrete queries and fetch top‑K results (K≈6–8). Normalize: canonical URL, strip UTM, detect type by domain/path, parse date when available.
5. **Evaluate candidates (LLM).** Score *fit, credibility, novelty* qualitatively from title/snippet/domain; detect **Latest** items and also **Context** items that teach.
6. **In‑run branching (LLM).** If coverage is thin or lopsided, auto‑propose ≤6 follow‑up schemas to widen/deepen (e.g., “competitions near {{city}}”, “beginner playlists”, “people to follow”, “adjacent concept X”). Fetch and merge.
7. **Enrich & merge (LLM).** Collapse near‑duplicates; attach short hooks (≤120 chars) and one‑line reasons (≤90 chars: *why this, for you, now*). Add light metadata (price, location, duration) when obvious.
8. **Delta filter & memory update.** Drop items whose canonical URL hash is in memory unless flagged as resurfaced context; update `seen_*` and quick feedback signals.
9. **Compose the Stream (LLM).** Sequence \~10–14 items mixing *Now*, *Practical On‑ramps*, *Context*, and *Adjacent Sparks*. Include video/podcast/code/paper **only if they contribute**—no quotas. Mark **New since last run**.
10. **Publish.** Render web/RSS/email. Tiny info popover can list the queries used.
11. **Log & guardrails.** Keep a run trace (plan, queries, follow‑ups) for reproducibility; cap vendor calls (\~18) and tokens; fallback to index‑only if a supplier degrades.

**Pseudocode**

```
function runStream(stream):
  ctx   = summarizeContext(stream)
  plan  = LLM.plan(ctx)                         // outcomes, recency, constraints
  schemas = LLM.generateSchemas(plan, ctx)
  queries = LLM.makeQueries(schemas, ctx)
  cands = fetchAllViaBing(queries, topK=8)

  critique = LLM.critique(cands, ctx)           // find gaps, bias, thin areas
  if critique.followups:
     fq = LLM.makeQueries(critique.followups, ctx)
     cands += fetchAllViaBing(fq, topK=6)

  items = LLM.compose(cands, ctx, target=12)    // dedupe, hooks, reasons
  items = deltaFilter(items, stream.memory)
  updateMemory(stream, items)
  publish(stream, items, queries+fq)
  return items
```

**Notes**

* Emphasis on **latest**: the planner prefers `recency=7d` when mission implies newsy tracking; relaxes to `30d`/`all` when the stream needs context or primers.
* Beginners: planner may invoke **Starter Library**, **Hands‑On Kits** (with price caps), **Communities/Competitions**, and **People to Follow** playbooks as part of the run—only if the mission suggests it.
* Media awareness: enforce presence of media lanes **only when** useful items exist.
* Exploration: keep a 15–20% novelty slice for outside‑the‑diet domains without causing whiplash.

## 9) User Flow (creating a **Stream**)

1. **Name your mission.** Free text, e.g., “AI tools with persistent user memory—what’s real & useful?”

   * You can *hint sources inline*: “favor arXiv, Substacks A/B, YouTube C; avoid listicles.”
2. **Pick cadence.** Daily AM / Evening / 3× week / Weekly / On discovery.
3. **Start.** We run the loop and produce your first **Current**.
4. **Browse.** Angled sections + media lanes; each card has a crisp hook and opens the original link.
5. **Steer with tiny actions.** Save / More‑like‑this / Less‑like‑this / Follow source. No heavy settings.
6. **Share.** Copy the public URL or RSS. (Forking/contributions later.)

---

## 10) Example Missions (seed set)

* VC ecosystem meta‑shifts (players, defense/infra, regulation).
* AI tools with memory & context (products, frameworks, protocols).
* Local model training & indie hardware (methods, tools, providers).

## 12) Why Big Chat Won’t Chase (and why we can own it)

* **Surface mismatch:** We’re building a public, link‑first browsing space; chat incumbents optimize for chat retention.
* **Editorial risk:** We elevate skepticism and adjacent leaps by default; large platforms avoid that liability.
* **Network effects:** Public Currents create a taste graph (missions, sources, authors) that compounds.

---

---

*Minimal, curious, link‑first. The web is alive again.*
