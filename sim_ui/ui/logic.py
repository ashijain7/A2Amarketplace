"""
Cached-episode loader for the Agent-to-Agent Marketplace sim UI.

Reads the paper-run rollouts (results/paper_runs/<config>/phase{1-4}/rollouts.jsonl),
classifies each rollout's true mode by content (NOT the scrambled folder name),
regroups the shared channel into per-focal-deal threads, and returns a structured
Episode the renderer/replay can consume. Pure stdlib — no engine dependency, $0.

The single source of truth for "what a cached run contains" lives here so the
Gradio dashboard, the (future) live path, and tests all agree.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---- anchors --------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]          # project_deal/
PAPER_RUNS = ROOT / "results" / "paper_runs"

# ---- model naming ---------------------------------------------------------
# config names look like  focal_<F>_vs_<O>  e.g. focal_X_vs_O48, focal_G35_vs_X
_TOKEN_MODEL = {
    "S": "Sonnet 4.5", "H": "Haiku 4.5", "O": "Opus 4.7", "O48": "Opus 4.8",
    "G": "Gemini 3.1 Pro", "G35": "Gemini 3.5 Flash", "X": "GPT-5.5",
}

# the four UI stages, in order
MODES = ["market", "review", "transaction", "swap"]
MODE_LABEL = {"market": "MarketDeal", "review": "Review",
              "transaction": "Transaction", "swap": "SwapShop"}
MODE_STAGE = {"market": "MarketDeal · Stage I", "review": "Review · Stage II",
              "transaction": "Transaction · Stage III", "swap": "SwapShop · Stage IV"}
MODE_TITLE = {"market": "Basic trading", "review": "Review-assisted",
              "transaction": "Payment under a scammer", "swap": "Item-for-item barter"}


def models_for(config: str) -> tuple[str, str]:
    """(evaluated_model, opponent_model) readable names from a config slug."""
    m = re.match(r"focal_(.+)_vs_(.+)", config or "")
    if not m:
        return (config or "?", config or "?")
    f, o = m.group(1), m.group(2)
    return (_TOKEN_MODEL.get(f, f), _TOKEN_MODEL.get(o, o))


# ---- mode classification (folder names are scrambled — classify by content) --
def classify_mode(rollout: dict) -> str:
    if rollout.get("settlement_records"):
        return "transaction"
    phase = str((rollout.get("metadata") or {}).get("phase"))
    if phase == "3":
        return "swap"
    if phase == "2":
        return "review"
    return "market"


# ---- data model -----------------------------------------------------------
@dataclass
class Turn:
    agent: str
    action: str
    price: Optional[float]
    message: str
    img_uri: Optional[str] = None     # data-URI of the item photo (swap turns only)


@dataclass
class RoomLine:
    speaker: str
    text: str
    is_scammer: bool = False


@dataclass
class Deal:
    seller: str
    buyer: str
    item_id: str
    price: float                      # -1.0 for a swap
    thread: list[Turn] = field(default_factory=list)
    room: list[RoomLine] = field(default_factory=list)   # transaction settlement room
    settlement: Optional[dict] = None                    # scam_tactic / paid_wrong_owner / released_unpaid

    @property
    def is_swap(self) -> bool:
        return self.price == -1.0


@dataclass
class Episode:
    mode: str
    config: str
    set_id: str
    focal: str
    focal_model: str
    opponent_model: str
    reward: float
    rubrics: dict[str, float]
    deals: list[Deal] = field(default_factory=list)
    attempts: list[Deal] = field(default_factory=list)   # focal's failed negotiations (no-deal view)
    passes: list[Turn] = field(default_factory=list)     # focal only watched/passed (no listing or offer)


# ---- thread reconstruction -----------------------------------------------
def _listing_event(channel: list[dict], item_id: str) -> Optional[dict]:
    return next((e for e in channel
                 if e.get("action") in ("listing", "post_listing") and e.get("target") == item_id), None)


def _build_thread(rollout: dict, deal: dict, swap: bool) -> list[Turn]:
    """Reconstruct ONE deal's coherent two-party thread from the shared channel.

    A listing can draw several buyers, and the seller's counters all target the
    listing (not a specific offer) — so we can't just take "every event by the two
    parties". Instead we walk the listing's negotiation in turn order, track which
    buyer the seller is currently talking to (= the last non-seller to act), and
    keep a seller counter ONLY while that buyer is *this* deal's buyer. This drops
    the seller's replies to other buyers (which is what produced orphaned messages)
    while preserving full multi-round back-and-forth for the real counterparty.
    The winning offer + closing accept come from the accept's own target chain.
    """
    channel = rollout.get("channel_events", [])
    seller, buyer, item = deal["seller"], deal["buyer"], deal["item_id"]
    price = deal.get("price")
    listing = _listing_event(channel, item)
    lid = listing.get("event_id") if listing else None

    by_id = {e.get("event_id"): e for e in channel}

    def _accept_on_listing(a):
        # the accept references the offer/counter it accepted; that event should be on THIS listing
        ref = by_id.get(a.get("target"))
        return ref is not None and (ref.get("target") in (item, lid) or ref.get("event_id") == lid)

    if swap:
        cands = [e for e in channel if e.get("action") == "accept_swap" and e.get("agent") in (seller, buyer)]
    else:
        cands = [e for e in channel if e.get("action") == "accept"
                 and e.get("agent") in (seller, buyer) and e.get("price") == price]
    on_this = [e for e in cands if _accept_on_listing(e)]     # prefer accepts whose offer is on THIS listing
    pool = on_this or cands
    pool.sort(key=lambda e: abs((e.get("turn") or 0) - (deal.get("turn") or 0)))
    accept = pool[0] if pool else None
    # coherence guard: you accept the OTHER party's offer, never your own. If the
    # source rollout mislinked it (accept references its own author's event), drop
    # the accept bubble — the outcome banner (from the deal record) still shows the close.
    if accept is not None:
        ref = by_id.get(accept.get("target"))
        if ref is not None and ref.get("agent") == accept.get("agent"):
            accept = None
    accept_turn = accept.get("turn") if accept else 10 ** 9

    body = _two_party_events(channel, seller, buyer, item, lid, _NEG[swap], accept_turn)
    picked = ([listing] if listing else []) + body + ([accept] if accept else [])
    return _events_to_turns(picked)


_NEG = {False: ("offer", "counter"), True: ("propose_swap", "swap_proposal")}


def _two_party_events(channel, seller, buyer, item, lid, actions, upto_turn):
    """Walk a listing's negotiation in turn order and keep ONLY the seller<->buyer
    exchange: the buyer's events, plus the seller's events while its current
    counterparty (last non-seller to act) is this buyer. Drops the seller's replies
    to other buyers on the same listing (which was the orphaned-message bug)."""
    on_listing = sorted((e for e in channel if e.get("target") in (item, lid) and e.get("action") in actions),
                        key=lambda e: e.get("turn") or 0)
    picked, current_buyer = [], None
    for e in on_listing:
        if (e.get("turn") or 0) > upto_turn:
            break
        a = e.get("agent")
        if a == seller:
            if current_buyer == buyer:
                picked.append(e)
        elif a == buyer:
            picked.append(e)
            current_buyer = buyer
        else:
            current_buyer = a
    return picked


def _events_to_turns(events) -> list[Turn]:
    out, seen = [], set()
    for e in sorted(events, key=lambda e: e.get("turn") or 0):
        eid = e.get("event_id")
        if eid in seen:
            continue
        seen.add(eid)
        out.append(Turn(agent=e.get("agent"), action=e.get("action"),
                        price=e.get("price"), message=e.get("message", "")))
    return out


def _focal_attempts(rollout: dict, focal: str, swap: bool) -> list["Deal"]:
    """The focal's negotiations that did NOT close, reconstructed two-sided (the
    opponent's offers/counters included) — powers the 'no deal closed' view."""
    channel = rollout.get("channel_events", [])
    neg = _NEG[swap]
    actions = neg + ("decline", "reject", "reject_swap")
    out, seen = [], set()

    # focal as SELLER — ALWAYS surface the focal's own listings (even with no offers)
    for L in (e for e in channel if e.get("action") in ("listing", "post_listing") and e.get("agent") == focal):
        item, lid = L.get("target"), L.get("event_id")
        buyers = list(dict.fromkeys(e.get("agent") for e in channel
                      if e.get("target") in (item, lid) and e.get("action") in neg and e.get("agent") != focal))
        if buyers:
            for b in buyers:
                key = (focal, b, item)
                if key in seen:
                    continue
                seen.add(key)
                turns = _events_to_turns([L] + _two_party_events(channel, focal, b, item, lid, actions, 10 ** 9))
                if len(turns) >= 2 and any(t.agent != focal for t in turns):
                    out.append(Deal(seller=focal, buyer=b, item_id=item, price=0.0, thread=turns))
        else:                                              # listed, but nobody engaged
            key = (focal, "", item)
            if key not in seen:
                seen.add(key)
                out.append(Deal(seller=focal, buyer="", item_id=item, price=0.0, thread=_events_to_turns([L])))

    # focal as BUYER — listings by others it offered on
    for e in channel:
        if e.get("agent") == focal and e.get("action") in neg:
            L = next((x for x in channel if x.get("event_id") == e.get("target")
                      and x.get("action") in ("listing", "post_listing")), None) or _listing_event(channel, e.get("target"))
            if L and L.get("agent") != focal:
                s, item, lid = L.get("agent"), L.get("target"), L.get("event_id")
                key = (s, focal, item)
                if key in seen:
                    continue
                seen.add(key)
                turns = _events_to_turns([L] + _two_party_events(channel, s, focal, item, lid, actions, 10 ** 9))
                if len(turns) >= 2 and any(t.agent == focal for t in turns):
                    out.append(Deal(seller=s, buyer=focal, item_id=item, price=0.0, thread=turns))

    out.sort(key=lambda d: (0 if d.seller == focal else 1, -len(d.thread)))   # own listings first
    return out[:5]


def _settlement_for(rollout: dict, deal_id: str) -> Optional[dict]:
    return next((s for s in (rollout.get("settlement_records") or []) if s.get("deal_id") == deal_id), None)


def _room_lines(sr: dict) -> list[RoomLine]:
    return [RoomLine(speaker=x.get("speaker"), text=x.get("text", ""), is_scammer=bool(x.get("is_scammer")))
            for x in (sr.get("room") or [])]


# swap photos: resolve each party's item image (DeepFashion) to a small data URI.
_IMG_CACHE: dict[str, Optional[str]] = {}


def _image_data_uri(rel_path: Optional[str]) -> Optional[str]:
    if not rel_path:
        return None
    if rel_path in _IMG_CACHE:
        return _IMG_CACHE[rel_path]
    path = ROOT / rel_path
    uri = None
    if path.exists():
        try:
            import base64
            import io
            from PIL import Image
            im = Image.open(path).convert("RGB")
            im.thumbnail((240, 300))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=72)
            uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            uri = None
    _IMG_CACHE[rel_path] = uri
    return uri


def _persona(rollout: dict, name: str) -> dict:
    return next((p for p in rollout.get("personas", []) if p.get("name") == name), {})


def _item_image(rollout: dict, persona_name: str, item_id: Optional[str]) -> Optional[str]:
    """Image for a persona's item (by id, else the first item that has one)."""
    items = _persona(rollout, persona_name).get("items_to_sell", [])
    it = next((x for x in items if x.get("item_id") == item_id), None)
    if it is None:
        it = next((x for x in items if x.get("image_path")), None)
    return _image_data_uri((it or {}).get("image_path"))


def _resolve_swap_images(rollout: dict, deal: Deal):
    for t in deal.thread:
        if t.action in ("listing", "post_listing"):
            t.img_uri = _item_image(rollout, deal.seller, deal.item_id)
        elif t.action in ("swap_proposal", "propose_swap"):
            t.img_uri = _item_image(rollout, deal.buyer, None)


def _rollout_to_episode(rollout: dict) -> Episode:
    meta = rollout.get("metadata") or {}
    mode = classify_mode(rollout)
    swap = (mode == "swap")
    focal = meta.get("focal_persona")
    config = meta.get("config_name") or ""
    fm, om = models_for(config)

    # keep only rubrics that actually scored (a None "combined" was renormalized out).
    rubrics = {k: v["combined"] for k, v in (rollout.get("rubric_scores") or {}).items()
               if isinstance(v, dict) and v.get("combined") is not None and k != "final_reward"}

    def is_focal_deal(d):
        if focal not in (d.get("seller"), d.get("buyer")):
            return False
        return d.get("price") == -1.0 if swap else (d.get("price", 0) or 0) > 0

    deals: list[Deal] = []
    for d in rollout.get("deals", []):
        if not is_focal_deal(d):
            continue
        deal = Deal(seller=d["seller"], buyer=d["buyer"], item_id=d["item_id"],
                    price=d.get("price", 0.0) if not swap else -1.0,
                    thread=_build_thread(rollout, d, swap))
        sr = _settlement_for(rollout, d.get("deal_id"))
        if sr:
            deal.settlement = {k: sr.get(k) for k in
                               ("scam_tactic", "paid_wrong_owner", "released_unpaid")}
            deal.room = _room_lines(sr)
        if swap:
            _resolve_swap_images(rollout, deal)
        deals.append(deal)

    # no deal closed? rebuild the focal's failed negotiations two-sided
    attempts = _focal_attempts(rollout, focal, swap) if not deals else []
    if swap:
        for a in attempts:                       # swap attempts need item photos too
            _resolve_swap_images(rollout, a)

    # focal never listed/offered — it only passed. Capture a few passes so the view
    # shows it deliberately sat out (not a bug / empty screen).
    passes: list[Turn] = []
    if not deals and not attempts:
        pz = [e for e in rollout.get("channel_events", [])
              if e.get("agent") == focal and e.get("action") == "pass"]
        passes = [Turn(agent=e.get("agent"), action="pass", price=None, message=e.get("message", ""))
                  for e in pz[:4]]

    return Episode(mode=mode, config=config, set_id=meta.get("set_id"),
                   focal=focal, focal_model=fm, opponent_model=om,
                   reward=rollout.get("reward", 0.0), rubrics=rubrics, deals=deals,
                   attempts=attempts, passes=passes)


# ---- serialize an Episode to the frontend JSON shape ----------------------
# (the shape web/app.js consumes: camelCase keys, room lines use `scam`, turns
#  use `img`. This is the single exporter — used by both the episodes.json build
#  and the live path's end-of-run render.)
def _turn_json(t: Turn) -> dict:
    return {"agent": t.agent, "action": t.action, "price": t.price,
            "message": t.message, "img": t.img_uri}


def _deal_json(d: Deal) -> dict:
    return {"seller": d.seller, "buyer": d.buyer, "item_id": d.item_id, "price": d.price,
            "thread": [_turn_json(t) for t in d.thread],
            "room": [{"speaker": r.speaker, "text": r.text, "scam": r.is_scammer} for r in d.room],
            "settlement": d.settlement}


def episode_to_frontend(ep: Episode, focal_model: Optional[str] = None,
                        opponent_model: Optional[str] = None) -> dict:
    """Episode dataclass -> the exact dict web/app.js renders. focal_model /
    opponent_model override the config-derived names (the live path passes the
    real chosen models, since its task uses the canonical focal_S_vs_S config)."""
    return {
        "stage": MODE_STAGE.get(ep.mode, ep.mode),
        "title": MODE_TITLE.get(ep.mode, ep.mode),
        "config": ep.config,
        "set": ep.set_id,
        "focal": ep.focal,
        "focalModel": focal_model or ep.focal_model,
        "oppModel": opponent_model or ep.opponent_model,
        "reward": ep.reward,
        "rubrics": ep.rubrics,
        "deals": [_deal_json(d) for d in ep.deals],
        "attempts": [_deal_json(d) for d in ep.attempts],
        "passes": [_turn_json(t) for t in ep.passes],
    }


def rollout_line_to_frontend(rollout: dict, focal_model: Optional[str] = None,
                             opponent_model: Optional[str] = None) -> dict:
    """One raw rollout dict -> frontend episode dict (reconstruct + serialize)."""
    return episode_to_frontend(_rollout_to_episode(rollout), focal_model, opponent_model)


# ---- catalog --------------------------------------------------------------
@dataclass
class CatalogEntry:
    mode: str
    config: str
    set_id: str
    file: str
    line: int


def build_catalog() -> list[CatalogEntry]:
    """Scan every paper-run rollout once and index it by (mode, config, set)."""
    entries: list[CatalogEntry] = []
    for f in sorted(PAPER_RUNS.glob("*/phase*/rollouts.jsonl")):
        for i, line in enumerate(f.open()):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            meta = r.get("metadata") or {}
            entries.append(CatalogEntry(
                mode=classify_mode(r), config=meta.get("config_name") or "",
                set_id=meta.get("set_id") or "", file=str(f), line=i))
    return entries


def load_episode(entry: CatalogEntry) -> Episode:
    with open(entry.file) as fh:
        for i, line in enumerate(fh):
            if i == entry.line:
                return _rollout_to_episode(json.loads(line))
    raise IndexError(f"line {entry.line} not found in {entry.file}")


# ---- convenience for the dropdowns ---------------------------------------
class Catalog:
    """Query helper over the scanned entries — powers the UI dropdowns."""
    def __init__(self):
        self.entries = build_catalog()

    def modes(self) -> list[str]:
        present = {e.mode for e in self.entries}
        return [m for m in MODES if m in present]

    def configs(self, mode: str) -> list[str]:
        return sorted({e.config for e in self.entries if e.mode == mode})

    def sets(self, mode: str, config: str) -> list[str]:
        return sorted({e.set_id for e in self.entries if e.mode == mode and e.config == config})

    def find(self, mode: str, config: str, set_id: str) -> Optional[CatalogEntry]:
        return next((e for e in self.entries
                     if e.mode == mode and e.config == config and e.set_id == set_id), None)


if __name__ == "__main__":
    cat = Catalog()
    print(f"catalog: {len(cat.entries)} rollouts")
    for m in cat.modes():
        cfgs = cat.configs(m)
        print(f"  {MODE_LABEL[m]:12s}: {len(cfgs)} configs, "
              f"{sum(len(cat.sets(m,c)) for c in cfgs)} (config×set) runs")
    # sample load
    e = cat.find("market", cat.configs("market")[0], cat.sets("market", cat.configs("market")[0])[0])
    ep = load_episode(e)
    print(f"\nsample: {ep.mode} {ep.config} {ep.set_id} focal={ep.focal} "
          f"({ep.focal_model} vs {ep.opponent_model}) reward={ep.reward:.3f} deals={len(ep.deals)}")
    for i, d in enumerate(ep.deals):
        role = "SELL" if d.seller == ep.focal else "BUY"
        print(f"   deal{i+1} [{role}] {d.seller}->{d.buyer} {d.item_id} "
              f"${d.price} turns={len(d.thread)} room={'Y' if d.room else '-'}")
