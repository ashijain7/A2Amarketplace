# RL-ADA, explained simply — and how it wires with Project Deal

A plain-English walkthrough of the paper **"RL-ADA: A World-Feedback Framework for Adversarially Robust Enterprise Dialogue Agents"** (Ram Narayanan, Harshit Rajgarhia, Abhishek Mukherji — all Centific, KDD Workshop), and how it connects to our marketplace + settlement work.

---

## The paper in one breath

RL-ADA is a way to train a customer-support AI by making it **fight an adversary AI that keeps trying to trip it up** — with no human grading any data. Two AIs spar like boxers; a referee AI keeps score; whoever is losing goes off to practice on its own mistakes; they repeat until neither can reliably beat the other.

Our project already has this exact shape — a focal agent vs. a DeepSeek scammer, with a GPT-4o judge. The difference: **we only measure who won. RL-ADA adds the practice step that actually makes the agent better.**

---

## Why the paper needed to exist (the problem)

To make a support AI good, you normally show it thousands of example conversations where a human has already marked the right action for each. That human marking is called **annotation** (labelling). It causes three pains:

- **Expensive** — humans labelling thousands of chats costs a lot.
- **Private** — real customer chats contain personal data, so you can't freely share them.
- **Always out of date** — customers invent new phrasings faster than you can label. The moment the answer key is done, the questions change.

The result: agents that ace the practice test (the **benchmark**) but break when a real, unpredictable customer pushes on them.

Existing shortcuts only half-help. **RLHF** (training from human ratings) still needs lots of humans. **Self-play** (an AI playing a copy of itself) assumes both players are the *same kind* — but support is **asymmetric**: the support agent and the customer have different jobs and abilities (a goalkeeper vs. a striker). RL-ADA is built for that asymmetric, no-labels case.

---

## The three characters

The whole method is three AIs:

- **The Helper** — the support agent. The paper abbreviates it **"DA"**, and uses a *small* model (Qwen2.5, 3 billion parameters; §3). Its job: read the conversation and decide to **use a tool**, **say something**, or **end the call**.
- **The Trickster** — the adversarial customer. Abbreviated **"CA"**, a *bigger* model (Qwen2.5, 7B; §3). Its job: talk like a confusing customer and fool the Helper into the **wrong** action.
- **The Referee** — the judge. A separate model (Qwen2.5, 7B; §3.1) that scores how well each conversation went. It is deliberately a *local* model (not GPT) so training never depends on an outside company. They checked it agrees with GPT-4o-mini, including a **perfect** score (F1 1.000; Table 1) at catching made-up facts (**hallucinations**).

The Trickster being *bigger* than the Helper is on purpose: deception is its own hard skill, and the Helper is the one you'd actually deploy at scale, so you want it small and cheap.

A concrete example of the battle (from §3): the Trickster says *"I see something odd on my statement."* The Helper must guess — does the customer want to **dispute a charge** or just **see recent transactions**? The vague phrasing is the trap.

---

## The loop — three steps, repeated (Figure 1)

1. **They play.** The Helper and the Trickster run *many* conversations — 180 in one round (18 conversations across 10 scenarios; §3.4). One conversation could be luck, so you need a big batch. The Referee scores each, and we tally what fraction the Helper got right.

2. **The loser practices.** Whoever did worse studies its *own recent mistakes* — like a team watching game tape of matches they lost. Meanwhile the winner is **frozen** (kept unchanged). The practice set is a **70:30 mix** (§3.5): 70% recent mistakes, 30% past wins.

3. **Play again.** The improved loser plays a fresh batch. Repeat until the two are evenly matched — a stable balance — then stop. In the experiments this took **5 rounds** (§5.1).

### The one clever trick: only one player trains at a time

Freezing the winner and training only the loser fixes two classic problems:

- **Non-stationarity** (the "moving dartboard"): if both sides change at once, you can't tell if you improved or the opponent just moved. Freezing the winner gives the loser a *still* target.
- **Catastrophic forgetting** (learning new things makes you forget old ones): the 70:30 mix keeps some past wins in the practice, so the loser fixes its mistakes *without* forgetting what it already did well.

---

## The results — did it work?

To prove the Helper *really* learned (and didn't just memorize practice), they gave it a **surprise test**: 12 fresh situations it had never trained on (Table 4, §5.2). Before vs. after the game:

| What was measured | Before (DA₀) | After (DA₂) | Source |
|---|---|---|---|
| Picked the right action | 75% | **100%** | Table 4 |
| "Did everything right" (strict PASS) | 25% | **50%** | Table 4 |
| Overall fail rate | 33% | 33% | Table 4 |
| Average score per conversation | +1.58 | +2.16 | Table 4 |
| Tried a safe lookup first | 58% | 83% | Table 4 |

The Helper went from picking the wrong action a quarter of the time to **never** picking the wrong one — with **no human grading**, purely from playing the game.

**Honest caveat (the paper is upfront):** the overall fail rate stayed at 33%, but the *reason* for failing changed. Before, it failed by **picking the wrong action**; after, it always picks the right action but sometimes fumbles on **conversation quality**. The exact problem they attacked got fully fixed; what's left is a gentler problem for more rounds.

The win-rate also **bounced up and down** across rounds rather than rising steadily (§5.1). That bouncing is a *good* sign — it means both sides kept genuinely catching up to each other.

### The surprise: "Contextual Camouflage"

Nobody told the Trickster *how* to be tricky — it was only rewarded for fooling the Helper. On its own it discovered a tactic (§5.3): instead of saying *too little* (vague), it gave *lots* of real, specific detail — merchant names, exact amounts, dates — and **buried the real request in the middle of all that detail**. Like hiding one key fact inside a long, realistic, rambling story. The paper calls this **Contextual Camouflage**. The striking part: an AI *invented a deception strategy by itself*, just because it worked.

---

## The honest limitations

The authors call this preliminary work and admit:

1. **Only tested in one world — banking** (§6). The strongest limitation, and the reason this collaboration matters.
2. **The "when to stop" rule and settings (like 70:30) were chosen by gut**, not careful tuning.
3. **Never faced real live customers** — it all ran in the simulated game.
4. **The Trickster sometimes broke character** and impersonated the bank's own agent; patched with instructions but not fully eliminated.

They also state the method is meant to be **domain-agnostic** (works in any field — swap the tools, re-check the referee; §7) but **admit they haven't shown this yet**. That single admission is exactly what our project can answer.

---

## How it wires with Project Deal

### We already have all three characters

| RL-ADA needs | We already have |
|---|---|
| The Helper (support agent) | Our **focal agent** (Claude Sonnet / Haiku) |
| The Trickster (adversarial customer) | Our **DeepSeek scammer** (payee-redirect, credential-phish, fake-receipt) |
| The Referee (judge) | Our **GPT-4o judge** |

And our project has **two** flavours that match the paper's two halves:

- **Settlement + scammer** = a direct match for the *adversarial* half (Helper vs. attacker). This is the clean "red-teaming / phishing" use Karthikeya wants.
- **Core marketplace + reviews + swaps** = a match for the *general machinery* half (referee + outcome-reward + practice loop), where the "opponent" is a fellow bargainer rather than an attacker. Here RL-ADA would train a *better negotiator* rather than a fraud-resister.

### What we already do vs. what we'd add

Today we do **Step 1 only** — the focal and the scammer play, and the judge scores it. We do **not** do Steps 2 and 3: nobody collects the losses, practices, and replays. **The gym is the missing piece.** Adding it turns our static "measure it" setup into a self-improving "train it" loop.

### Two ways to wire in the practice loop (the open decision)

**Approach A — train model weights (closest to the paper).**
Switch the focal (and/or the scammer) to *open* models we can actually fine-tune (the paper uses Qwen2.5 3B/7B), then run real reinforcement-learning practice on GPUs. Pros: faithful to RL-ADA, biggest skill gains, strongest paper result. Cons: needs trainable models + GPU pipeline; it's a bigger build.

**Approach B — improve by prompts, not weights (lighter).**
Keep our API models (Claude / DeepSeek via OpenRouter) and run the same loop, but the "practice" updates the agent's *instructions and examples* from its recent losses instead of retraining its brain. Pros: works with our current models, much cheaper. Cons: weaker than true training; not what the paper demonstrates, so a smaller research claim.

A sensible path: prove the *loop* end-to-end with Approach B first (cheap, fast), then do one slice of Approach A on open models for the headline result.

### Which agent to train first (also a choice)

- **Train the Helper (focal):** makes our agent more scam-resistant and a better negotiator — the "defend" story.
- **Train the Trickster (scammer):** makes it discover new scam tactics on its own (the Contextual Camouflage effect) — the "red-team" story Karthikeya wants.
- Both is the full co-evolution, but start with whichever matches the first paper we want to write.

### Two things to settle with the authors early

1. **Trainable models vs. API models.** RL-ADA trains open models with RL (needs GPUs). Our agents are API models we can't fine-tune the same way. Pick Approach A or B up front — it's the single biggest practical question.
2. **A trustworthy referee for our world.** They validated their judge for banking (Table 1). Our GPT-4o judge would need the same check for *marketplace + scam* scoring before its scores can safely drive training.

---

## Bottom line

- The paper and our project are **the same idea in different clothes**: an adversary stress-tests a helper, a referee scores it, and the loser practices.
- Their **gap** is our **strength**: they've only shown it in banking; our marketplace + scam world is a strong *second domain* that turns their "works anywhere" claim from a hope into a result.
- Their **strength** is our **gap**: we measure but don't yet train; their gym is the piece that would make our agents actually improve.
- The main thing to agree on before starting is **trainable open models vs. our current API models** (Approach A vs. B).
