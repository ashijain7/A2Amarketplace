# Run Findings — All 5 Persona Sets

Analysis of the first complete run across all 5 frozen persona sets.
Model: `anthropic/claude-sonnet-4.5` via OpenRouter. Scheduler: shuffled rotation.

---

## Run Overview

| Set | Name | Deals | Events | Total Value | Events/Deal | Rejects | Stop Reason |
|-----|------|-------|--------|-------------|-------------|---------|-------------|
| 01 | Friction | 10 | 83 | $486 | 8.3 | 9 | stall |
| 02 | Easy | 14 | 68 | $578 | 4.9 | 6 | stall |
| 03 | Sparse | 10 | 97 | $312 | 9.7 | 20 | stall |
| 04 | Competitive | 10 | 77 | $416 | 7.7 | 13 | stall |
| 05 | Chain | 14 | 78 | $523 | 5.6 | 3 | stall |

---

## Set 01 — Friction Set

**10 deals · $486 total · 83 events · 9 rejects**

### Deal log

| Turn | Seller | Buyer | Item | Price | Seller Margin | Buyer Savings |
|------|--------|-------|------|-------|--------------|---------------|
| 6 | Samir | Buck | Weber charcoal grill | $55 | +$15 | $0 |
| 14 | Buck | Priya | Trek mountain bike | $95 | +$20 | $0 |
| 16 | Derek | Rosa | Polaroid camera | $55 | +$10 | $15 |
| 18 | Zoe | Kai | Dog-sitting | $28 | +$8 | $12 |
| 19 | Lin | Samir | Sci-fi paperbacks | $25 | +$7 | $5 |
| 21 | Priya | Jax | Sony headphones | $85 | +$5 | $5 |
| 30 | Maya | Derek | Ninja blender | $50 | +$15 | $0 |
| 35 | Buck | Jax | Toolbox | $35 | +$15 | $3 |
| 50 | Zoe | Lin | Cast iron teapot | $35 | +$7 | $0 |
| 64 | Maya | Samir | Yoga mat | $23 | +$8 | $2 |

### Per-agent outcomes

| Agent | Sold | Unsold | Wants Fulfilled | Wants Unfulfilled | Revenue | Spent | Net |
|-------|------|--------|-----------------|-------------------|---------|-------|-----|
| Maya | 2 | 0 | 0 | 1 | $73 | $0 | **+$73** |
| Derek | 1 | 0 | 1 | 1 | $55 | $50 | +$5 |
| Priya | 1 | 0 | 1 | 0 | $85 | $95 | -$10 |
| Buck | 2 | 0 | 1 | 0 | $130 | $55 | **+$75** |
| Lin | 1 | 0 | 1 | 1 | $25 | $35 | -$10 |
| Samir | 1 | 0 | 2 | 0 | $55 | $48 | +$7 |
| Zoe | 2 | 0 | 0 | 1 | $63 | $0 | +$63 |
| Kai | 0 | 1 | 1 | 1 | $0 | $28 | **-$28** |
| Rosa | 0 | 1 | 1 | 0 | $0 | $55 | **-$55** |
| Jax | 0 | 1 | 2 | 0 | $0 | $120 | **-$120** |

### What went unsold
- Kai's Corsair keyboard — floor $50, Zoe's ceiling $35 — **structurally impossible**
- Rosa's JBL speaker — floor $55, Kai's ceiling $40 — **structurally impossible**
- Jax's skateboard — no buyer expressed interest

### What went unfulfilled
- Maya's vintage camera want — nobody sold it
- Derek's headphones want — Derek bought a blender, headphones ceiling ($45) was below Priya's floor ($80)
- Lin's yoga mat — Lin bought a teapot instead, yoga mat want unfulfilled
- Kai's mechanical keyboard — bought dog-sitting, keyboard unsold
- Jax's backpack — nobody selling one

### Findings
- The two structurally impossible deals (keyboard, speaker) stayed unsold exactly as predicted. Agents made several attempts and eventually stopped.
- Jax bought $120 worth of goods (headphones + toolbox) but sold nothing. Biggest deficit of the run.
- Buck extracted $20 above his floor on the bike (sold at $95 vs floor $75) — buyer Priya paid her exact ceiling.
- 3 reject events from agents countering on an offer ID (`off_017`) instead of a listing ID — the most common targeting error in the simulation.
- Avg seller margin: **+$11.00**. Avg buyer savings: **$4.20**. Sellers significantly outperformed buyers.

---

## Set 02 — Easy Set

**14 deals · $578 total · 68 events · 6 rejects**

### Deal log

| Turn | Seller | Buyer | Item | Price | Seller Margin | Buyer Savings |
|------|--------|-------|------|-------|--------------|---------------|
| 6 | Iris | Bo | Bluetooth speaker | $28 | +$6 | $7 |
| 14 | Sage | Dex | Cast iron teapot | $35 | +$10 | $0 |
| 18 | Iris | Luna | Yoga mat | $24 | +$6 | $1 |
| 19 | Luna | Finn | HP laptop | $95 | +$20 | $0 |
| 22 | Zoe | Bo | Sci-fi books | $25 | +$5 | $0 |
| 25 | Mira | Kai | Vintage film camera | $62 | +$17 | $3 |
| 33 | Sage | Luna | Wool scarf | $20 | +$5 | — |
| 35 | Luna | Kai | Timex watch | $28 | +$8 | $2 |
| 44 | Bo | Iris | Over-ear headphones | $33 | +$5 | $7 |
| 46 | Kai | Mira | Road bike | $70 | +$10 | $15 |
| 49 | Mira | Zoe | Succulents | $18 | +$6 | $0 |
| 54 | Rex | Sage | Cordless drill | $50 | +$10 | $0 |
| 57 | Zoe | Finn | Desk lamp | $20 | +$5 | $0 |
| 58 | Finn | Rex | Switch games | $70 | +$15 | $0 |

### Per-agent outcomes

| Agent | Sold | Unsold | Wants Fulfilled | Wants Unfulfilled | Revenue | Spent | Net |
|-------|------|--------|-----------------|-------------------|---------|-------|-----|
| Mira | 2 | 0 | 1 | 0 | $80 | $70 | +$10 |
| Kai | 1 | 0 | 2 | 0 | $70 | $90 | -$20 |
| Zoe | 2 | 0 | 1 | 0 | $45 | $18 | +$27 |
| Bo | 1 | 0 | 2 | 0 | $33 | $53 | -$20 |
| Iris | 2 | 0 | 1 | 0 | $52 | $33 | +$19 |
| Finn | 1 | 0 | 2 | 0 | $70 | $115 | -$45 |
| Luna | 2 | 0 | 2 | 0 | $123 | $44 | **+$79** |
| Rex | 1 | 0 | 1 | 1 | $50 | $70 | -$20 |
| Sage | 2 | 0 | 1 | 0 | $55 | $50 | +$5 |
| Dex | 0 | 1 | 1 | 1 | $0 | $35 | -$35 |

### What went unsold
- Dex's North Face backpack — nobody in this set wanted a backpack

### What went unfulfilled
- Rex's hand tools want — nobody selling hand tools
- Dex's warm scarf want — nobody selling a scarf

### Findings
- Highest deal count (14) and highest total value ($578) of all 5 runs.
- Most efficient market: 4.9 events per deal — negotiations were short because prices overlapped cleanly.
- 0 declines across the entire run. Agents never needed to send a hard price signal.
- Both predicted circular swaps confirmed: Mira sold camera to Kai, Kai sold bike to Mira. Bo sold speaker to Iris, Iris sold headphones to Bo.
- Luna was the standout: sold laptop ($95) and watch ($28), bought yoga mat ($24). Net +$79.
- Finn spent $115 buying laptop and desk lamp but only recovered $70 from game sales. Net -$45.
- Avg buyer savings: **$2.50** — lowest of all sets. In a liquid market, buyers paid close to their ceiling.
- All 6 rejects were counter-on-offer-ID errors. No ceiling/floor violations attempted.

---

## Set 03 — Sparse Set

**10 deals · $312 total · 97 events · 20 rejects**

### Deal log

| Turn | Seller | Buyer | Item | Price | Seller Margin | Buyer Savings |
|------|--------|-------|------|-------|--------------|---------------|
| 12 | Lily | Priya | Succulents | $20 | +$5 | $0 |
| 14 | Marcus | Isla | JBL Bluetooth speaker | $35 | +$7 | $0 |
| 19 | Zara | Hank | Sony headphones | $25 | +$7 | — |
| 20 | Isla | Kai | Ceramic teapot | $28 | +$6 | $2 |
| 28 | Zara | Felix | Cookbook | $40 | +$10 | $10 |
| 33 | Mira | Felix | Ninja blender | $42 | +$7 | $3 |
| 37 | Lily | Marcus | Novel | $12 | +$4 | — |
| 39 | Hank | Priya | Basic tool set | $32 | +$12 | — |
| 57 | Felix | Mira | Canon AE-1 film camera | $58 | +$13 | $2 |
| 71 | Mira | Zara | Yoga mat | $20 | +$5 | $5 |

### Per-agent outcomes

| Agent | Sold | Unsold | Wants Fulfilled | Wants Unfulfilled | Revenue | Spent | Net |
|-------|------|--------|-----------------|-------------------|---------|-------|-----|
| Mira | 2 | 0 | 1 | 0 | $62 | $58 | +$4 |
| Felix | 1 | 0 | 2 | 0 | $58 | $82 | -$24 |
| Zara | 2 | 0 | 1 | 0 | $65 | $20 | **+$45** |
| Hank | 1 | 0 | 1 | 1 | $32 | $25 | +$7 |
| Priya | 0 | 2 | 2 | 0 | $0 | $52 | -$52 |
| Diego | 0 | 1 | 0 | 2 | $0 | $0 | $0 |
| Lily | 2 | 0 | 0 | 2 | $32 | $0 | +$32 |
| Marcus | 1 | 0 | 1 | 1 | $35 | $12 | +$23 |
| Isla | 1 | 1 | 1 | 0 | $28 | $35 | -$7 |
| Kai | 0 | 1 | 1 | 1 | $0 | $28 | -$28 |

### What went unsold
- Priya's Trek mountain bike and wool scarf — Hank wanted a bike (ceiling $80 vs floor $65, possible) but bought tools instead
- Diego's complete skateboard — nobody wanted it
- Isla's dog-sitting service — nobody wanted it
- Kai's pair of 15lb dumbbells — nobody wanted them

### What went unfulfilled
- Hank's cooking books want — nobody selling
- Diego's basic tools want and camera want — nobody selling tools, camera priced above ceiling
- Lily's cozy scarf and wireless headphones wants — nobody selling
- Marcus's skateboard and fiction books wants
- Kai's cookbook want

### Findings
- Highest event count (97) and lowest total value ($312) of all 5 runs.
- Most chaotic run: 20 rejects, 9.7 events per deal.
- The dominant reject type shifted: 15 of 20 were "accept price above all ceilings" — agents tried to close deals at prices exceeding their own stated maximum. This only appeared significantly in Sets 03 and 04, suggesting it correlates with a noisier, more competitive channel.
- Diego was completely inactive: sold nothing, bought nothing, net $0. His skateboard had no buyer and his wants had no sellers at workable prices.
- Priya bought two items ($52 total) but both her items went unsold. Net -$52 despite no constraint violations.
- Avg buyer savings: **$11.50** — highest of all sets. When deals finally closed in a sparse market, buyers extracted significant value.
- Lowest total value ($312) because the high-value items (bike, headphones) never sold. Only small-ticket items closed.

---

## Set 04 — Competitive Set

**10 deals · $416 total · 77 events · 13 rejects**

### Deal log

| Turn | Seller | Buyer | Item | Price | Seller Margin | Buyer Savings |
|------|--------|-------|------|-------|--------------|---------------|
| 9 | Sienna | Luna | Pothos plants | $25 | +$7 | $0 |
| 14 | Zara | Marcus | Ninja blender | $43 | +$8 | $7 |
| 23 | Ivy | Buck | Dog-sitting | $45 | +$10 | $0 |
| 24 | Tess | Dev | Board games | $45 | +$10 | $30 |
| 25 | Sienna | Buck | Cast iron skillet | $28 | +$6 | $7 |
| 29 | Raj | Ivy | Complete skateboard | $55 | +$15 | $0 |
| 30 | Luna | Marcus | Sony headphones | $32 | +$12 | $8 |
| 34 | Tess | Raj | Acoustic guitar | $70 | +$15 | $15 |
| 36 | Zara | Sienna | Yoga mat | $18 | +$6 | $2 |
| 48 | Marcus | Tess | Polaroid camera | $55 | +$10 | $15 |

### Per-agent outcomes

| Agent | Sold | Unsold | Wants Fulfilled | Wants Unfulfilled | Revenue | Spent | Net |
|-------|------|--------|-----------------|-------------------|---------|-------|-----|
| Zara | 2 | 0 | 0 | 1 | $61 | $0 | **+$61** |
| Marcus | 1 | 0 | 2 | 0 | $55 | $75 | -$20 |
| Luna | 1 | 1 | 1 | 0 | $32 | $25 | +$7 |
| Raj | 1 | 0 | 1 | 1 | $55 | $70 | -$15 |
| Sienna | 2 | 0 | 1 | 0 | $53 | $18 | +$35 |
| Buck | 0 | 1 | 2 | 0 | $0 | $73 | **-$73** |
| Ivy | 1 | 1 | 1 | 0 | $45 | $55 | -$10 |
| Omar | 0 | 1 | 0 | 2 | $0 | $0 | $0 |
| Tess | 2 | 0 | 1 | 0 | $115 | $55 | **+$60** |
| Dev | 0 | 1 | 1 | 1 | $0 | $45 | -$45 |

### What went unsold
- Luna's Sony headphones sold; her sci-fi books did not — no buyer at right price
- Buck's basic tool set — Omar wanted tools (ceiling $42 > floor $30, possible) but Omar never closed any deal
- Ivy's HP printer — Omar wanted a printer (ceiling $50 > floor $38, possible) but Omar was inactive
- Omar's mountain bike — Raj wanted a bike but spent his budget on the skateboard first
- Dev's Dell monitor — nobody wanted a monitor

### What went unfulfilled
- Zara's vintage camera want — Marcus sold a camera but Zara never bought it (she sold out her own items first)
- Raj's bicycle want — Omar's bike was available and priced right, but the deal never formed
- Omar's two wants — his counterparts were busy or had already sold
- Dev's board games want — Tess sold board games to Raj first

### Findings
- Tess was the standout agent: sold both items (guitar $70, board games $45) and bought a camera ($55). Net +$60. The "one buyer wants both your items" dynamic (Dev wanted both guitar and board games) created competition — Tess ended up selling guitar to Raj at a higher price ($70) and board games to Dev ($45).
- Buck bought $73 of goods (dog-sitting + skillet) but his toolbox went unsold. Same pattern as Jax in Set 01: buying freely while failing to sell.
- Omar was completely inactive: his bike floor ($65) was above what the market would bear once Raj spent his budget on the skateboard. Net $0.
- "Accept above ceiling" was again the dominant reject type (9 of 13) — same confusion as Set 03. Both Sets 03 and 04 had more simultaneous negotiations running, suggesting multi-threading causes agents to lose track of their own price limits.
- 2 declines in this run — only Set 01 (7) and Set 04 (2) used decline at all.

---

## Set 05 — Chain Set

**14 deals · $523 total · 78 events · 3 rejects**

### Deal log

| Turn | Seller | Buyer | Item | Price | Seller Margin | Buyer Savings |
|------|--------|-------|------|-------|--------------|---------------|
| 17 | Duke | Taj | Leather work boots | $45 | +$10 | $0 |
| 18 | Nola | Vik | Board game bundle | $38 | +$8 | $2 |
| 24 | Mira | Kade | Pentax K1000 camera | $55 | +$10 | $5 |
| 25 | Taj | Vik | Casio digital watch | $30 | +$10 | $8 |
| 32 | Rex | Duke | Black & Decker drill | $53 | +$11 | $2 |
| 36 | Jade | Vik | Canvas backpack | $32 | +$7 | — |
| 37 | Mira | Lin | Desk lamp | $22 | +$7 | $3 |
| 38 | Kade | Nola | Mountain bike | $65 | +$0 | $10 |
| 39 | Zara | Mira | Cast iron skillet | $23 | +$1 | $57 |
| 44 | Nola | Taj | Ninja blender | $35 | +$7 | $5 |
| 54 | Lin | Zara | Sony headphones | $44 | +$6 | $1 |
| 62 | Jade | Vik | Dog-sitting | $35 | +$5 | — |
| 63 | Lin | Rex | Yoga mat | $18 | +$6 | $17 |
| 68 | Zara | Duke | Hardcover sci-fi | $28 | +$10 | $2 |

### Per-agent outcomes

| Agent | Sold | Unsold | Wants Fulfilled | Wants Unfulfilled | Revenue | Spent | Net |
|-------|------|--------|-----------------|-------------------|---------|-------|-----|
| Mira | 2 | 0 | 1 | 0 | $77 | $23 | **+$54** |
| Kade | 1 | 0 | 1 | 1 | $65 | $55 | +$10 |
| Zara | 2 | 0 | 1 | 0 | $51 | $44 | +$7 |
| Duke | 1 | 0 | 2 | 0 | $45 | $81 | -$36 |
| Lin | 2 | 0 | 1 | 0 | $62 | $22 | **+$40** |
| Rex | 1 | 0 | 1 | 1 | $53 | $18 | +$35 |
| Nola | 2 | 0 | 1 | 0 | $73 | $65 | +$8 |
| Taj | 1 | 0 | 2 | 0 | $30 | $80 | -$50 |
| Jade | 2 | 0 | 0 | 1 | $67 | $0 | **+$67** |
| Vik | 0 | 1 | 4 | 0 | $0 | $135 | **-$135** |

### What went unsold
- Vik's Bluetooth speaker — nobody in this set explicitly wanted a speaker

### What went unfulfilled
- Kade's sci-fi novels want — nobody selling at a workable price
- Rex's exercise mat want — nobody selling
- Jade's digital watch want — Taj sold a watch but the deal never formed with Jade

### Findings
- Cleanest run of all 5: only 3 rejects, all counter-on-offer-ID errors. The chain structure reduced confusion — agents had clear bilateral negotiations rather than competing threads.
- Vik is the most extreme agent outcome across all 5 runs: net -$135. He bought backpack ($32), dog-sitting twice ($32 + $35), blender ($38) — 4 fulfilled wants — but his Bluetooth speaker found zero buyers. He fulfilled every want he had but earned nothing.
- Jade earned +$67 selling exclusively to Vik. Vik's eagerness to buy everything Jade was selling created a one-sided dynamic.
- Kade sold his bike to Nola at exactly floor price ($65), margin $0. First time in any run a seller extracted zero above their floor. Nola had been waiting since Mira got the bike first (turn 24) and accepted asking price.
- Mira resolved the bicycle competition: she closed first (turn 24, $55) while Nola had to wait and accept $65 floor price on turn 38.
- 0 declines. No agent needed to block a price range.
- Zara bought the skillet from Mira at $23 — Mira's floor was $22, savings of $57 vs ceiling $80. Biggest buyer savings of this run.
- Avg seller margin: **+$7.00**, avg buyer savings: **+$8.00** — the most balanced of all 5 runs.

---

## Cross-Set Findings

### Finding 1 — Zero constraint violations, all 5 runs

58 total deals across all runs. Not one violated a floor or ceiling. The enforcement mechanism is airtight. Every agent always sold at or above their floor and bought at or below their ceiling.

---

### Finding 2 — Every run ended in stall

No run hit the 120-turn cap. No run had every agent fully satisfied. Every single run stalled when the remaining deals were either structurally impossible or agents could not form them. The stall detection correctly identified when no progress was possible.

---

### Finding 3 — Deal count splits into two groups: 10 or 14

Sets 01, 03, 04 all closed exactly 10 deals. Sets 02 and 05 both closed 14. The two high-deal sets had the cleanest structures — no impossible price gaps, no sparse demand. The three 10-deal sets each had a structural reason deals could not form (impossible prices, orphan items, incomplete chains).

---

### Finding 4 — Counter-on-wrong-ID is the most persistent LLM error

Every single run had agents countering on an offer event ID (`off_xxx`) instead of the listing event ID (`lst_xxx`). This error appeared despite the explicit CASE 1/2/3 targeting examples added to the agent template. It is the one error that did not go away.

---

### Finding 5 — Two distinct reject patterns by market type

| Reject type | Sets it appears in |
|-------------|-------------------|
| Counter against non-listing ID | All 5 runs |
| Accept price above all ceilings | Sets 03 and 04 only |

The "accept above ceiling" error only appeared in the two most complex markets (sparse demand and multi-buyer competition). It did not appear in Sets 01, 02, or 05. Hypothesis: when multiple negotiations run simultaneously, agents lose track of their own price limits.

---

### Finding 6 — Sellers outperformed buyers in 3 of 5 runs

| Set | Avg Seller Margin | Avg Buyer Savings | Winner |
|-----|------------------|------------------|--------|
| 01 | +$11.00 | $4.20 | Sellers |
| 02 | +$9.14 | $2.50 | Sellers |
| 03 | +$7.60 | $11.50 | Buyers |
| 04 | +$9.90 | $8.40 | Sellers |
| 05 | +$7.00 | $8.00 | Buyers (marginal) |

In liquid markets (Sets 01, 02, 04) sellers extracted more. In sparse markets (Set 03) buyers extracted more. When supply exceeds demand, buyers have leverage.

---

### Finding 7 — Message economy tracks market difficulty

| Set | Events/Deal | Interpretation |
|-----|-------------|----------------|
| 02 | 4.9 | Clean market, fast closes |
| 05 | 5.6 | Chain structure, clear bilateral deals |
| 04 | 7.7 | Competition creates longer threads |
| 01 | 8.3 | Impossible deals waste turns |
| 03 | 9.7 | Sparse market, many failed attempts |

Fewer events per deal = more efficient agents. Higher events per deal = more wasted turns from targeting errors, impossible deals, or confused agents.

---

### Finding 8 — The "completely inactive agent" pattern

Two agents across two runs ended with net $0 — no sales, no purchases:
- **Diego (Set 03):** skateboard had no buyer, wanted tools and camera with no matching seller
- **Omar (Set 04):** bike floor ($65) too high once Raj's budget was spent, wanted tools and printer but counterparts were busy

These agents correctly passed rather than making invalid moves, but they burned stall turns. The simulation has no mechanism for an agent to exit early once their situation is hopeless.

---

### Finding 9 — Decline is almost never used

| Set | Declines |
|-----|---------|
| 01 | 7 |
| 02 | 0 |
| 03 | 0 |
| 04 | 2 |
| 05 | 0 |

9 total declines across 58 deals in 5 runs. The model strongly prefers to counter or pass rather than send an explicit rejection. The decline-blocks-price mechanic was barely triggered. Worth investigating: does the model avoid decline strategically (keeping options open) or does it simply not read the decline rule closely enough?

---

### Finding 10 — Extreme net outcomes

Biggest gains and losses across all runs:

| Agent | Set | Net | Reason |
|-------|-----|-----|--------|
| Vik | 05 | -$135 | Bought 4 items, sold nothing |
| Jax | 01 | -$120 | Bought 2 items, sold nothing |
| Buck | 04 | -$73 | Bought 2 items, sold nothing |
| Luna | 02 | +$79 | Sold laptop at $20 above floor |
| Buck | 01 | +$75 | Sold 2 items, bought selectively |
| Jade | 05 | +$67 | Sold 2 items to one eager buyer |

The pattern is consistent: **agents who went into deficit bought multiple items but failed to sell**. They did not violate their own ceiling prices — they were rational buyers. But their items found no market. Winners sold multiple items and bought selectively or not at all.

---

### Finding 11 — Total value by set

| Set | Deals | Total Value | Avg per Deal |
|-----|-------|-------------|-------------|
| 02 | 14 | $578 | $41 |
| 05 | 14 | $523 | $37 |
| 01 | 10 | $486 | $49 |
| 04 | 10 | $416 | $42 |
| 03 | 10 | $312 | $31 |

Set 01 has the highest average deal value ($49) despite the same deal count as Sets 03 and 04. Its market contains higher-priced items (bike $95, headphones $85). Set 03's low total ($312) reflects that the high-value items never sold — only small-ticket deals closed.

---

## Summary Table

| Metric | Set 01 | Set 02 | Set 03 | Set 04 | Set 05 |
|--------|--------|--------|--------|--------|--------|
| Deals closed | 10 | **14** | 10 | 10 | **14** |
| Total value | $486 | **$578** | $312 | $416 | $523 |
| Events/deal | 8.3 | **4.9** | 9.7 | 7.7 | 5.6 |
| Rejects | 9 | 6 | **20** | 13 | **3** |
| Declines | 7 | 0 | 0 | 2 | 0 |
| Avg seller margin | **+$11.00** | +$9.14 | +$7.60 | +$9.90 | +$7.00 |
| Avg buyer savings | $4.20 | $2.50 | **$11.50** | $8.40 | $8.00 |
| Constraint violations | 0 | 0 | 0 | 0 | 0 |
| Completely inactive agents | 0 | 0 | 1 | 1 | 0 |
| Stop reason | stall | stall | stall | stall | stall |
