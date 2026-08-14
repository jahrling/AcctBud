# Prior art & lessons learned

Survey of similar projects (2026-08-13), and what AcctBud should copy or avoid.

## Closest prior art

### Habit-tracker accountability coach (OpenClaw use-case writeup)
<https://github.com/hesamsheikh/awesome-openclaw-usecases/blob/main/usecases/habit-tracker-accountability-coach.md>

A proactive agent that messages the user (Telegram/SMS) at scheduled times and
adapts based on streak data. Its documented lessons map almost 1:1 onto AcctBud:

1. **Active accountability beats passive tracking.** The differentiator is the
   agent reaching out, not the user remembering to open an app. → Push
   notifications are not a nice-to-have; they *are* the product.
2. **Adaptive tone matters.** Static reminders get ignored; encouragement that
   references actual streaks/history increases retention. → The check-in prompt
   should always be built from real journal/graph data, never a canned string.
3. **Fewer habits work better.** Tracking >5 items causes check-in fatigue and
   message avoidance. → Validates the "1 key work item + 1 key personal item"
   framing; cap the daily multiple-choice list at ~5 entries.
4. **Pattern detection adds value.** Weekly summaries like "you skip workouts on
   Wednesdays" help planning. → A weekly review pass over the graph is a
   distinct, high-value feature.
5. **A follow-up cooldown (theirs: 2 hours) prevents spam.** → Nag at most once.

### localllmjournal — local-LLM guided journaling
<https://github.com/superS007/localllmjournal>

FastAPI + vanilla JS frontend, Ollama (llama3.2:3b chat + nomic-embed-text
embeddings), SQLite + ChromaDB, SSE streaming. Flow: brain-dump → LLM asks
gentle clarifying questions → polished entry → user approves and saves.

Takeaways:
- The **draft → clarify → polish → user approves** loop is a good shape for
  evening reflection; the user stays the author of record.
- A 3B-class model is enough for the *conversation*; it's the long-horizon
  memory that needs help. Separating "chat model" from "embedding model" in
  Ollama is the standard pattern and fits TheRig easily.
- SQLite + a vector index is sufficient for v1 recall; graph memory can come
  later (see below).

### self-improvement-4all
<https://github.com/tripathiarpan20/self-improvement-4all>

Privacy-first coaching with open LLMs, using the **Plan–Act–Reflect** paradigm
from Stanford's Generative Agents paper. Takeaway: frame the day as an explicit
Plan (morning) → Act (the day) → Reflect (evening) cycle in both the UX and the
data model — each journal entry belongs to one phase of one day's cycle.

### Other journaling apps scanned
- Journiv (<https://github.com/journiv/journiv-app>) — self-hosted journaling
  with mood tracking, prompts, analytics. Feature-checklist reference.
- Pile (<https://github.com/xiqiuqiu/Pile>) — local-first reflective journaling
  desktop app; good minimal-UI reference.
- Esther (<https://github.com/vortext/esther>) — diary with embedded llama.cpp;
  proof that modest hardware suffices.

## Lessons from the habit-app space generally

From build guides and product roundups (e.g.
<https://www.questera.ai/blogs/build-habit-tracker-app-with-ai>):

- **Friction kills check-ins.** If the daily check-in takes more than a few
  taps, people skip it. The multiple-choice answer format (tap one/many/none)
  is the right instinct — free-text should be optional, offered *after* the
  taps.
- **Pick a psychology angle deliberately** (streak-protection, positive
  reinforcement, identity, social). For a self-hosted single-user tool,
  positive reinforcement + gentle probing fits the stated "not a therapist,
  but reflective" goal; avoid shame mechanics.
- Stall detection (≥3 consecutive misses on an item) is a cheap, useful
  trigger for a different conversation ("should we rescope this?") instead of
  another nag.

## Graph memory for small-context LLMs

The "compress journal/goals into a graph DB" idea is an active research/product
area, so we can stand on existing work:

- **Graphiti** (<https://github.com/getzep/graphiti>, writeup:
  <https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/>) —
  open-source *temporal* knowledge-graph memory engine (powers Zep). Facts
  carry validity intervals ("valid from X until contradicted"), which suits a
  journal where goals and blockers evolve. Supports Neo4j/FalkorDB backends and
  can use Ollama-served models.
- **Mem0** (<https://vectorize.io/articles/mem0-vs-zep>) — vector store +
  optional graph; lighter-weight, faster, cheaper; benchmarks put Zep/Graphiti
  ahead on long-horizon recall (LongMemEval 63.8% vs 49.0% on GPT-4o) but the
  efficiency gap favors Mem0.
- Survey of graph-based agent memory:
  <https://github.com/DEEP-PolyU/Awesome-GraphMemory>

**Key caution:** all of these rely on an LLM to do entity/relationship
extraction, and quality degrades with small models. Practical implication for
TheRig: let the local model handle *conversation*, and run the nightly
"compress into the graph" pass either with a carefully-prompted local model or
with the Claude API (a day's journal is small; the cost is cents). Decide per
data-sensitivity — see ARCHITECTURE.md.

## Notifications on iPhone from a home server

Two viable self-hosted-friendly paths (research: <https://docs.ntfy.sh/subscribe/pwa/>,
<https://noted.lol/ntfy/>):

1. **Standard Web Push to an installed PWA.** iOS has supported web push for
   home-screen PWAs since 16.4; iOS 26 is fine. The server sends outbound to
   Apple's push endpoint — no inbound ports opened on TheRig. Requires the PWA
   be served over HTTPS with a valid cert.
2. **ntfy** — dead-simple self-hosted pub/sub with an iOS app. Gotcha: the
   native iOS app needs the upstream ntfy.sh relay to wake the phone for
   self-hosted servers (message IDs transit ntfy.sh), or you use ntfy's own PWA
   which is just web push again.

Conclusion: since the client is a PWA anyway, **native Web Push from our own
backend is the clean end-state**; ntfy is a fine day-one shortcut for testing
schedules before the PWA exists.
