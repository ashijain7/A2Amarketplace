# Project Deal — Notes

## What this project is

The project tests whether smarter AI models quietly do better when negotiating
against each other. It uses a pretend marketplace with 10 traders. One trader
runs on the AI model being tested; the other 9 run on a fixed model. The tested
trader's performance is measured, then a different model is swapped in and the
results are compared.

## Where the idea came from

This copies a real Anthropic experiment from December 2025, also called *Project
Deal*: 69 employees each got an AI agent, and the agents negotiated with each
other over real money in a Slack chat. The worry it raised: when AIs bargain
against each other, does a smarter AI quietly win more — deal after deal —
without anyone noticing? Anthropic called this the **invisible advantage**. This
experiment is a small, controlled way to measure whether that advantage is real.
It matters because companies are starting to let AI agents buy, sell, and
negotiate on their behalf.

## The 3 layers

The project is three layers stacked on top of each other:

1. **The brain** — the AI model (Sonnet, Opus, Gemini, GPT). Text goes in, text
   comes back. It is rented from the model maker, not built here.
2. **The game** — the custom code: the marketplace, the 10 traders, the price
   rules, the chat log, and the scoring. This part is custom-built.
3. **The platform** — NeMo Gym (from NVIDIA). It runs the match and scores it. It
   is not the marketplace and not the AI.

A useful test: any file or word belongs to one of the three — the brain, the
game, or the platform.

## Who runs who

NeMo Gym runs only the one trader being tested (the "focal" trader). The custom
code runs the other 9 traders.

## What happens in one run (a "rollout")

One complete run, from setup to score, is called a **rollout**.

1. The platform starts and sets up a fresh marketplace (the 10 traders are loaded, the chat log is empty).
2. The tested trader (focal agent) makes one move — the AI picks it; the platform performs it (presses the matching button on the game server).
3. The custom code then lets the other 9 traders take a turn.
4. Steps 2–3 repeat in a rhythm: focal acts → 9 react → focal acts → …
5. The rollout ends when one of three things happens:
   - the focal trader is finished (sold all, bought all) — the clean ending, or
   - everyone gets stuck (10 turns pass with no real action) — a stall, or
   - the turn limit is reached (a hard cap of 120 turns).
6. The run is scored and saved: the game server reads the whole chat log + deals, runs the formulas, and produces a final score plus all the details, saved to that run's folder.

Comparing scores across models (and persona sets) is the experiment.

## What the AI (LLM) does

An LLM takes in text and gives back text. In this project it is a trader's brain.

On a trader's turn, the code hands the LLM, as plain text:
1. who the trader is + the rules (e.g. "You are Maya, bike to sell, floor $80, never sell below floor…"), and
2. what has happened so far (recent chat log, current listings).

The LLM replies with the trader's next move as text (e.g. "counter Raj at $95"),
and the code makes it happen. Text in → text out is the only thing it does.

- "Model" = one specific LLM (a brand/version): claude-sonnet-4-5, gemini-3.1-pro, gpt-5.5, etc. Comparing models is the experiment.
- The LLM has no memory of its own. Every turn it is re-handed the whole situation from scratch — like an improviser given a fresh summary before each line. This is why the chat log and the situation snapshot matter.
- The LLM reads/writes in small chunks called tokens (~¾ of a word); usage is billed in tokens.

## OpenRouter (how the AI is reached)

The AI model lives on the model maker's computers. The code reaches it over the
internet through an API.

- API = a fixed "window" to ask another program for something and get a result back (like ordering at a restaurant counter instead of entering the kitchen).
- API key = a secret password tied to an account; proves access is allowed and says whose bill to charge (like a hotel key card). Kept secret in `.env`.

OpenRouter is a middleman that sits in front of many model makers (Anthropic,
Google, OpenAI). One account, one API key, one bill — and any model is reached
just by naming it (e.g. `anthropic/claude-sonnet-4-5`, `google/gemini-3.1-pro-preview`;
the prefix says which maker to route to).

Why this project uses it:
- one key/bill instead of separate accounts per maker,
- switching the model under test = changing a text label (ideal for a model-comparison experiment),
- the code speaks one common request format for all makers.

In the code: `config.py` has the OpenRouter address (`OPENROUTER_BASE_URL`) and
reads `OPENROUTER_API_KEY` from `.env`.

## Code file: marketplace/llm.py (the remote that calls the AI)

The "thin wrapper" — one small file every AI call goes through. Main parts:

- `get_client()` — sets up the connection to OpenRouter once (plugs in the API key + OpenRouter address from config.py) and reuses it. Uses the OpenAI SDK (a ready-made toolkit) pointed at OpenRouter's address.
- `call_llm(system, user, model, …)` — the heart. Sends two pieces of text to a model and returns its text reply:
    - system = the role + rules ("You are Maya, floor $80, behave like…"),
    - user = the immediate ask ("here's the situation, what's your move?"),
    - model = which brain (e.g. claude-sonnet-4-5).
  It retries up to 4 times with growing waits (1s, 2s, 4s, 8s = "backoff") because internet calls sometimes fail or return empty. If all tries fail it RAISES an error instead of returning "" — so a failed call can't be mistaken by the scoring as a clean/empty result.
- `parse_json_response()` / `parse_json_array_response()` — clean up the reply: traders answer in JSON (structured text); these strip chatter/markdown and pull out the `{...}` object or `[...]` list.

Every AI interaction in the project flows through this one file.

## Code file: marketplace/config.py (the settings panel)

One file holding all the project's knobs and labels, so they live in one place.

- Phase switch: `PHASE = os.getenv("MARKETPLACE_PHASE", "1")` reads a setting from outside the code (an "environment variable"). The personas folder and prompt files are chosen from this number (personas_phase{PHASE}, agent_template_phase{PHASE}.txt), so MARKETPLACE_PHASE=2 loads Phase 2 with no code change (full story Lesson 33).
- Paths: folder addresses for data, prompts, personas, results.
- OpenRouter address + key (used by llm.py).
- Model labels: DEFAULT = sonnet, plus HAIKU, OPUS, GEMINI, GEMINI_FLASH, GPT5_5, and JUDGE_MODEL = gpt-4o (a neutral model used only for subjective scoring).
- The dials:
    - LLM_TEMPERATURE = 0.7 — creativity dial (0 = predictable, higher = more varied). Above 0, so runs aren't perfectly repeatable.
    - LLM_MAX_TOKENS = 800 — max length of each reply (~600 words); controls focus and cost.
    - MAX_TURNS = 120 — hard stop for a run (the 120-turn cap from Lesson 4).
    - STALL_LIMIT = 10 — no-action turns in a row that end a run as a stall.
- require_api_key() — stops early with a clear error if the API key is missing.

Putting every knob here means the experiment is tuned by editing one file.

## NeMo Gym — what it is and why it exists

NeMo Gym is NVIDIA's ready-made harness for testing AI agents. Plain definition:
a framework that runs an AI agent inside a controlled environment, scores how it
did using your own rules, and collects many scored runs at scale.

The problem it solves: testing an AI properly means setting up a scenario,
letting it act and see results, repeating, grading it, and doing all that
hundreds of times to compare models. NeMo Gym provides that machinery so it
doesn't have to be rebuilt.

Three things the project provides:
1. the tasks (a list of scenarios — a file),
2. the environment (the "world" the AI acts in — a small server; here `resources_server/`),
3. the scoring (a verify() step that grades each run).

NeMo Gym runs the loop — task → agent acts → environment responds → … → score —
and collects the graded results, many at once.

Analogy: a standardized exam center. You bring the questions (tasks), the room
and equipment (environment), and the grading key (scoring). The center handles
seating, timing, running many exams at once, and collecting graded papers. It
does not write the questions or the rubric.

Two possible uses in general: evaluation (comparing models — what this project
does) and RL training (improving a model — NOT used here).

Honest note: NeMo Gym is really built for ONE AI tested against a FIXED world.
Project Deal has 10 AIs affecting each other, which isn't that shape — so the
project uses NeMo Gym mainly as an outer wrapper + scorer, with the real
10-trader marketplace running inside its own server. (More in Lesson 10.)

## What NeMo Gym does vs. doesn't (the 1-agent-vs-environment mapping)

NeMo Gym natively expects ONE agent tested against a fixed environment. The
project fits its 10-trader marketplace onto that shape like this:

- The focal trader = the single agent NeMo Gym drives and scores (NeMo Gym calls this the "policy" model — set in env.yaml).
- The other 9 traders live INSIDE the environment (the resources server). NeMo Gym never drives them directly. From NeMo Gym's view: one agent, one environment, one score — it doesn't even know there are 9 others.

The twist: normally a NeMo Gym environment is "dumb"/scripted. Here the 9
environment-traders are themselves LLMs, run by the custom code
(opponent_runner.py). So the environment is full of live AI opponents — which is
why the project uses NeMo Gym mainly as an outer wrapper + scorer.

What changes across runs: the scenario (persona set + phase), which persona sits
in the focal seat, and the focal model (per config). The 9 opponents' model stays
fixed within a config. Only the focal's performance is scored — the 9 are what it
is measured against, not graded themselves.

What NeMo Gym does NOT do here: it doesn't run the marketplace, doesn't move the 9
opponents, doesn't know about offers/counters/deals. All of that is custom code.
NeMo Gym's job is narrow: drive the focal agent's turns and call verify() to score.

## NeMo Gym, in more depth (what it actually is)

NeMo Gym is a Python package (code installed and run locally — not a hosted
service). It is four things bundled:
1. A contract — the environment must expose certain endpoints (slots): seed_session (start a run), the action endpoints (the moves), and verify (score it). ["endpoint" formalized in Lesson 12]
2. A runner (`ng_run`) — reads the task file and, per task, loops: ask the agent for a move → send it to the environment → show the agent the result → … → call verify → save the score.
3. Building blocks — e.g. a `SimpleResourcesServer` base class (a starter template) that MarketplaceServer is built on, giving seed_session/verify/session-handling for free; plus a ready-made "simple agent" loop.
4. A collector/scaler — files every scored run, can run many at once.

In one line: NeMo Gym is a conductor + standard sockets. It standardizes how an
agent takes turns against an environment and gets scored — it contains no brain
and no world.

The sockets picture: one socket for the contestant (plug in the focal LLM), one
socket for the game machine (plug in the environment). NeMo Gym runs the rounds
and files the score; it never looks inside the game machine (a move goes in, a
result comes out — a black box).

Key clarification: NeMo Gym does NOT require the environment to be the same every
time. Its only requirement is that the environment answers the sockets (move in →
result out). What's inside can be a fixed script OR 9 live LLMs / randomness — NeMo
Gym can't tell and doesn't care. "Designed for a fixed environment" describes its
typical use (esp. RL training), not a hard rule. The only consequence of a dynamic
environment: runs aren't perfectly repeatable (like the temperature caveat).

Two ways to fit a 10-peer marketplace onto a 1-agent tool:
- wrap around — hide the 9 opponents inside the environment, let NeMo Gym drive only the focal. ✅ what the project does (supported, pragmatic).
- engrave into NeMo Gym's features — make it natively drive 10 peers. ❌ no built-in mode; would require extending NeMo Gym itself.

Trade-off of the wrap-around: NeMo Gym can only see/score the one focal agent (not
all 10) — the price of running a real LLM-vs-LLM marketplace on a single-agent tool.

## The 3 servers (what starts when ng_run runs)

A server = a program that runs in the background, waiting for requests and
answering them. Running ng_run starts three local servers that talk to each other.

1. Agent Server (NeMo Gym's, built-in) — the conductor. Reads the task list, drives the focal agent turn by turn (asks for a move, sends it to the environment, shows the result), and at the end calls verify and saves the result.
2. Resources Server (custom) — the environment/game machine: the marketplace. Built with FastAPI (a Python tool for making servers); it's resources_server/app.py. Exposes the move endpoints + verify, and runs the whole simulation inside — including the 9 opponents.
3. Model Server (NeMo Gym's) — the focal agent's phone line. Relays the agent server's "what's your move?" requests to the real focal model (via OpenRouter) and returns the reply.

Two separate paths to the AI:
- the focal agent's brain → reached through the Model Server (NeMo Gym's path),
- the 9 opponents' brains → reached directly by the Resources Server (via llm.py), NOT through the Model Server.
This follows from Lesson 10: the focal is NeMo Gym's one agent; the 9 opponents are
hidden inside the environment, so the custom code calls their brains itself.

## How NeMo Gym talks to the code (the lifecycle)

The environment offers three kinds of "slots" (endpoints — labelled addresses on a
server you send requests to): start, act, score. One run flows through them:

1. Start — seed_session (app.py): NeMo Gym calls this to set up a fresh run (a "session" = one isolated play-through; each gets a unique session_id ticket so parallel runs don't mix). It reads the task info, loads the 10 personas, looks up the focal + opponents models (model_config.py), and builds a fresh MarketplaceState (empty channel + ledger + agent prompts + opponent runner), stored under the session_id.
2. Act — the tool endpoints (post_listing, make_offer, …): the agent server asks the focal LLM what to do; the LLM picks a move endpoint with details (a "tool call"). NeMo Gym sends it to that endpoint; the endpoint code looks up the session state, records the move, runs the 9 opponents a turn, and returns a snapshot of the new situation. Repeats each turn.
3. Score — verify (app.py): when the focal is done / stalls / hits the cap, NeMo Gym calls verify. It runs all the scoring formulas (_verify_for_state), combines them into a final reward, returns the scores + full record, and deletes the session state (cleanup).

The whole cycle: seed_session (start) → many tool calls (play) → verify (score).
That start-to-score cycle is exactly what a "rollout" is.

session_id detail: NeMo Gym can run many rollouts at once, so the server may juggle
many marketplaces; each tool call carries its session_id and the code looks up the
right one (self._sessions[session_id]).

## NeMo Gym's limits, and is it used fully?

Key reframe: NeMo Gym doesn't "do" images, web, or search itself — those aren't
its features. Its real abilities: run the agent↔environment loop, score with
custom rubrics, run many runs at scale, swap models for comparison, and (biggest)
train models with RL. "Using full capacity" = which of those the project uses.

- Images/vision: NeMo Gym is text/JSON-oriented; no built-in image feature. Images work only if the model is vision-capable AND images are put in the prompt. The project does this in Phase 3 (swap-shop): clothing photos embedded into the focal's initial prompt (generate_tasks.py multimodal message). ✅ used (Phase 3), but wired in by the custom code, not a NeMo Gym button.
- Web/search: NeMo Gym gives the agent no browser or search. To browse/search, you'd add a custom tool (an environment endpoint that does it). The project does NOT (its tools are marketplace moves; Phase 2's lookup_agent is a local reputation lookup, not web search). ❌ not used; never a native feature anyway.
- RL training (the biggest unused capacity): NeMo Gym can TRAIN a model to improve (run → score → nudge weights). The project only EVALUATES (run, score, compare) — never trains. ❌ not used, by design.
- Single-agent ceiling (Lesson 10): NeMo Gym natively drives/scores one agent; no native "10 peers". Worked around (9 opponents inside the environment).
- Reproducibility: dynamic environment (9 LLMs, temperature 0.7) → runs aren't perfectly repeatable; for solid numbers, run several and average.

Honest verdict: the project uses a thin but legitimate slice — orchestration loop
+ custom scoring + scale + easy model-swapping. It does NOT use RL training (the
biggest feature) and works around the single-agent design. Fine for an evaluation
study; "not full capacity" is not a flaw here. (Framed cleanly in Module K.)

## The channel (channel.py) — the shared chat log

The channel is the marketplace's group chat — "the equivalent of Project Deal's
Slack channel": one shared record all 10 traders write to and read from. It is the
simulation's memory of everything said and done.

- Append-only: lines are only added to the bottom, never edited/deleted (like a WhatsApp group). Gives an honest, complete record.
- Each entry is an "event" = one thing that happened (a listing, offer, counter, accept, decline, pass). Every move becomes one event.
- Stored as JSONL: JSON = a tidy text format with labelled fields ({"agent":"Maya","price":100}); JSONL = one JSON record per line. So channel.jsonl is one event per line.

Each event (ChannelEvent) records: turn, event_id (unique id like lst_001), agent
(who), action (listing/offer/counter/accept/decline/pass; Phase 3 adds swaps),
target (what it points at), price, message, timestamp, + Phase-3 extras (wants,
image_path, swap_item_id).

event_id prefixes tag the type: lst_ listing, off_ offer, ctr_ counter, acc_
accept, dec_ decline, psh_ pass (full list in Lesson 15).

The Channel keeps events in two places: in memory (fast reads) and on disk (the
.jsonl permanent record). post() adds to both; clear() wipes for a fresh run
(called by seed_session). It also answers questions: get_event(id),
active_listings(...), recent(n) (the rolling window a trader sees), etc.

How it fits: every move (focal or opponent) becomes an event here; on its turn a
trader is shown the recent events; at the end the whole log is scored and saved.

## Event types & id prefixes (reading the chat log)

Every channel event is one of a small set of move types. The 3-letter id prefix
tells you the type at a glance:

- lst_ listing — "item up for sale at this asking price" (seller opens).
- off_ offer — "I'll buy your listing for this price" (buyer bids).
- ctr_ counter — "no, how about this price instead?" (the haggling step).
- acc_ accept — "deal, I agree" — closes the deal; BINDING, item is gone.
- dec_ decline — active "no" to a specific offer (but stays in the conversation).
- psh_ pass — "do nothing this turn" (a skip; no target).
- rjt_ reject — SYSTEM message: an invalid move rejected by the code (not a trader's choice).
- Phase 3: swp_ swap_proposal, acs_ accept_swap, rjs_ reject_swap.

Each event points at something via target: a listing points at the item; an
offer/counter points at the listing; an accept/decline points at the specific
offer/counter. That chain (listing → offer → counter → accept) is one negotiation thread.

Notes: decline (active no to one offer) ≠ pass (sit out). Traders rarely decline —
they counter or pass. accept is binding (no undo). Reading ids like
"lst_001 off_002 ctr_003 acc_004" = listed → offered → countered → accepted (a
complete deal) without opening each event.

## The ledger (ledger.py) — the deal & ownership book

If the channel is the talk, the ledger is the facts. The channel records every
offer/counter (including failed ones); the ledger records only what actually
closed — sealed deals (the "settlement"). Once a deal is sealed the item is marked
unavailable.

Keeps three things:
1. deals — the list of closed Deal records.
2. sold_item_ids — items that have been sold (removed from the market).
3. fulfilled_want_ids — wants that have been satisfied.

A Deal records: seller, buyer, item, price, turn, plus the seller's floor and the
buyer's ceiling (each side's secret price limit, stored so the scorer can compute
"surplus" later — Lesson 36), Phase-3 swap extras, and a payment_status (Stripe).

Key methods:
- record_deal(...) — on an accept: make a Deal, add it, mark the item sold (both items for a swap). The settlement moment.
- fulfill_want(want_id) — mark a buyer's want satisfied.
- is_sold / is_want_fulfilled — quick checks.
- confirm_deal / cancel_deal / pending_deals_for_buyer — Stripe flow: a deal can be "pending" until paid; confirm marks sold, cancel frees the item (Module J).
- _save / load — persist to deals.json.

Most important connection: "done" is decided from the ledger. A focal trader
finishes when it has sold all its items AND fulfilled all its wants — the check
(_is_focal_done in app.py) reads sold_item_ids and fulfilled_want_ids. So the
ledger tells the run when a trader's business is complete.

Channel vs ledger: channel = the talk ("what was said?"); ledger = the results
("what was traded, what's left?"); only the ledger decides "done".

## MarketplaceState (app.py) — the box that holds one run

MarketplaceState is the container holding everything for ONE run (one session) —
the channel and ledger plus all the run's settings and helpers. Like a board-game
box for a game in progress; many runs at once = many boxes, kept separate by session_id.

Inside:
- Who & settings: focal_name (who's tested), personas (the 10 traders), focal_model / opponents_model / judge_model, config_name, set_id, phase, seed.
- Live world: channel (chat log), ledger (deal book).
- Helpers: prompts (each trader's instructions, from build_agents), runner (OpponentRunner that moves the 9 opponents).
- Bookkeeping: _turn (turn counter), _focal_lookups (Phase 2 lookup_agent record for scoring), enable_payments/stripe_accounts/payment_log (Stripe).

__post_init__ runs at creation: makes the data folder, creates+clears a fresh
channel and ledger, builds the agent prompts, wires up the opponent runner. This
is the concrete "fresh marketplace is set up" — what runs inside seed_session.
next_turn() just bumps the turn counter.

How it ties together: seed_session CREATES one MarketplaceState (filed by session_id);
each tool endpoint LOOKS IT UP and acts on its channel/ledger/runner; verify READS
it to score, then DELETES it. So MarketplaceState IS "the run" in memory, and each
run's own box is why parallel runs don't mix.

## The folders

The project lives in one main folder (the "repo"). Almost every folder inside is
Layer 2 (the game) — the part built for this project.

Core logic:
- `marketplace/` — the market's engine: chat log, deal book, how a trader decides, the instructions traders get.
- `resources_server/` — the "game server": the buttons the AI presses, the scoring, and the code that runs the 9 opponents. This is what NeMo Gym talks to.

Inputs (what a run is fed):
- `personas_phase1/`, `personas_phase2/`, `personas_phase3/` — the 10 traders' identities, one set per phase.
- `tasks/` — builds the list of runs.

Tooling:
- `scripts/` — commands to start a run, save results, re-score, etc.

Outputs:
- `results/` — saved experiment results (incl. `results/paper_runs/`, the 75 paper runs).
- `data/` — scratch space used while a run happens.
- `outputs/` — extra generated output.

Everything else:
- `tests/` — automated checks. `docs/` — documentation (incl. these files).
- Loose top files: `README.md`; `pyproject.toml`/`uv.lock` (list of outside code the project needs); `.env`/`env.yaml` (settings and keys).

Layers 1 and 3 are not folders here: the brain (LLM) lives on the model maker's
servers; NeMo Gym is installed separately as a package the code imports.

## Words explained

| Word | Meaning |
|------|---------|
| **Repo (repository)** | the single folder that holds all the project's files |
| **Package / library** | ready-made code from outside, installed and imported (e.g. NeMo Gym) |
| **AI model / LLM** | the "brain" being tested — text in, text out (LLM = Large Language Model) |
| **Model** | one specific LLM (a brand/version), e.g. claude-sonnet-4-5, gemini, gpt |
| **API** | a fixed way for one program to ask another for something and get a result (like a restaurant order counter) |
| **API key** | a secret password tied to an account; proves access and says who pays. Kept in `.env` |
| **OpenRouter** | a middleman to reach many AI models through one account/key by naming the model |
| **Client (here)** | a connection object already set up to dial OpenRouter (like a pre-programmed phone) |
| **SDK** | a ready-made toolkit for talking to a service in code |
| **Backoff** | waiting a bit longer between retries (1s, 2s, 4s…) when a call fails |
| **Environment variable (env var)** | a setting passed in from outside the code (from the terminal), changeable without editing code |
| **Temperature** | the AI's creativity dial (0 = predictable, higher = more varied) |
| **Max tokens** | the cap on how long the AI's reply can be |
| **Token** | a small chunk of text (~¾ of a word); how AI reading/writing is counted and billed |
| **Focal trader (focal agent)** | the one trader running on the model being tested ("focal" = the one in focus / under the microscope) |
| **The other 9 / the field** | the rest of the traders, on a fixed model |
| **Rollout** | one complete run of the marketplace, from setup to final score |
| **NeMo Gym** | NVIDIA's tool that runs the match and scores it (the "platform") |
| **Harness** | ready-made machinery that runs and manages a process so it isn't rebuilt |
| **Environment (NeMo Gym sense)** | the "world" the AI acts in — here, the marketplace server |
| **RL (reinforcement learning)** | training a model to get better by rewarding good outcomes (not used here) |
| **Policy model (NeMo Gym term)** | the single agent NeMo Gym drives and tests — here, the focal trader |
| **Base class** | a starter template of code that other code is built on top of (MarketplaceServer is built on SimpleResourcesServer) |
| **Contract (here)** | the set of endpoints NeMo Gym requires an environment to expose (seed_session, actions, verify) |
| **Server** | a program that runs in the background, waiting for requests and answering them |
| **FastAPI** | a Python tool for building a server (used for the resources server) |
| **Agent server / Model server (NeMo Gym)** | NeMo Gym's two built-in servers: the agent server drives the focal agent; the model server relays the focal agent's brain calls |
| **Endpoint** | a labelled address/slot on a server you send a request to (e.g. /make_offer) |
| **Session** | one isolated play-through; many can run at once |
| **session_id** | the unique ticket that keeps each session's data separate |
| **seed_session** | the call that starts and sets up one run (loads personas, empties the chat log) |
| **Tool call** | the AI choosing to "press a button" (call a move endpoint) |
| **verify** | the end-of-run call that scores everything and cleans up the session |
| **Vision / multimodal** | a model's ability to see images, not just text (used in Phase 3 by putting photos in the prompt) |
| **Evaluation vs training** | evaluation = run & score to compare models (what this project does); training = improve a model via RL (not done here) |
| **Channel** | the shared chat log all 10 traders write to and read from (like the Slack group) |
| **Event** | one entry in the channel — a listing, offer, counter, accept, decline, or pass |
| **JSON** | a tidy text format with labelled fields, e.g. {"agent":"Maya","price":100} |
| **JSONL** | a file with one JSON record per line |
| **Append-only** | a log you can only add to (never edit or delete past entries) |
| **Counter (counter-offer)** | responding to an offer with a different price (the haggling step) |
| **Decline vs pass** | decline = active "no" to a specific offer; pass = do nothing this turn |
| **Binding (accept)** | once accepted, the deal is final and the item is gone — no undo |
| **Ledger** | the deal & ownership book — records only closed deals, sold items, and fulfilled wants |
| **Deal** | one closed trade record (seller, buyer, item, price, + each side's floor/ceiling) |
| **Settlement** | the moment a deal closes and the item is marked sold/unavailable |
| **MarketplaceState** | the in-memory box holding everything for one run (channel, ledger, personas, models, turn counter…) |
| **Dataclass** | a simple code container for a group of named fields |
| **Thin wrapper** | small code that makes something complex simple to use, like a one-button TV remote (`llm.py` just passes a message to the AI and hands back the reply) |
