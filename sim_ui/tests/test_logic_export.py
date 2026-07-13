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
