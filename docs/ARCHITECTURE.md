# How This Project Works

---

## What is this?

This is a simulation of a marketplace where AI agents buy and sell things from each other — completely on their own, no humans involved.

It is based on a real experiment Anthropic ran in December 2025 called **Project Deal**. In that experiment, 69 Anthropic employees each got a $100 budget. An AI interviewed each person for 10 minutes to learn what they wanted to buy and sell. Then a personal AI agent was built for each person. All 69 agents were dropped into a Slack channel and left alone to negotiate. Whatever deals the agents agreed to were real and binding — money actually changed hands.

This project replicates that entire experiment locally, with fewer people (10 instead of 69) and fictional characters instead of real employees.

---

## The Simple Version

Think of it like a school flea market:

- 10 students each bring stuff to sell and a shopping list of things they want to buy
- They're all in the same room shouting offers at each other
- When two students agree on a price, the deal is done

In this project:
- The "students" are AI agents (one per fictional person)
- The "room" is a log file everyone reads and writes to
- The "shouting" is JSON messages the agents post to that log
- The "agreement" is when one agent accepts another's offer

Nobody controls the agents during the run. They make every decision themselves.

---

## Step by Step — What Happens When You Run It

### Step 1 — Create the people

Before the marketplace opens, the system needs characters to populate it. It asks an AI to invent 10 fictional people. Each person has:

- **Things to sell** — with a floor price (the minimum they'll accept)
- **Things to buy** — with a ceiling price (the maximum they'll pay)
- **A personality** — terse, friendly, aggressive, playful, etc.

Example of one person:

```json
{
  "name": "Dexter",
  "items_to_sell": [
    { "item_id": "camera_01", "name": "Canon point-and-shoot camera", "floor_price": 45 }
  ],
  "items_to_buy": [
    { "want_id": "headphones_w1", "description": "Wireless headphones", "ceiling_price": 50 }
  ],
  "style": "Terse and direct. Gets straight to numbers."
}
```

Dexter will never sell his camera below $45. He will never pay more than $50 for headphones.

These 10 people are saved to a file called `personas.json`. They are reused every run unless you ask for new ones.

**File that does this:** `interview.py`

---

### Step 2 — Build each agent

Now the system turns each person into an AI agent. It does this by filling in a template:

> "You are an AI representing Dexter. He is selling a camera with a floor price of $45. He wants to buy headphones for at most $50. His style is terse and direct. Here are the marketplace rules. Here is the exact JSON format you must reply in."

This template becomes the agent's **system prompt** — its identity and instructions. Every time the AI is called to act as Dexter, it receives this prompt.

All 10 agents use the same underlying AI model. The only difference between them is their system prompt — their identity, inventory, and personality.

**File that does this:** `build_agents.py`

---

### Step 3 — Open the marketplace (the channel)

There is one shared log file: `data/channel.jsonl`. This is the marketplace. Every single action any agent takes gets written as one line to this file — permanently, in order, forever. Nothing is ever deleted or changed.

This mirrors Project Deal's Slack channel. Every message anyone posted is still there, in order.

Example of what the channel looks like after a few turns:

```
{"turn": 5,  "event_id": "lst_005", "agent": "Dexter",  "action": "listing", "price": 65,  "message": "Canon camera, works perfectly. $65."}
{"turn": 7,  "event_id": "off_007", "agent": "Mika",    "action": "offer",   "price": 55,  "message": "Hey Dexter! Would you take $55?"}
{"turn": 14, "event_id": "ctr_014", "agent": "Mika",    "action": "counter", "price": 60,  "message": "How about we meet in the middle at $60?"}
{"turn": 16, "event_id": "acc_016", "agent": "Dexter",  "action": "accept",  "price": 60,  "message": "Mika — $60 works. Camera's yours."}
```

Each event has a unique ID. The ID prefix tells you what type it is:

| Prefix | Meaning |
|--------|---------|
| `lst_` | listing — someone is selling something |
| `off_` | offer — someone wants to buy |
| `ctr_` | counter — a new price proposed |
| `acc_` | accept — deal sealed |
| `dec_` | decline — offer rejected |
| `rjt_` | reject — invalid action attempted |
| `psh_` | pass — agent did nothing |

**File that does this:** `channel.py`

---

### Step 4 — Run the marketplace (the main loop)

The scheduler runs the marketplace. It works in rounds:

1. Shuffle the list of active agents (agents who still have something to buy or sell)
2. Give each one a turn, in that shuffled order
3. Reshuffle and repeat

An agent is "done" when it has sold everything it wanted to sell AND bought everything it wanted to buy. Done agents drop out of the rotation.

The run stops when:
- All agents are done, OR
- The turn limit is reached (120 turns), OR
- Nothing productive has happened for 10 turns in a row (stalled)

**File that does this:** `scheduler.py`

---

### Step 5 — Each agent's turn

When it's Dexter's turn, the system builds a summary of what's happening in the marketplace and sends it to the AI as a message. It looks like this:

```
You are Dexter. It is now your turn.

=== YOUR ITEMS TO SELL ===
Currently listed:
  - listing lst_005: camera_01 asking $65
    offers: Mika $55 (off_007)

=== YOUR WANTS ===
  - headphones_w1: Wireless headphones (ceiling $50)

=== ACTIVE LISTINGS FROM OTHER AGENTS ===
  - lst_017 from Mika: 'Sony wireless headphones...' asking $48

=== DEALS ALREADY CLOSED ===
  - Rosa sold 'Yoga mat' to Yuki for $22

=== FULL CHANNEL HISTORY ===
  [turn 5]  Dexter (listing): Canon camera, works perfectly. $65.
  [turn 7]  Mika (offer):     Hey Dexter! Would you take $55?
  [turn 9]  Rosa (listing):   Thick yoga mat, barely used. $20.
  ...

Decide your single action and respond with JSON only.
```

The AI reads this, decides what to do, and replies with a single JSON object:

```json
{
  "action": "counter",
  "target": "lst_005",
  "price": 62,
  "message": "Mika — best I can do is $62."
}
```

The scheduler reads this response, checks if it's valid, and either posts it to the channel or rejects it with a `rjt_` event explaining why.

**File that does this:** `agent.py`

---

### Step 6 — Deals close (the ledger)

When an agent accepts an offer, the scheduler seals the deal:

- The item is marked as sold — nobody can list or offer on it again
- The want is marked as fulfilled — the buyer stops looking for that item
- The deal is recorded in `data/deals.json` with: who sold, who bought, what item, final price, seller's floor, buyer's ceiling, and which turn it happened on

Example deal record:

```json
{
  "deal_id": "deal_001",
  "seller": "Dexter",
  "buyer": "Mika",
  "item_id": "camera_01",
  "item_name": "Canon point-and-shoot camera",
  "price": 60.0,
  "seller_floor": 45,
  "buyer_ceiling": 65,
  "turn": 16
}
```

Dexter got $60 — that's $15 above his minimum. Mika paid $60 — that's $5 below her maximum. Both respected their limits.

**File that does this:** `ledger.py`

---

### Step 7 — Read the results (analysis)

After the run, the analyzer reads the channel and deals files and prints a summary:

- How many listings, offers, counters, accepts, declines, and rejections happened
- For each deal: price, how much the seller extracted above their floor, how much the buyer saved below their ceiling
- For each agent: what they sold, what they bought, what they failed to sell or buy
- A constraint check: did any deal violate a floor or ceiling?

**File that does this:** `analyze.py`

---

## The 6 Actions — Simply Explained

| Action | What it means | Example |
|--------|--------------|---------|
| **listing** | "I'm selling this item for $X" | Dexter posts his camera at $65 |
| **offer** | "I want to buy that item for $X" | Mika offers $55 on Dexter's camera |
| **counter** | "Not at that price — how about $X?" | Mika counters at $60 |
| **accept** | "Deal — I agree to $X" | Dexter accepts Mika's $60 counter |
| **decline** | "No. Not at that price or lower." | Dexter declines a $40 offer — the other agent cannot come back with $40 or less |
| **pass** | "I'll wait this turn" | Agent has nothing useful to do right now |

---

## Every Action and Event — What Each One Actually Does

There are 6 things an agent can do (actions) and 2 things the system does in response (events). Here is what each one means, what triggers it, and what changes as a result.

---

### LISTING — "I am selling this item"

The agent posts one of its own items for sale with an asking price.

```
Turn 5: Dexter → LISTING camera_01 at $65
        "Canon camera, works perfectly. $65."
```

- The asking price must be at or above the agent's floor price. If not, the action is rejected.
- The item can only be listed once. A second listing of the same item is rejected.
- Once listed, the item appears in every other agent's context under "ACTIVE LISTINGS FROM OTHER AGENTS."
- Nothing is sold yet. The listing is just an invitation to negotiate.

**What changes:** A `lst_` event appears in the channel. All agents can see the listing on their next turn.

---

### OFFER — "I want to buy that item for $X"

The agent bids on another agent's listing. It references the listing by its event ID.

```
Turn 7: Mika → OFFER $55 on lst_005
        "Hey Dexter! Would you take $55?"
```

- You can only offer on active listings (item not yet sold, listing exists).
- You cannot offer on your own listing.
- If you previously had an offer declined on this listing, you cannot come back with the same price or lower — only higher.
- The offer is not binding. The seller can ignore it, counter it, or accept it.

**What changes:** An `off_` event appears in the channel. The seller sees the offer under their listing on their next turn.

---

### COUNTER — "Not at that price — how about $X?"

Either the seller or the buyer proposes a new price on an existing negotiation thread. The counter always references the original listing ID, not the offer ID.

```
Turn 14: Mika → COUNTER $60 on lst_005
         "How about we meet in the middle at $60?"

Turn 15: Dexter → COUNTER $63 on lst_005
         "Best I can do is $63."
```

- Both sides can counter. The seller can counter down from their asking price; the buyer can counter up from their offer.
- A counter does not close anything. It is just a new price on the table.
- Only participants in a negotiation can counter (the seller, or someone who has already made an offer on that listing).

**What changes:** A `ctr_` event appears in the channel. Both parties see it on their next turn.

---

### ACCEPT — "I agree to this price" (agent action)

The agent agrees to a specific price. This is the agent's message only — it does not by itself close the deal. The scheduler must validate it first (see SEAL below).

There are three different situations and each needs a different event ID as the target:

**Case 1 — Seller accepting a buyer's offer or counter:**
Target = the offer or counter event ID (`off_007` or `ctr_014`)
```
Dexter → ACCEPT off_007 at $55
"Mika, $55 works. Camera's yours."
```

**Case 2 — Buyer accepting a seller's counter back to them:**
Target = the seller's counter event ID (`ctr_015`)
```
Mika → ACCEPT ctr_015 at $63
"Fine, $63. Deal."
```

**Case 3 — Buyer buying at the original asking price:**
Target = the listing event ID (`lst_005`)
```
Mika → ACCEPT lst_005 at $65
"I'll take it at $65."
```

**What changes:** An `acc_` event appears in the channel. Then the scheduler validates it. If valid → SEAL happens. If invalid → REJECT is posted and nothing changes.

---

### SEAL — "The deal is done" (system event, not agent action)

This is what the **scheduler** does after a valid accept. The agent cannot trigger a seal directly — it happens automatically when the scheduler confirms the accept is legitimate.

The scheduler checks:
- Does the target event exist?
- Is the item still unsold?
- Is the price at or above the seller's floor?
- Is the price at or below the buyer's ceiling?

If all checks pass:
- Item is marked as sold in the ledger — no further listings or offers on it are accepted
- Buyer's want is marked as fulfilled — they stop trying to buy that category of item
- Deal is recorded in `deals.json` with price, floor, ceiling, both agents, and turn number

In the run output you see both lines when it works:
```
→ ACCEPT: Mika — $60 works. Camera's yours.
[SEAL] turn 16: Dexter sold 'Camera' to Mika for $60 (floor $45, ceil $65)
```

The `ACCEPT` is the agent's message. The `[SEAL]` confirms the system validated it and state has changed.

**An accept with no seal means the accept was rejected** — wrong ID, item already sold, or price out of range.

---

### DECLINE — "No, and that price is now off the table"

The agent explicitly rejects a specific offer or counter. Unlike pass (which is silent), a decline is visible to everyone in the channel.

```
Turn 9: Dexter → DECLINE off_007
        "Mika, $55 is too low for this camera."
```

The key rule: **once you decline, the other agent cannot re-offer at the same price or lower on that listing.** They can only come back with a higher number. The declined price is permanently blocked.

- Use decline when you want to signal that a price range is closed, not just that you are waiting.
- Use it deliberately — it constrains the other agent's future options.

**What changes:** A `dec_` event appears in the channel. The declined price is recorded. Any future offer from that agent at or below that price on the same listing will be rejected by the scheduler.

---

### PASS — "I'll sit this turn out"

The agent does nothing. No message is posted to the channel that other agents can see. Everyone else just sees a gap in the turns.

```
Turn 11: Rosa → (pass)
```

Pass is always valid. An agent passes when it has nothing useful to do — maybe waiting for a response, maybe its only potential deals are already in progress, maybe the market isn't moving.

**What changes:** A `psh_` event is written to `channel.jsonl` for logging, but it is filtered out of the context window that other agents see. From other agents' perspective, Rosa simply did not act this turn.

Stall detection: if 10 consecutive turns are all passes (or no productive action), the run stops early.

---

### REJECT — "That action was invalid" (system event, not agent action)

This is what the **scheduler** posts when an agent tries to do something the rules don't allow. The agent's original action is discarded. The agent sees the rejection on its next turn and can try again with a corrected action.

```
[reject] Priya turn 21: counter against non-listing 'off_004'
```

Common causes:
- Targeting a wrong event ID (e.g. countering an offer ID instead of the listing ID)
- Trying to list an item already listed or already sold
- Making an offer at or below a previously declined price
- Accepting at a price above the buyer's ceiling or below the seller's floor
- Trying to offer on your own listing

**What changes:** A `rjt_` event is posted to the channel with the reason. The agent's intended action has no effect. The run continues.

---

### Quick Reference

| Name | Who does it | Visible to others | Changes state |
|------|------------|-------------------|---------------|
| listing | Agent | Yes | No — starts negotiation |
| offer | Agent | Yes | No — proposal only |
| counter | Agent | Yes | No — new price proposal |
| accept | Agent | Yes | No — triggers validation |
| **seal** | **Scheduler** | **Yes** | **Yes — item sold, want fulfilled** |
| decline | Agent | Yes | Yes — blocks that price range |
| pass | Agent | No (filtered out) | No |
| **reject** | **Scheduler** | **Yes** | **No — original action discarded** |

---

## A Complete Deal From Start to Finish

Here is the Dexter ↔ Mika camera deal from the first run:

```
Turn 5:  Dexter  → LISTING  camera_01 at $65
                   "Canon camera, works perfectly. $65."
                   Dexter's floor is $45 — $65 is well above it ✓

Turn 7:  Mika    → OFFER    $55 on lst_005
                   "Hey Dexter! Would you take $55?"
                   Mika's ceiling is $65 — $55 is below it ✓

Turn 14: Mika    → COUNTER  $60 on lst_005
                   "How about we meet in the middle at $60?"

Turn 16: Dexter  → ACCEPT   $60 targeting ctr_014
                   "Mika — $60 works. Camera's yours."
                   $60 ≥ Dexter's floor of $45 ✓
                   $60 ≤ Mika's ceiling of $65 ✓

DEAL SEALED:
  Dexter sold camera to Mika for $60
  Dexter extracted $15 above his floor
  Mika saved $5 below her ceiling
```

---

## What Each File Does

```
config.py        Loads the .env file. Defines all paths, model names, and constants.
llm.py           The only place that talks to the AI. Every LLM call goes through here.
interview.py     Asks the AI to invent the fictional people (personas).
build_agents.py  Turns each persona into a system prompt for their agent.
channel.py       The shared log file. Append-only. Every action goes here.
ledger.py        Tracks what has been sold and what wants have been fulfilled.
agent.py         Builds the context each agent sees and parses their response.
scheduler.py     The main loop. Picks agents in rotation, validates actions, seals deals.
analyze.py       Reads the log after a run and prints the summary report.
run.py           The entry point. Wires everything together and runs the whole thing.
```

---

## The Three Data Files

After a run, three files exist in `project_deal_poc/data/`:

**`personas.json`** — The 10 fictional people. Reused across runs unless you regenerate.

**`channel.jsonl`** — Every single event from the marketplace, one line per event. This is the complete transcript of everything that happened.

**`deals.json`** — Every sealed deal with full details: who sold to whom, at what price, what the floor and ceiling were, and which turn it happened on.

---

## The Five Frozen Persona Sets

Instead of generating random personas every run (which makes results non-reproducible), we pre-generated 5 fixed sets of 10 people. All experiments use these. They are stored in `project_deal_poc/personas/`.

**Important:** Every single agent in every set is both a buyer and a seller. Each person comes with at least one item to sell and at least one item they want to buy. There is no separate "buyer role" or "seller role" — everyone is doing both simultaneously, just like a real flea market.

What actually varies between sets is the item count, the price ranges, and whether buyers and sellers can find each other at a price they both agree on.

---

### How the Numbers Are Calculated

Before getting into the sets, here is exactly what each term means and how it is measured.

**Possible deal**
Two agents where one is selling something the other wants to buy, AND the seller's floor price is at or below the buyer's ceiling price. The numbers overlap — a deal is theoretically achievable if they negotiate.

Example: Dexter sells camera at floor $45. Rosa wants a camera and will pay up to $70. Possible — any price between $45 and $70 works for both.

**Impossible deal**
Two agents where the item matches but the prices never can. The seller's floor is higher than the buyer's ceiling. No matter how much they negotiate, no number exists that both sides will accept.

Example: Kai sells keyboard at floor $50. Zoe wants a keyboard but will only pay up to $35. Impossible — Kai won't go below $50, Zoe won't go above $35. The gap never closes.

**Unmatched item (previously called "orphan item")**
An item being sold where no other agent has expressed any interest in buying that type of thing at all — regardless of price. It is not that the price is wrong; it is that nobody in this marketplace wants it. The seller will almost certainly go home with it unsold.

Example: Jax sells a backpack. Nobody in the set has "backpack" on their shopping list. It is an unmatched item — not because the price is off, but because there is simply no demand.

**Unmatched want**
The reverse: an agent wants something that nobody in this set is selling. They will definitely leave empty-handed on that want.

Example: Jax wants "a durable backpack" (ceiling $38). Nobody sells a backpack. Unmatched want.

These numbers are approximate because matching is done by keyword — "blender" matches "blender for smoothies" but "camera" and "vintage Pentax" might not always match even though they should. Treat the counts as directional, not exact.

---

### Set 01 — The Friction Set

**10 agents · 13 items to sell · 15 wants**
Every agent is both a buyer and a seller.

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Maya | Ninja blender, Yoga mat | $35, $15 | Vintage camera | $60 |
| Derek | Polaroid camera | $45 | Blender, Headphones | $50, $45 |
| Priya | Sony WH-1000XM3 headphones | $80 | Bicycle | $95 |
| Buck | Trek mountain bike, Toolbox | $75, $20 | Small grill | $55 |
| Lin | Set of 8 sci-fi paperbacks | $18 | Yoga mat, Teapot | $22, $35 |
| Samir | Weber charcoal grill | $40 | Sci-fi books, Toolbox | $25, $30 |
| Zoe | Cast iron teapot, Dog-sitting | $28, $20 | Mechanical keyboard | $35 |
| Kai | Corsair mechanical keyboard | $50 | Dog-sitting, Bluetooth speaker | $30, $40 |
| Rosa | JBL Flip 5 Bluetooth speaker | $55 | Any working camera | $70 |
| Jax | Complete skateboard | $42 | Headphones, Backpack | $90, $38 |

**Possible deals (~10):** Blender (Maya→Derek), Camera (Derek→Rosa or Maya), Bike (Buck→Priya), Books (Lin→Samir), Grill (Samir→Buck), Yoga mat (Maya→Lin), Teapot (Zoe→Lin), Dog-sitting (Zoe→Kai), Toolbox (Buck→Samir), Headphones (Priya→Jax)

**Impossible deals (2):**
- Keyboard: Kai floor $50 > Zoe ceiling $35 — the only keyboard buyer can't afford the only keyboard seller's minimum
- Speaker: Rosa floor $55 > Kai ceiling $40 — same problem

**Unmatched items:** Jax's skateboard (nobody wants one), Jax's backpack want (nobody sells one)

**Why it's useful:** The only set with built-in price impossibilities. Tests whether agents figure out that some deals are structurally dead and stop wasting turns on them.

---

### Set 02 — The Easy Set (control/upper bound)

**10 agents · 15 items to sell · 15 wants**
Every agent is both a buyer and a seller.

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Mira | Vintage film camera, Succulents | $45, $12 | Road bike | $85 |
| Kai | Road bike | $60 | Vintage camera, Analog watch | $65, $30 |
| Zoe | Box of sci-fi books, Desk lamp | $20, $15 | Indoor plants | $18 |
| Bo | Bluetooth speaker | $28 | Sci-fi books, Over-ear headphones | $25, $35 |
| Iris | Sony headphones, Yoga mat | $22, $18 | Bluetooth speaker | $40 |
| Finn | Nintendo Switch games (3) | $55 | Used laptop, Desk lamp | $95, $20 |
| Luna | HP laptop, Timex watch | $75, $20 | Yoga mat | $25 |
| Rex | Cordless drill | $40 | Switch games, Hand tools | $70, $30 |
| Sage | Cast iron teapot, Wool scarf | $25, $15 | Cordless drill | $50 |
| Dex | North Face backpack | $35 | Teapot, Warm scarf | $35, $20 |

**Possible deals (~10):** Camera (Mira↔Kai swap), Bike (Kai↔Mira swap), Speaker (Bo↔Iris swap), Headphones (Iris↔Bo swap), Laptop (Luna→Finn), Switch games (Finn→Rex), Drill (Rex→Sage), Yoga mat (Iris→Luna), Teapot (Sage→Dex), Desk lamp (Zoe→Finn)

**Impossible deals: 0.** Every matching pair has workable prices.

**Unmatched items:** Succulents (Mira), sci-fi books (Zoe), HP laptop (Luna — Finn wants a laptop but floor $75 > ceiling $95... actually that's possible), wool scarf (Sage), backpack (Dex sells one but nobody else wants it)

**Why it's useful:** Upper-bound control. Almost every deal that could happen will happen. Use this set to establish the maximum possible deal completion rate for comparison against harder sets.

---

### Set 03 — The Sparse Set

**10 agents · 15 items to sell · 16 wants**
Every agent is both a buyer and a seller.

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Mira | Ninja blender, Yoga mat | $35, $15 | Vintage film camera | $60 |
| Felix | Canon AE-1 film camera | $45 | Headphones, Blender | $50, $45 |
| Zara | Sony headphones, Cookbook | $30, $18 | Yoga mat | $25 |
| Hank | Basic tool set | $20 | Cooking books, Bicycle | $25, $80 |
| Priya | Trek mountain bike, Wool scarf | $65, $12 | Indoor plants | $20 |
| Diego | Complete skateboard | $40 | Basic tools, Any camera | $30, $55 |
| Lily | Three succulents, Novel | $15, $8 | Cozy scarf, Wireless headphones | $18, $40 |
| Marcus | JBL Bluetooth speaker | $28 | Skateboard, Fiction books | $50, $12 |
| Isla | Ceramic teapot, Dog-sitting | $22, $30 | Bluetooth speaker | $35 |
| Kai | Pair of 15lb dumbbells | $25 | Teapot, Cookbook | $30, $22 |

**Possible deals (~9):** Camera (Felix→Mira or Diego), Yoga mat (Mira→Zara), Headphones (Zara→Lily), Tools (Hank→Diego), Camera/skateboard (Diego), Succulents (Lily→Priya), Speaker (Marcus→Isla), Teapot (Isla→Kai), Dog-sitting (Isla — if someone wants it)

**Impossible deals: 0.**

**Unmatched items (7):** Mira's blender (Felix wants one but price works, this is a match actually), Priya's bike (Hank wants a bike — also a match), wool scarf (Lily wants a scarf — match), novel (Marcus wants fiction books — match), dog-sitting (nobody explicitly wants it), dumbbells (nobody wants them), cookbook (Zara sells one, Hank/Kai want cooking books — matches)

Note: many of these "unmatched" are actually matches — the keyword script missed them. What truly has no buyer: dog-sitting and dumbbells.

**Why it's useful:** Tests how agents behave when some items genuinely have no buyer. Those agents will burn turns trying before giving up.

---

### Set 04 — The Competitive Set

**10 agents · 15 items to sell · 15 wants**
Every agent is both a buyer and a seller.

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Zara | Ninja blender, Yoga mat | $35, $12 | Vintage camera | $65 |
| Marcus | Polaroid camera | $45 | Blender, Headphones | $50, $40 |
| Luna | Sci-fi books, Sony headphones | $20, $28 | Indoor plants | $25 |
| Raj | Complete skateboard | $40 | Sci-fi books, Bicycle | $30, $85 |
| Sienna | Pothos plants, Cast iron skillet | $18, $22 | Yoga mat | $20 |
| Buck | Basic tool set | $30 | Cast iron pan, Dog-sitting | $35, $45 |
| Ivy | Dog-sitting, HP printer | $35, $38 | Skateboard | $55 |
| Omar | Mountain bike | $65 | Basic tools, Printer | $42, $50 |
| Tess | Acoustic guitar, Board games | $55, $35 | Any camera | $70 |
| Dev | Dell monitor | $48 | Acoustic guitar, Board games | $75, $45 |

**Possible deals (~11):** Camera (Marcus→Zara or Tess), Blender (Zara→Marcus), Yoga mat (Zara→Sienna), Books (Luna→Raj), Skateboard (Raj→Ivy), Plants (Sienna→Luna), Skillet (Sienna→Buck), Tools (Buck→Omar), Dog-sitting (Ivy→Buck), Printer (Ivy→Omar), Guitar+Board games (Tess→Dev both)

**Impossible deals: 0.**

**Unmatched items:** Dell monitor (Dev sells one, nobody explicitly wants a monitor), bike (Omar sells one, Raj wants one — that's a match)

**Why it's useful:** Dev wants both the guitar AND board games from Tess — two items from one seller. Tests whether agents can negotiate bundles or handle multiple simultaneous threads with the same counterpart.

---

### Set 05 — The Chain Set

**10 agents · 15 items to sell · 15 wants**
Every agent is both a buyer and a seller.

| Agent | Sells | Floor | Wants | Ceiling |
|-------|-------|-------|-------|---------|
| Mira | Pentax K1000 film camera, Desk lamp | $45, $15 | Bicycle | $80 |
| Kade | Mountain bike | $65 | Film camera, Sci-fi novels | $60, $20 |
| Zara | Hardcover sci-fi collection, Cast iron skillet | $18, $22 | Wireless headphones | $45 |
| Duke | Leather work boots | $35 | Cordless drill, Cast iron | $55, $30 |
| Lin | Sony headphones, Yoga mat | $38, $12 | Desk lamp | $25 |
| Rex | Black & Decker cordless drill | $42 | Board games, Exercise mat | $35, $18 |
| Nola | Board game bundle, Ninja blender | $30, $28 | Bicycle | $75 |
| Taj | Casio digital watch | $20 | Kitchen blender, Sturdy boots | $40, $45 |
| Jade | Canvas backpack, Dog-sitting | $25, $30 | Digital watch | $28 |
| Vik | Bluetooth speaker | $32 | Backpack, Dog-sitting | $38, $40 |

**Possible deals (~11):** Camera (Mira→Kade), Lamp (Mira→Lin), Sci-fi (Zara→Kade), Skillet (Zara→Duke), Boots (Duke→Taj), Headphones (Lin→Zara), Yoga mat (Lin→Rex), Drill (Rex→Duke), Board games (Nola→Rex), Watch (Taj→Jade), Backpack (Jade→Vik), Dog-sitting (Jade→Vik)

**Impossible deals: 0.**

**Unmatched items:** Blender (Nola sells, Taj wants — match), bicycle (Mira and Nola both want one, only Kade sells — first to close wins). Bluetooth speaker (Vik sells — nobody explicitly wants a speaker here, though Lin or others might take it)

**Competition:** Both Mira and Nola want a bicycle. Only Kade is selling one. Whoever closes first gets it; the other leaves empty-handed on that want. Tests buyer competition for a scarce item.

**Why it's useful:** Clean chain structure. If each deal in the chain closes, it unlocks the next. Tests whether agents can run parallel negotiations without losing track.

---

### Summary Comparison

| Set | Agents | Items to sell | Wants | Possible deals | Impossible deals | Difficulty |
|-----|--------|--------------|-------|---------------|-----------------|------------|
| 01 | 10 | 13 | 15 | ~10 | 2 | High — structural dead-ends |
| 02 | 10 | 15 | 15 | ~10 | 0 | Low — near-perfect overlap |
| 03 | 10 | 15 | 16 | ~9 | 0 | Medium — unmatched supply |
| 04 | 10 | 15 | 15 | ~11 | 0 | Medium — multi-buyer competition |
| 05 | 10 | 15 | 15 | ~11 | 0 | Medium — scarce item competition |

All counts are approximate. "Possible" and "impossible" are based on keyword matching of item descriptions plus price comparison — the script can miss matches where descriptions use different words for the same thing.

---

## How to Run

```bash
# First time setup
uv pip install -e .

# Run with default settings (uses existing personas, generates if none found)
uv run deal

# Generate fresh personas before running
uv run deal --regenerate-personas

# Use a specific frozen persona set
uv run deal --persona-set 2

# Change the model
uv run deal --model anthropic/claude-haiku-4-5

# Longer run with a fixed random seed (reproducible)
uv run deal --max-turns 120 --seed 42

# Use pure random scheduler instead of rotation
uv run deal --scheduler random
```
