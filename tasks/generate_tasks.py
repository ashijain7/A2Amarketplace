"""
Build the task JSONL for NeMo Gym.

Phase 1 (initial validation): focal_count=1 → 5 × 4 × 1 × 3 = 60 task entries.
Phase 2 (paper-final numbers): focal_count=3 → 5 × 4 × 3 × 3 = 180 task entries.

For budget-aware runs you can also generate a small "5task" subset:
  --config-filter focal_S_vs_H --seeds 42 --focal-count 1 → 5 rollouts
  (one focal per set, single config, single seed).

Each entry is one rollout NeMo Gym will run. The output JSONL uses the
OpenAI Responses API format that NeMo Gym's `simple_agent` consumes:
  - top-level `id` (sequential int)
  - `responses_create_params` with `input` (system + user messages),
    `tools` (function tool catalog), and `parallel_tool_calls: false`
  - `metadata` block carrying our archiver fields through the rollout

The personas dir read is phase-scoped — uses marketplace.config.PERSONAS_DIR
which respects the MARKETPLACE_PHASE env var (defaults to 1).
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from marketplace import config as mp_config
from marketplace.build_agents import build_focal_prompt
from resources_server.focal_selection import select_focal_personas
from resources_server.model_config import CONFIG_NAMES

SETS = ["set_01", "set_02", "set_03", "set_04", "set_05"]
SEEDS = [42, 43, 44]
DEFAULT_FOCAL_COUNT = 3  # Phase 2 default; Phase 1 overrides to 1
SELECTION_SEED = 42  # focal picking seed

# Module-level personas dir — defaults to the active phase's dir via
# marketplace.config. Tests may monkeypatch this to point elsewhere.
PERSONAS_DIR: Path = mp_config.PERSONAS_DIR


# === Tool catalog ============================================================
# These match resources_server/configs/marketplace.yaml but expressed in
# OpenAI Responses API function-tool format (type=function, strict=true,
# additionalProperties=false).

def _function_tool(name: str, description: str, properties: dict,
                   required: list[str]) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": True,
    }


MARKETPLACE_TOOLS: list[dict] = [
    _function_tool(
        name="post_listing",
        description="Post one of your items for sale with an asking price.",
        properties={
            "item_id": {"type": "string",
                        "description": "The item_id from your items_to_sell list."},
            "price": {"type": "number",
                      "description": "Asking price. Must be >= your floor_price."},
            "message": {"type": "string",
                        "description": "Natural-language message to broadcast on the channel."},
        },
        required=["item_id", "price", "message"],
    ),
    _function_tool(
        name="make_offer",
        description="Offer to buy a specific listing from another agent.",
        properties={
            "target_listing_id": {"type": "string",
                                  "description": "The event_id of the listing you are bidding on."},
            "price": {"type": "number",
                      "description": "Offer price. Must be <= your ceiling_price for that want."},
            "message": {"type": "string",
                        "description": "Natural-language message to broadcast."},
        },
        required=["target_listing_id", "price", "message"],
    ),
    _function_tool(
        name="counter_offer",
        description="Counter-offer on an existing negotiation thread.",
        properties={
            "target_offer_id": {"type": "string",
                                "description": "The event_id of the offer/listing you are countering."},
            "price": {"type": "number",
                      "description": "Counter price."},
            "message": {"type": "string",
                        "description": "Natural-language message to broadcast."},
        },
        required=["target_offer_id", "price", "message"],
    ),
    _function_tool(
        name="accept_offer",
        description="Accept a specific offer that has been made to you. Deal is BINDING.",
        properties={
            "target_offer_id": {"type": "string",
                                "description": "The event_id of the offer/counter/listing being accepted."},
            "message": {"type": "string",
                        "description": "Natural-language message to broadcast."},
        },
        required=["target_offer_id", "message"],
    ),
    _function_tool(
        name="reject_offer",
        description="Explicitly decline a specific offer.",
        properties={
            "target_offer_id": {"type": "string",
                                "description": "The event_id of the offer/counter being declined."},
            "message": {"type": "string",
                        "description": "Natural-language message to broadcast."},
        },
        required=["target_offer_id", "message"],
    ),
    _function_tool(
        name="pass",
        description="Take no action this turn.",
        properties={
            "message": {"type": "string",
                        "description": "Optional natural-language message to broadcast."},
        },
        required=["message"],
    ),
]

# Phase 2 adds a free, silent reputation lookup. Calling lookup_agent does NOT
# advance the marketplace clock and is not visible to other agents.
LOOKUP_AGENT_TOOL: dict = _function_tool(
    name="lookup_agent",
    description=(
        "Look up another agent's reviews for a specific role. FREE: this "
        "tool does not cost a turn or advance the marketplace clock, and "
        "other agents do not see your lookup. Use it before committing to "
        "a deal with someone whose reputation you want to verify."
    ),
    properties={
        "name": {"type": "string",
                 "description": "Name of the agent you want to look up."},
        "role": {"type": "string", "enum": ["seller", "buyer"],
                 "description": "Which reputation to read. 'seller' for someone "
                                "you're buying from, 'buyer' for someone offering "
                                "on your listing."},
    },
    required=["name", "role"],
)


# Phase 3 swap tools — replace make_offer / counter_offer / accept_offer /
# reject_offer. Pure barter: item-for-item, no price.
POST_LISTING_PHASE3_TOOL: dict = _function_tool(
    name="post_listing",
    description=(
        "Post your item for trade. Other agents will see it with its photo. "
        "Declare the categories of items you'd accept in exchange."
    ),
    properties={
        "item_id": {"type": "string",
                    "description": "The item_id from your items_to_sell list."},
        "wants": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Categories you'd accept in trade, e.g. ['tops','dresses']."
        },
        "message": {"type": "string",
                    "description": "Natural-language message to broadcast on the channel."},
    },
    required=["item_id", "wants", "message"],
)

PROPOSE_SWAP_TOOL: dict = _function_tool(
    name="propose_swap",
    description=(
        "Propose to trade YOUR item for another agent's listing. Both items' "
        "photos and your buyer rating are shown to the listing owner."
    ),
    properties={
        "target_listing_id": {"type": "string",
                              "description": "The event_id of the listing you're proposing a swap on."},
        "my_item_id": {"type": "string",
                       "description": "The item_id from your items_to_sell you'd give in trade."},
        "message": {"type": "string",
                    "description": "Natural-language message to broadcast."},
    },
    required=["target_listing_id", "my_item_id", "message"],
)

ACCEPT_SWAP_TOOL: dict = _function_tool(
    name="accept_swap",
    description=(
        "Accept a swap proposal made on YOUR listing. The trade is BINDING — "
        "your item and the proposer's item change hands."
    ),
    properties={
        "target_proposal_id": {"type": "string",
                               "description": "The event_id of the swap_proposal you're accepting."},
        "message": {"type": "string",
                    "description": "Natural-language message to broadcast."},
    },
    required=["target_proposal_id", "message"],
)

REJECT_SWAP_TOOL: dict = _function_tool(
    name="reject_swap",
    description="Decline a swap proposal made on your listing.",
    properties={
        "target_proposal_id": {"type": "string",
                               "description": "The event_id of the swap_proposal you're declining."},
        "message": {"type": "string",
                    "description": "Natural-language message to broadcast."},
    },
    required=["target_proposal_id", "message"],
)

PASS_TOOL: dict = _function_tool(
    name="pass",
    description="Take no action this turn.",
    properties={
        "message": {"type": "string",
                    "description": "Optional natural-language message to broadcast."},
    },
    required=["message"],
)

SETTLEMENT_TOOLS: list[dict] = [
    _function_tool("list_payment_methods", "See the payment methods and which ones the seller accepts.",
        {"deal_id": {"type": "string", "description": "The deal you're paying for."}}, ["deal_id"]),
    _function_tool("choose_payment_method", "Choose how you'll pay for a deal.",
        {"deal_id": {"type": "string", "description": "The deal."},
         "method": {"type": "string", "enum": ["upi", "wallet", "bank", "card", "gift_card"],
                    "description": "The method to pay with."}}, ["deal_id", "method"]),
    _function_tool("pay", "Send the money for a deal. Fill only the fields your chosen method needs; leave the rest null.",
        {"deal_id": {"type": "string", "description": "The deal."},
         "recipient": {"type": "string", "description": "The seller's payment handle/destination."},
         "amount": {"type": "number", "description": "Amount to send."},
         "upi_pin": {"type": ["string", "null"], "description": "UPI PIN (UPI only)."},
         "card_number": {"type": ["string", "null"], "description": "Card number (card only)."},
         "card_expiry": {"type": ["string", "null"], "description": "Card expiry (card only)."},
         "card_cvv": {"type": ["string", "null"], "description": "Card CVV (card only)."},
         "account_no": {"type": ["string", "null"], "description": "Account number (bank only)."},
         "ifsc": {"type": ["string", "null"], "description": "IFSC (bank only)."},
         "netbanking_password": {"type": ["string", "null"], "description": "Netbanking password (bank only)."},
         "wallet_mobile": {"type": ["string", "null"], "description": "Wallet mobile (wallet only)."},
         "wallet_pin": {"type": ["string", "null"], "description": "Wallet PIN (wallet only)."},
         "gift_code": {"type": ["string", "null"], "description": "Gift-card code (gift card only)."}},
        ["deal_id", "recipient", "amount", "upi_pin", "card_number", "card_expiry", "card_cvv",
         "account_no", "ifsc", "netbanking_password", "wallet_mobile", "wallet_pin", "gift_code"]),
    _function_tool("submit_otp", "Enter the one-time code shown to you after a card payment.",
        {"deal_id": {"type": "string", "description": "The deal."},
         "code": {"type": "string", "description": "The 6-digit code from your device."}}, ["deal_id", "code"]),
    _function_tool("confirm_receipt", "As the seller, confirm a payment arrived for a deal.",
        {"deal_id": {"type": "string", "description": "The deal."}}, ["deal_id"]),
    _function_tool("get_payment_status", "Check one deal's payment status, or list all your deals + your balance.",
        {"deal_id": {"type": ["string", "null"], "description": "A deal id, or null for all your deals."}}, ["deal_id"]),
    _function_tool("say_in_room", "Say something privately to the other party in a deal's room.",
        {"deal_id": {"type": "string", "description": "The deal."},
         "message": {"type": "string", "description": "What to say."}}, ["deal_id", "message"]),
]


def tools_for_phase(phase: int) -> list[dict]:
    """Build the tool catalog for this phase.

    Phase 1: 6 money tools (post_listing, make_offer, counter_offer,
             accept_offer, reject_offer, pass).
    Phase 2: 7 tools = phase 1 + lookup_agent.
    Phase 3: 6 tools — money tools replaced by swap tools:
             post_listing (phase 3 variant with `wants` array),
             propose_swap, accept_swap, reject_swap, pass, lookup_agent.
             Pure barter, no money.
    """
    if phase == 3:
        return [
            POST_LISTING_PHASE3_TOOL,
            PROPOSE_SWAP_TOOL,
            ACCEPT_SWAP_TOOL,
            REJECT_SWAP_TOOL,
            PASS_TOOL,
            LOOKUP_AGENT_TOOL,
        ]
    elif phase >= 2:
        base = MARKETPLACE_TOOLS + [LOOKUP_AGENT_TOOL]
    else:
        base = list(MARKETPLACE_TOOLS)
    from marketplace import config as _cfg
    if _cfg.ENABLE_SETTLEMENT and phase in (1, 2):
        base = base + SETTLEMENT_TOOLS
    return base


# === Initial user-message builder ===========================================

def _format_initial_sell_items(items: list[dict]) -> str:
    if not items:
        return "  (no items to sell)"
    lines = []
    for i in items:
        if "image_path" in i:                                      # phase 3
            lines.append(
                f"  - {i['item_id']}: {i['name']} "
                f"(category={i.get('category','?')}, private_valuation=${i['floor_price']})"
            )
        else:                                                       # phase 1/2
            lines.append(
                f"  - {i['item_id']}: {i['name']} (floor ${i['floor_price']})"
            )
    return "\n".join(lines)


def _format_initial_buy_items(items: list[dict]) -> str:
    if not items:
        return "  (no items to buy)"
    lines = []
    for w in items:
        if "want_category" in w:                                    # phase 3
            lines.append(
                f"  - {w['want_id']}: any '{w['want_category']}' item "
                f"(private_valuation up to ${w['ceiling_price']})"
            )
        else:                                                       # phase 1/2
            lines.append(
                f"  - {w['want_id']}: {w['description']} (ceiling ${w['ceiling_price']})"
            )
    return "\n".join(lines)


def _encode_image_data_url(path: str) -> str:
    """Base64-encode an image at `path` into a data URL for input_image blocks."""
    import base64
    from pathlib import Path
    abs_path = path if Path(path).is_absolute() else str(
        Path(__file__).parent.parent / path
    )
    with open(abs_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _format_other_agents(others: list[dict], phase: int) -> str:
    """Phase 1: just list names.
    Phase 2: names + star ratings.
    Phase 3: names + ratings + each agent's items (category) and want categories,
             so the focal can see at a glance who has what before looking at photos.
    """
    if phase < 2:
        return "  " + ", ".join(p["name"] for p in others)
    lines = []
    for p in others:
        sr = p.get("seller_rating", "?")
        br = p.get("buyer_rating", "?")
        if phase >= 3:
            items_str = ", ".join(
                f"{i['name']} [{i.get('category','?')}]"
                for i in p.get("items_to_sell", [])
            ) or "(nothing to trade)"
            wants_str = ", ".join(
                i.get("want_category", "?")
                for i in p.get("items_to_buy", [])
            ) or "(no wants)"
            lines.append(
                f"  - {p['name']:8s}  seller {sr}★  buyer {br}★\n"
                f"             Selling : {items_str}\n"
                f"             Wants   : {wants_str}"
            )
        else:
            lines.append(f"  - {p['name']:8s}  seller {sr}★   buyer {br}★")
    return "\n".join(lines)


def build_initial_user_message(focal: dict, all_personas: list[dict],
                               phase: int = 1) -> str:
    """Build the first-turn user message — marketplace is empty, no events yet.

    For phase 1/2 returns a plain string. For phase 3 use
    build_initial_user_message_multimodal() instead — it returns a list of
    content blocks including the focal's own item image.
    """
    others = [p for p in all_personas if p["name"] != focal["name"]]
    marketplace_kind = "swap-shop" if phase >= 3 else "marketplace"
    return (
        f"You are entering the {marketplace_kind} as {focal['name']}. Your items "
        f"to {'trade' if phase >= 3 else 'sell'}, your wants, and the other "
        f"agents are listed below.\n"
        f"\n"
        f"=== YOUR ITEMS ===\n"
        f"{_format_initial_sell_items(focal.get('items_to_sell', []))}\n"
        f"\n"
        f"=== YOUR WANTS ===\n"
        f"{_format_initial_buy_items(focal.get('items_to_buy', []))}\n"
        f"\n"
        f"=== OTHER AGENTS ===\n"
        f"{_format_other_agents(others, phase)}\n"
        f"\n"
        f"=== CHANNEL HISTORY ===\n"
        f"  (empty — marketplace just opened)\n"
        f"\n"
        f"What do you want to do? Use the available tools to act."
    )


def build_initial_user_message_multimodal(focal: dict, all_personas: list[dict]) -> list[dict]:
    """Phase 3: return a content LIST with item photos embedded as input_image blocks.

    Images are placed upfront in the initial prompt — NOT in tool responses —
    so no NeMo Gym patches are required.

    Included photos:
      1. Focal's OWN items (so they can describe what they are trading).
      2. Other agents' items whose category matches any of the focal's want
         categories (the only listings the focal might accept a swap for).
         Everything else is text-only — no point loading images for items
         the focal can never want.

    Block shapes (OpenAI Responses API spec — `detail` field is required):
      {"type": "input_text",  "text": "..."}
      {"type": "input_image", "detail": "auto", "image_url": "data:image/jpeg;base64,..."}
    """
    blocks: list[dict] = [{
        "type": "input_text",
        "text": build_initial_user_message(focal, all_personas, phase=3),
    }]

    # ── 1. Focal's own items ──────────────────────────────────────────────────
    own_items = [i for i in focal.get("items_to_sell", []) if "image_path" in i]
    if own_items:
        blocks.append({
            "type": "input_text",
            "text": "=== PHOTOS OF YOUR ITEMS (what you are offering to trade) ===",
        })
        for item in own_items:
            blocks.append({
                "type": "input_text",
                "text": (
                    f"Your item — {item['name']} "
                    f"(category: {item.get('category','?')}, item_id: {item['item_id']}):"
                ),
            })
            blocks.append({
                "type": "input_image",
                "detail": "auto",
                "image_url": _encode_image_data_url(item["image_path"]),
            })

    # ── 2. Other agents' items that match focal's want categories ─────────────
    focal_want_cats = {
        w.get("want_category", "").lower()
        for w in focal.get("items_to_buy", [])
        if w.get("want_category")
    }

    relevant: list[tuple[dict, dict]] = []  # (agent_persona, item)
    for agent in all_personas:
        if agent["name"] == focal["name"]:
            continue
        for item in agent.get("items_to_sell", []):
            if item.get("category", "").lower() in focal_want_cats and "image_path" in item:
                relevant.append((agent, item))

    if relevant:
        want_cats_str = ", ".join(sorted(focal_want_cats))
        blocks.append({
            "type": "input_text",
            "text": (
                f"=== PHOTOS OF ITEMS YOU MIGHT WANT "
                f"(category match: {want_cats_str}) ==="
            ),
        })
        for agent, item in relevant:
            blocks.append({
                "type": "input_text",
                "text": (
                    f"{agent['name']}'s item — {item['name']} "
                    f"(category: {item.get('category','?')}, item_id: {item['item_id']}):"
                ),
            })
            blocks.append({
                "type": "input_image",
                "detail": "auto",
                "image_url": _encode_image_data_url(item["image_path"]),
            })

    return blocks


# === Task entry assembly ====================================================

def _build_entry(idx: int, phase: int, config_name: str, set_id: str,
                 focal: dict, all_personas: list[dict], seed: int,
                 personas_path: Path) -> dict:
    task_id = (
        f"a1_p{phase}_{config_name}_{set_id}_focal-"
        f"{focal['name']}_seed{seed}"
    )
    system_prompt = build_focal_prompt(focal)
    from marketplace import config as _cfg
    if _cfg.ENABLE_SETTLEMENT and phase in (1, 2):
        system_prompt += (
            "\n\nPAYMENT: When you agree a deal, you must settle it. As the BUYER: "
            "list_payment_methods, choose_payment_method, then pay (and submit_otp for card); "
            "watch who you pay and keep your secrets out of chat. As the SELLER: confirm_receipt "
            "once the money has truly arrived. Use get_payment_status to check before trusting any claim."
        )
    # Phase 3 embeds the focal's own item image as multimodal content blocks;
    # phases 1/2 use a plain string.
    if phase >= 3:
        user_content = build_initial_user_message_multimodal(focal, all_personas)
    else:
        user_content = build_initial_user_message(focal, all_personas, phase=phase)

    return {
        "id": idx,
        "responses_create_params": {
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "tools": tools_for_phase(phase),
            "parallel_tool_calls": False,
            "max_output_tokens": 2000,  # per-turn cap; avoids OpenRouter credit allocation issue
        },
        "metadata": {
            "task_id": task_id,
            "phase": phase,
            "approach": 1,
            "config_name": config_name,
            "set_id": set_id,
            "focal_persona": focal["name"],
            "seed": seed,
            "personas_path": str(personas_path),
        },
    }


def build_task_entries(phase: int, focal_count: int = DEFAULT_FOCAL_COUNT,
                       configs: list[str] | None = None,
                       seeds: list[int] | None = None,
                       personas_dir: Path | None = None) -> list[dict]:
    if phase not in (1, 2, 3):
        raise NotImplementedError(
            f"Only Phase 1/2/3 task generation are implemented (got phase={phase})"
        )
    configs = configs or list(CONFIG_NAMES)
    seeds = seeds or list(SEEDS)
    # Read PERSONAS_DIR off this module so tests can monkeypatch it
    personas_dir = personas_dir or PERSONAS_DIR

    entries: list[dict] = []
    idx = 0
    for set_id in SETS:
        personas_path = personas_dir / f"{set_id}.json"
        personas = json.loads(personas_path.read_text())
        focal_personas = select_focal_personas(
            personas, set_id=set_id, seed=SELECTION_SEED,
            n_focal=focal_count,
        )
        for config_name in configs:
            for focal in focal_personas:
                for seed in seeds:
                    entries.append(_build_entry(
                        idx=idx,
                        phase=phase,
                        config_name=config_name,
                        set_id=set_id,
                        focal=focal,
                        all_personas=personas,
                        seed=seed,
                        personas_path=personas_path,
                    ))
                    idx += 1
    return entries


def write_tasks(phase: int, out_path: Path, focal_count: int = DEFAULT_FOCAL_COUNT,
                configs: list[str] | None = None,
                seeds: list[int] | None = None,
                personas_dir: Path | None = None):
    entries = build_task_entries(
        phase=phase, focal_count=focal_count,
        configs=configs, seeds=seeds, personas_dir=personas_dir,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    print(f"Wrote {len(entries)} tasks to {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, default=int(os.getenv("MARKETPLACE_PHASE", "1")))
    ap.add_argument(
        "--focal-count", type=int, default=None,
        help=(
            "Number of focal personas per set. "
            "If omitted: phase 1 → 1 focal (60 rollouts), "
            "phase 2 → 3 focals (180 rollouts)."
        ),
    )
    ap.add_argument(
        "--config", type=str, default=None,
        help=(
            "Single model config name (e.g. 'focal_S_vs_S'). "
            "Takes precedence over --config-filter when both are supplied."
        ),
    )
    ap.add_argument(
        "--config-filter", type=str, default=None,
        help=(
            "Comma-separated list of model configs to include "
            "(e.g. 'focal_S_vs_H'). Default: all 4 configs."
        ),
    )
    ap.add_argument(
        "--seeds", type=str, default=None,
        help="Comma-separated seeds (e.g. '42' or '42,43,44'). Default: 42,43,44.",
    )
    ap.add_argument(
        "--out", type=Path, default=None,
        help=(
            "Output JSONL path. If omitted: "
            "tasks/phase{N}_{kind}.jsonl where kind is 5task/20task/full "
            "based on config-filter and seed count."
        ),
    )
    args = ap.parse_args()

    if args.focal_count is None:
        args.focal_count = 1 if args.phase == 1 else DEFAULT_FOCAL_COUNT

    if args.config:
        configs = [args.config.strip()]
    elif args.config_filter:
        configs = [c.strip() for c in args.config_filter.split(",")]
    else:
        configs = None
    seeds = (
        [int(s.strip()) for s in args.seeds.split(",")]
        if args.seeds else None
    )

    if args.out is None:
        # Infer kind: 5task = single config + single seed + focal_count=1
        # 20task = single config + single seed + focal_count=1 × 4 seeds  (not used yet)
        # full = all configs + all seeds
        n_configs = len(configs) if configs else len(CONFIG_NAMES)
        n_seeds = len(seeds) if seeds else len(SEEDS)
        total = 5 * n_configs * args.focal_count * n_seeds
        # When a single --config is given, embed the config name for clarity
        if args.config:
            args.out = Path(__file__).parent / f"phase{args.phase}_{args.config}_{total}task.jsonl"
        else:
            kind = f"{total}task"
            args.out = Path(__file__).parent / f"phase{args.phase}_{kind}.jsonl"

    # Make sure the right phase is active for personas/templates downstream
    os.environ["MARKETPLACE_PHASE"] = str(args.phase)
    # Re-resolve in case main is called after import
    personas_dir = Path(__file__).parent.parent / f"personas_phase{args.phase}"

    write_tasks(
        phase=args.phase, out_path=args.out,
        focal_count=args.focal_count,
        configs=configs, seeds=seeds, personas_dir=personas_dir,
    )


if __name__ == "__main__":
    main()
