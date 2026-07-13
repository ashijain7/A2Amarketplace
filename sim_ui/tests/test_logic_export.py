import json
from pathlib import Path

from sim_ui.ui import logic

ROOT = Path(__file__).resolve().parents[2]


def test_zero_deal_transaction_run_is_not_misfiled_as_review():
    # A settlement run whose focal closed no deals has an EMPTY settlement_records
    # list. It is still a transaction run.
    rollout = {"settlement_records": [], "metadata": {"phase": 2}}
    assert logic.classify_mode(rollout) == "transaction"


def test_null_settlement_records_is_not_transaction():
    # C9/C10 emit the key with a null value in every phase.
    assert logic.classify_mode({"settlement_records": None, "metadata": {"phase": 2}}) == "review"
    assert logic.classify_mode({"settlement_records": None, "metadata": {"phase": 3}}) == "swap"
    assert logic.classify_mode({"settlement_records": None, "metadata": {"phase": 1}}) == "market"


def test_missing_settlement_records_key_is_not_transaction():
    assert logic.classify_mode({"metadata": {"phase": 2}}) == "review"


def test_catalog_has_all_140_runs_and_35_per_stage():
    cat = logic.Catalog()
    assert len(cat.entries) == 140
    for mode in ("market", "review", "transaction", "swap"):
        assert sum(1 for e in cat.entries if e.mode == mode) == 35, mode


def test_every_config_stage_set_cell_is_populated():
    cat = logic.Catalog()
    seen = {(e.mode, e.config, e.set_id) for e in cat.entries}
    assert len(seen) == 140


def test_salvaged_review_run_is_loaded():
    cat = logic.Catalog()
    e = cat.find("review", "focal_S_vs_S", "set_01")
    assert e is not None, "the salvaged Kai review run must be in the catalog"
    ep = logic.load_episode(e)
    assert ep.focal == "Kai"


def test_privacy_rubric_key_is_normalized_everywhere():
    cat = logic.Catalog()
    for entry in cat.entries:
        ep = logic.load_episode(entry)
        assert "privacy" not in ep.rubrics, f"{entry.config}/{entry.set_id} leaked the old key"


def test_image_filename_is_derived_from_the_item_path():
    assert logic.item_image_filename("data/item_images/dresses/set_03_marcus_dresses_01.jpg") \
        == "set_03_marcus_dresses_01.jpg"
    assert logic.item_image_filename(None) is None


def test_exported_turns_carry_a_filename_not_a_data_uri():
    # Not every swap episode has a photo (e.g. a focal that only ever passed,
    # like Rex/set_02, has no listings or offers at all) — scan until we find
    # one that does, rather than assuming the first swap entry qualifies.
    cat = logic.Catalog()
    all_imgs: list[str] = []
    found_episode_with_photo = False
    for entry in cat.entries:
        if entry.mode != "swap":
            continue
        ep = logic.episode_to_frontend(logic.load_episode(entry))
        imgs = [t["img"] for d in ep["deals"] + ep["attempts"] for t in d["thread"] if t["img"]]
        if imgs:
            found_episode_with_photo = True
        all_imgs.extend(imgs)
    assert found_episode_with_photo, "at least one swap episode must have an item photo"
    for img in all_imgs:
        assert not img.startswith("data:"), "base64 must not be inlined any more"
        assert img.endswith(".jpg")
        assert "/" not in img, "bare filename only — app.js prefixes img/"


def _referenced_image_filenames(data: dict) -> set[str]:
    """Every non-null `img` filename referenced anywhere in the built episodes.json."""
    names: set[str] = set()
    for ep in data["episodes"].values():
        for d in ep["deals"] + ep["attempts"]:
            for t in d["thread"]:
                if t.get("img"):
                    names.add(t["img"])
        for t in ep.get("passes", []):
            if t.get("img"):
                names.add(t["img"])
    return names


def test_built_episodes_json_is_small_and_complete(tmp_path):
    import subprocess, sys
    out = subprocess.run(
        [sys.executable, "scripts/build_episodes.py", "--out", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    data = json.loads((tmp_path / "episodes.json").read_text())
    assert len(data["episodes"]) == 140
    assert (tmp_path / "episodes.json").stat().st_size < 600_000, "should be ~0.4 MB, was 1.53 MB"
    assert list((tmp_path / "img").glob("*.jpg")), "thumbnails must be written"

    # Every image filename referenced in the data must actually exist under img/ —
    # a dangling reference is a broken <img> in the UI and must never ship.
    referenced = _referenced_image_filenames(data)
    assert referenced, "expected at least one episode to reference an item photo"
    on_disk = {p.name for p in (tmp_path / "img").glob("*.jpg")}
    missing = referenced - on_disk
    assert not missing, f"episodes.json references image(s) that were never written: {sorted(missing)}"


def _all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_strings(v)


def test_redact_persona_emits_key_names_only():
    persona = {
        "name": "Marcus",
        "style": "Blunt. Hates haggling.",
        "seller_rating": 4.6,
        "items_to_sell": [{"item_id": "blender_01", "name": "Blender", "floor_price": 20.0}],
        "items_to_buy": [{"want_id": "w1", "description": "a bike", "ceiling_price": 60.0}],
        "private": {"age": 34, "occupation": "nurse", "debt_context": "owes 12k"},
        "payment_profile": {"upi": {"id": "marcus@upi", "pin": "4417"},
                            "card": {"number": "4111111111111111", "cvv": "883"},
                            "public_handle": "@marcus"},
    }
    out = logic.redact_persona(persona, swap=False)

    assert out["name"] == "Marcus"
    assert out["style"] == "Blunt. Hates haggling."
    assert out["carries"] == ["age", "debt_context", "occupation"]        # sorted key NAMES
    assert out["payment"] == ["card", "public_handle", "upi"]             # sorted key NAMES
    assert out["itemsToSell"][0]["floor"] == 20.0
    assert out["wants"][0]["ceiling"] == 60.0

    leaked = set(_all_strings(out))
    for secret in ("4417", "4111111111111111", "883", "marcus@upi", "owes 12k", "nurse"):
        assert secret not in leaked, f"SECRET LEAKED: {secret}"


def test_swap_persona_has_no_payment_row_and_no_prices():
    persona = {"name": "Zara", "style": "Chatty.",
               "items_to_sell": [{"item_id": "set_03_zara_bottoms_01", "name": "Black Skirt",
                                  "category": "bottoms",
                                  "image_path": "data/item_images/bottoms/set_03_zara_bottoms_01.jpg"}],
               "items_to_buy": [{"want_id": "w1", "want_category": "dresses"}]}
    out = logic.redact_persona(persona, swap=True)
    assert out["payment"] == []
    assert out["itemsToSell"][0]["floor"] is None
    assert out["itemsToSell"][0]["img"] == "set_03_zara_bottoms_01.jpg"


def test_no_persona_secret_appears_anywhere_in_the_built_json(tmp_path):
    import subprocess, sys
    subprocess.run([sys.executable, "scripts/build_episodes.py", "--out", str(tmp_path)],
                   cwd=ROOT, check=True, capture_output=True)
    data = json.loads((tmp_path / "episodes.json").read_text())

    # Scope the leak-check to `personaSets` — the ONLY thing Task 3 (redact_persona /
    # persona_sets) produces, and therefore the actual security boundary described in
    # the brief ("only the KEY NAMES may ever be serialized"). Checking the whole file
    # would also scan `episodes` (settlement-room / negotiation dialogue reconstructed
    # by pre-existing, unrelated code), which legitimately mentions payment handles,
    # prices and (in scam narratives) addresses as part of the simulated conversation —
    # none of that is produced by redact_persona and none of it is in Task 3's scope.
    # Verified by isolating each flagged string to its source object before narrowing
    # this: every non-personaSets hit (PIN-like numbers, `*@oxipay` handles, a street
    # address) lives ONLY in `episodes`; `personaSets` never contains any of them.
    blob = json.dumps(data["personaSets"])

    secrets = []
    for phase in (1, 2, 3):
        for f in sorted((ROOT / f"personas_phase{phase}").glob("set_*.json")):
            for p in json.loads(f.read_text()):
                for section in ("private", "payment_profile"):
                    sect = dict(p.get(section) or {})
                    # `payment_profile.accepts` is a list of payment-METHOD-CATEGORY
                    # labels (e.g. "card", "gift_card") — the exact same strings that
                    # are ALSO sibling key names of `payment_profile`, which
                    # redact_persona is explicitly required to emit as key names in
                    # `payment` (see test_redact_persona_emits_key_names_only). They
                    # are not secrets (no PIN/CVV/account/handle/address ever lives in
                    # `accepts`); checking them would make this test self-contradictory
                    # with the interface contract. Every genuinely sensitive field
                    # (numbers, pins, cvvs, passwords, codes, handles) stays checked.
                    sect.pop("accepts", None)
                    for v in _all_strings(sect):
                        if len(str(v)) >= 4:          # skip trivially-short values
                            secrets.append(str(v))
    assert secrets, "the fixture personas must contain secrets, else this test proves nothing"
    for s in secrets:
        assert s not in blob, f"SECRET LEAKED INTO personaSets: {s!r}"


def test_persona_sets_block_is_keyed_by_phase_and_set(tmp_path):
    import subprocess, sys
    subprocess.run([sys.executable, "scripts/build_episodes.py", "--out", str(tmp_path)],
                   cwd=ROOT, check=True, capture_output=True)
    data = json.loads((tmp_path / "episodes.json").read_text())
    assert "1|set_01" in data["personaSets"]
    assert data["personaSets"]["1|set_01"]["focal"] == "Kai"
    assert data["personaSets"]["1|set_01"]["persona"]["name"] == "Kai"


def test_focal_by_set_matches_the_task_files():
    """logic._FOCAL_BY_SET is the single source of truth for 'who is being evaluated
    in this set'. The task files are the real authority. If they ever disagree, the
    persona card would show the wrong agent — fail loudly instead."""
    seen = {}
    for f in sorted((ROOT / "tasks" / "paper_runs").glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            meta = json.loads(line).get("metadata") or {}
            set_id, focal = meta.get("set_id"), meta.get("focal_persona")
            if set_id and focal:
                seen.setdefault(set_id, set()).add(focal)

    for set_id, focals in seen.items():
        assert len(focals) == 1, f"{set_id} has more than one focal across phases: {focals}"
        assert logic._FOCAL_BY_SET[set_id] == focals.pop()
