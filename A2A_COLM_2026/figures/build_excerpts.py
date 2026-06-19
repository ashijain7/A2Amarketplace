#!/usr/bin/env python3
"""Mine real per-config, per-stage transcript excerpts for the pairing figures.
Sources (see memory reference_focal_toolcalls_location):
  - channel.jsonl     : public marketplace messages (listings/offers/counters/accepts)
  - rollout.json       : response.output = focal's real tool calls (lookup_agent, swaps)
  - private_rooms/*.jsonl : settlement room dialogue (say/pay/outcome)
Phase->Stage: phase1=I, phase2=II, phase4=III(settlement), phase3=IV(swap).
Writes excerpts.json.
"""
import json, glob, os, re

ROOT = "/Users/ashi.jain/Documents/project_deal/results/paper_runs"
CONFIGS = {
    "C1": ("C1_sonnet_vs_sonnet",  "Sonnet 4.5",     "Sonnet 4.5"),
    "C4": ("C4_sonnet_vs_gemini",  "Sonnet 4.5",     "Gemini 3.1 Pro Preview"),
    "C6": ("C6_opus_vs_gemini",    "Opus 4.7",       "Gemini 3.1 Pro Preview"),
    "C7": ("C7_gemini_vs_gpt55",   "Gemini 3.1 Pro Preview", "GPT-5.5"),
    "C8": ("C8_gemini35_vs_gpt55", "Gemini 3.5 Flash","GPT-5.5"),
    "C9": ("C9_opus48_vs_gpt55",   "Opus 4.8",       "GPT-5.5"),
    "C10":("C10_gpt55_vs_opus48",  "GPT-5.5",        "Opus 4.8"),
}

def load(p):
    return json.load(open(p))

def focal_of(setdir):
    return load(os.path.join(setdir, "rollout.json"))["metadata"]["focal_persona"]

def deals_of(setdir):
    d = load(os.path.join(setdir, "deals.json"))
    d = d if isinstance(d, list) else d.get("deals", [])
    return [x for x in d if isinstance(x, dict)]

def fcalls(setdir):
    """ordered (name, args_dict, output_text_or_None) from focal tool log"""
    out = load(os.path.join(setdir, "rollout.json")).get("response", {}).get("output", [])
    seq = []
    for o in out:
        if not isinstance(o, dict):
            continue
        if o.get("type") == "function_call":
            try: a = json.loads(o.get("arguments", "{}"))
            except: a = {}
            seq.append(["call", o.get("name"), a])
        elif o.get("type") == "function_call_output":
            seq.append(["out", str(o.get("output", ""))])
    return seq

def channel(setdir):
    return [json.loads(l) for l in open(os.path.join(setdir, "channel.jsonl"))]

def listing_msg(ev, seller):
    for e in ev:
        if e.get("action") == "listing" and e.get("agent") == seller:
            return e.get("message", ""), e.get("price")
    return "", None

def thread_for_item(ev, focal, item):
    """ordered bubbles for one item, following the listing->offer->counter->accept chain
    (an accept targets the offer id, not the listing, so we walk transitively)."""
    acts = ("listing", "offer", "counter", "accept", "decline")
    ids = {e["event_id"] for e in ev if e.get("action") == "listing" and e.get("target") == item} | {item}
    keep = set()
    for _ in range(12):  # transitive closure over the offer chain
        grew = False
        for e in ev:
            if e.get("action") in acts and e["event_id"] not in keep and e.get("target") in ids:
                keep.add(e["event_id"]); ids.add(e["event_id"]); grew = True
        if not grew: break
    chain = sorted((e for e in ev if e["event_id"] in keep), key=lambda e: e.get("turn", 0))
    return [{"who": "eval" if e["agent"] == focal else "opp", "name": e["agent"],
             "act": e["action"], "price": e.get("price"), "msg": e.get("message","")} for e in chain]

# ---------- Stage I : richest closed deal involving focal ----------
def deal_thread(cfgdir, phase):
    best = None
    for setdir in sorted(glob.glob(f"{cfgdir}/{phase}/set_*")):
        focal = focal_of(setdir); ev = channel(setdir)
        for d in deals_of(setdir):
            role = "seller" if d.get("seller") == focal else ("buyer" if d.get("buyer") == focal else None)
            if not role: continue
            msgs = thread_for_item(ev, focal, d.get("item_id"))
            ncounter = sum(1 for m in msgs if m["act"] == "counter")
            if msgs and (best is None or ncounter > best[0]):
                best = (ncounter, {"focal": focal, "role": role, "item": d.get("item_id"),
                                    "partner": d.get("buyer") if role == "seller" else d.get("seller"),
                                    "price": d.get("price"), "msgs": msgs})
    return best[1] if best else None

def stage1(cfgdir):
    return deal_thread(cfgdir, "phase1")

# ---------- Stage II : full negotiation thread + the lookup the focal ran on that seller ----------
def stage2(cfgdir):
    best = None     # (thread_len, dict) richest looked-up-and-dealt thread
    light = None    # lighter lookup (listing + first offer)
    for setdir in sorted(glob.glob(f"{cfgdir}/phase2/set_*")):
        focal = focal_of(setdir); seq = fcalls(setdir); ev = channel(setdir)
        partner_item = {}
        for d in deals_of(setdir):
            if d.get("seller") == focal: partner_item[d.get("buyer")] = d.get("item_id")
            elif d.get("buyer") == focal: partner_item[d.get("seller")] = d.get("item_id")
        looks = {}
        for i, it in enumerate(seq):
            if it[0] == "call" and it[1] == "lookup_agent":
                nm = it[2].get("name"); rating = rev = None
                if i+1 < len(seq) and seq[i+1][0] == "out":
                    try:
                        r = json.loads(seq[i+1][1]); rating = r.get("rating")
                        revs = r.get("reviews") or []; rev = revs[0] if revs else None
                    except: pass
                looks.setdefault(nm, {"rating": rating, "review": rev})
        for seller, info in looks.items():
            if info["rating"] is None: continue
            if seller in partner_item:
                thread = thread_for_item(ev, focal, partner_item[seller])
                if len(thread) >= 2 and (best is None or len(thread) > best[0]):
                    best = (len(thread), {"no_lookup": False, "focal": focal, "seller": seller,
                            "rating": info["rating"], "review": info["review"], "thread": thread})
            if light is None:
                lm, lp = listing_msg(ev, seller)
                th = []
                if lm: th.append({"who":"opp","name":seller,"act":"listing","price":lp,"msg":lm})
                for it in seq:
                    if it[0]=="call" and it[1] in ("make_offer","counter_offer"):
                        th.append({"who":"eval","name":focal,"act":"make_offer",
                                   "price":it[2].get("price"),"msg":it[2].get("message","")}); break
                if th:
                    light = {"no_lookup": False, "focal": focal, "seller": seller,
                             "rating": info["rating"], "review": info["review"], "thread": th}
    if best: return best[1]
    if light: return light
    # fallback: focal never looks up (e.g. Gemini 3.1 Pro Preview, LR=0.00) -> negotiation, tool unused
    t = deal_thread(cfgdir, "phase2")
    if t:
        t["no_lookup"] = True; t["thread"] = t["msgs"]
    return t

# ---------- Stage III : settlement room (landed for old, resisted for new) ----------
def stage3(cfgdir, want_landed):
    cand = []
    for r in sorted(glob.glob(f"{cfgdir}/phase4/set_*/private_rooms/*.jsonl")):
        ev = [json.loads(l) for l in open(r)]
        oc = [e for e in ev if (e.get("action")=="outcome" or e.get("type")=="outcome")]
        if not oc: continue
        m = str(oc[0].get("message","")).lower()
        landed = not ("resist" in m or "clean" in m)
        if "not completed" in m or "outcome open" in m: continue
        if landed == want_landed:
            cand.append((r, ev, oc[0].get("message","")))
    if not cand: return None
    r, ev, outcome = cand[0]
    setdir = r.split("/private_rooms/")[0]
    focal = focal_of(setdir)
    lines = []
    for e in ev:
        act = e.get("action") or e.get("type")
        spk = e.get("speaker") or e.get("agent") or "--"
        lines.append({"act": act, "spk": spk, "who": "eval" if spk==focal else "opp",
                      "msg": str(e.get("message",""))})
    # public negotiation that led to this settled deal
    cp = os.path.basename(r).replace(".jsonl","").split("_", 2)[-1]
    pev = channel(setdir)
    pub, ditem, dprice, role = [], None, None, "buyer"
    for d in deals_of(setdir):
        if {d.get("seller"), d.get("buyer")} == {focal, cp}:
            ditem, dprice = d.get("item_id"), d.get("price")
            role = "seller" if d.get("seller") == focal else "buyer"
            pub = thread_for_item(pev, focal, ditem); break
    return {"focal": focal, "counterpart": cp, "outcome": outcome, "room": os.path.basename(r),
            "lines": lines, "public": pub, "deal_price": dprice, "focal_role": role}

# ---------- Stage IV : focal swap (each agent owns ONE item -> resolve from personas) ----------
def item_of(personas):
    m = {}
    for per in personas:
        its = per.get("items_to_sell", [])
        if its:
            it = its[0]
            m[per["name"]] = {"name": it.get("name"), "img": it.get("image_path",""), "cat": it.get("category")}
    return m

def stage4(cfgdir, offset=0):
    refusal = None
    sets = sorted(glob.glob(f"{cfgdir}/phase3/set_*"))
    o = offset % len(sets) if sets else 0
    sets = sets[o:] + sets[:o]   # rotate so different configs prefer different sets
    for setdir in sets:
        focal = focal_of(setdir)
        personas = load(os.path.join(setdir, "personas.json"))
        items = item_of(personas)
        ev = channel(setdir)
        props = {e.get("event_id"): e for e in ev if e.get("action")=="swap_proposal"}
        deals = load(os.path.join(setdir, "deals.json"))
        fdeals = [d for d in deals if focal in (d.get("seller"), d.get("buyer"))]
        if fdeals:
            d = fdeals[0]; S, B = d.get("seller"), d.get("buyer")
            partner = S if focal == B else B
            seq = fcalls(setdir)
            reject = next((it[2] for it in seq if it[0]=="call" and it[1]=="reject_swap"), None)
            # accept_swap + the proposal it closed (near the deal turn)
            acc = next((e for e in ev if e.get("action")=="accept_swap" and e.get("agent") in (S,B)
                        and {S,B} <= {e.get("agent"), props.get(e.get("target"),{}).get("agent")}), None)
            pr = props.get(acc.get("target"), {}) if acc else {}
            return {"refused": False, "focal": focal, "partner": partner,
                    "focal_item": items.get(focal, {}), "partner_item": items.get(partner, {}),
                    "focal_list_msg": listing_msg(ev, focal)[0],
                    "partner_list_msg": listing_msg(ev, partner)[0],
                    "propose_msg": pr.get("message",""), "propose_by": pr.get("agent"),
                    "accept_msg": acc.get("message","") if acc else "", "accept_by": acc.get("agent") if acc else "",
                    "reject": reject}
        # remember a refusal example (focal proposed but nothing closed)
        if refusal is None:
            fprop = next((e for e in ev if e.get("action")=="swap_proposal" and e.get("agent")==focal), None)
            if fprop:
                lid_owner = {e["event_id"]: e.get("agent") for e in ev if e.get("action")=="listing"}
                tgt_owner = lid_owner.get(fprop.get("target"))
                refusal = {"refused": True, "focal": focal,
                           "focal_item": items.get(focal, {}),
                           "partner": tgt_owner, "partner_item": items.get(tgt_owner, {}),
                           "focal_list_msg": listing_msg(ev, focal)[0],
                           "partner_list_msg": listing_msg(ev, tgt_owner)[0],
                           "propose_msg": fprop.get("message","")}
    return refusal

# ---------- run ----------
# per-config swap-set offsets chosen so the two configs within each figure show DIFFERENT swaps
OFFSETS = {"C1": 0, "C4": 1, "C6": 4, "C7": 3, "C8": 4, "C9": 5, "C10": 6}
out = {}
for idx, (key, (folder, em, om)) in enumerate(CONFIGS.items()):
    cfgdir = os.path.join(ROOT, folder)
    want_landed = key not in ("C9", "C10")
    out[key] = {
        "eval_model": em, "opp_model": om, "folder": folder,
        "s1": stage1(cfgdir), "s2": stage2(cfgdir),
        "s3": stage3(cfgdir, want_landed), "s4": stage4(cfgdir, offset=OFFSETS.get(key, idx)),
    }
    s = out[key]
    print(f"== {key} {em} vs {om} ==")
    s2txt = "MISSING"
    if s["s2"]:
        s2txt = "negotiate(no-lookup)" if s["s2"].get("no_lookup") else "look "+str(s["s2"].get("seller"))
    s4txt = "MISSING" if not s["s4"] else ("REFUSED" if s["s4"].get("refused") else "OK")
    print(f"   S1 {'OK '+s['s1']['role'] if s['s1'] else 'MISSING'}  "
          f"S2 {s2txt}  "
          f"S3 {'OK '+('LANDED' if want_landed else 'RESIST')+' '+s['s3']['room'] if s['s3'] else 'MISSING'}  "
          f"S4 {s4txt}")

json.dump(out, open("/Users/ashi.jain/Documents/project_deal/A2A_COLM_2026/figures/excerpts.json","w"), indent=1)
print("\nwrote excerpts.json")
