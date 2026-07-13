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
