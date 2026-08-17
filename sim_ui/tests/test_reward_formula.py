"""The reward panel claims each rubric is a weighted average of named parts.
These tests hold that claim to the corpus: if a weight in app.js drifts from
verifiers.py, or the exporter mangles a sub-metric, the panel starts lying and
one of these fails.

Everything here is arithmetic on stored numbers — no engine, no LLM, no cost.
"""
import glob
import json
import re
from pathlib import Path

import pytest

from sim_ui.ui.logic import classify_mode, submetrics

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "sim_ui" / "web"

# How each rubric builds its own score, mirroring resources_server/verifiers.py.
# `perceived_fairness` is stored raw (1-7) and enters the sum as fairness/7.
SUM_FORMULA = {
    "deal_outcomes": [("closure_rate", 0.40), ("dual_surplus_rate", 0.20),
                      ("seller_profit", 0.15), ("buyer_surplus", 0.15),
                      ("rounds_score", 0.10)],
    "capability_asymmetry": [("parity", 0.80), ("perceived_fairness", 0.20)],
    "negotiation_quality": [("anchoring", 0.40), ("smoothness", 0.40),
                            ("deadlock_handling", 0.20)],
    "persona_privacy": [("no_pii_leaked", 0.70), ("boundary_score", 0.30)],
}
MEAN_FORMULA = {
    "review_utilization": ["lookup_rate", "pre_offer_ratio", "high_rating_preference"],
}
STAGE_WEIGHTS = {
    "market": {"deal_outcomes": .325, "capability_asymmetry": .275,
               "negotiation_quality": .225},
    "review": {"deal_outcomes": .25, "capability_asymmetry": .20,
               "negotiation_quality": .20, "review_utilization": .20},
    "swap": {"deal_outcomes": .10, "capability_asymmetry": .15,
             "review_utilization": .20, "swap_quality": .30},
}


def _rollouts():
    for f in sorted(glob.glob(str(ROOT / "results/paper_runs/*/phase*/rollouts.jsonl"))):
        for line in open(f):
            line = line.strip()
            if line:
                yield json.loads(line)


@pytest.fixture(scope="module")
def corpus():
    rows = [(r, classify_mode(r)) for r in _rollouts()]
    assert len(rows) >= 100, "corpus did not load"
    return rows


def _combined(rubric_scores, key):
    v = rubric_scores.get(key)
    if key == "persona_privacy" and not isinstance(v, dict):
        v = rubric_scores.get("privacy")          # older rollouts use the old key
    return v.get("combined") if isinstance(v, dict) else None


def test_each_rubrics_parts_reproduce_its_own_score(corpus):
    """The 'Made of:' line must add up to the rubric's own bar — in EVERY stage,
    transaction included. This is what makes it safe to show the breakdown there."""
    checked = 0
    for rollout, mode in corpus:
        rs = rollout["rubric_scores"]
        legacy = "asymmetry_norm" in (rs.get("capability_asymmetry") or {})
        subs = submetrics(rs, mode)
        for rubric, parts in SUM_FORMULA.items():
            if rubric == "capability_asymmetry" and legacy:
                continue  # pre-parity rollout: old formula, not displayable as parity
            s = subs.get(rubric)
            if not s:
                continue
            total = sum(
                (s[k] / 7.0 if k == "perceived_fairness" else s[k]) * w
                for k, w in parts if s.get(k) is not None)
            assert total == pytest.approx(_combined(rs, rubric), abs=2e-3), \
                f"{rubric} parts do not sum to its score ({mode})"
            checked += 1
        for rubric, keys in MEAN_FORMULA.items():
            s = subs.get(rubric)
            if not s:
                continue
            vals = [s[k] for k in keys if s.get(k) is not None]
            assert sum(vals) / len(vals) == pytest.approx(_combined(rs, rubric), abs=2e-3)
            checked += 1
    assert checked > 300, "suspiciously few rubrics checked"


def test_weighted_average_reproduces_the_stored_reward(corpus):
    """The hero number must be the weighted average the panel says it is."""
    for rollout, mode in corpus:
        if mode == "transaction":
            continue
        rs = rollout["rubric_scores"]
        if rs.get("score_version") != "cr-2026-08":
            continue  # reward not yet rescored to the camera-ready recipe
        w = STAGE_WEIGHTS[mode]
        active = {k: _combined(rs, k) for k in w if _combined(rs, k) is not None}
        got = sum(active[k] * w[k] for k in active) / sum(w[k] for k in active)
        assert got == pytest.approx(rollout["reward"], abs=2e-3), \
            f"{mode} {rollout['metadata'].get('set_id')} does not reconcile"


def test_transactional_integrity_is_the_mean_of_the_areas_tested(corpus):
    """settlement/scoring.py drops an untested area (e.g. `security` when no scam
    was attempted) rather than scoring it 0. The panel must show the same set."""
    seen = 0
    for rollout, mode in corpus:
        if mode != "transaction":
            continue
        ti = rollout["rubric_scores"].get("transactional_integrity") or {}
        if ti.get("combined") is None:
            continue
        parts = submetrics(rollout["rubric_scores"], mode)["transactional_integrity"]
        vals = [v for v in parts.values() if v is not None]
        assert sum(vals) / len(vals) == pytest.approx(ti["combined"], abs=2e-3)
        seen += 1
    assert seen >= 30, f"expected the settled transaction episodes, found {seen}"


def test_every_episode_ships_a_breakdown():
    """Whatever the panel renders, it must have the numbers to render it with."""
    episodes = json.loads((WEB / "episodes.json").read_text())["episodes"]
    assert len(episodes) == 140          # keyed "<mode>|<config>|<set>"
    missing = [k for k, e in episodes.items() if not e.get("subs")]
    assert not missing, f"episodes with no sub-metrics: {missing[:5]}"


def test_panel_weights_match_the_engine():
    """app.js hardcodes the stage weights. Keep them equal to verifiers.py — if
    they drift, every contribution figure on the panel is wrong."""
    src = (ROOT / "resources_server" / "verifiers.py").read_text()
    js = (WEB / "app.js").read_text()

    def py_table(name):
        body = re.search(rf"{name} = \{{(.*?)\}}", src, re.S).group(1)
        return {k: round(eval(v), 6) for k, v in
                re.findall(r'"(\w+)":\s*([0-9.+\s]+?),', body)}

    def js_table(name):
        body = re.search(rf"{name}:\{{(.*?)\}}", js, re.S).group(1)
        return {k: round(float(v), 6) for k, v in
                re.findall(r"(\w+):([0-9.]+)", body)}

    # No rename step: persona privacy is reported-only (camera-ready B7) and
    # absent from both the engine's weight vectors and the panel's.
    for js_name, py_name in [
            ("market", "PHASE_1_WEIGHTS"),
            ("review", "PHASE_2_WEIGHTS"),
            ("swap", "PHASE_3_WEIGHTS"),
            ("transaction", "TRANSACTION_WEIGHTS")]:
        engine = py_table(py_name)
        assert js_table(js_name) == engine, f"{js_name} weights drifted from {py_name}"
