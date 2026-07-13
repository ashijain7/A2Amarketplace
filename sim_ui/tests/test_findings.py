"""The 5 findings shown on the leaderboard tab are claims about the corpus.
Assert every number in them, so the copy can never drift from the data."""
import statistics as st
from collections import defaultdict

from sim_ui.ui import logic


def _episodes():
    cat = logic.Catalog()
    return [(e, logic.load_episode(e)) for e in cat.entries]


def test_finding_1_sets_01_02_are_harder_than_03_05():
    # The published copy says "0.37 vs 0.58 — that 0.21 gap". Keep the three numbers
    # tied together here: 0.5762 - 0.3662 = 0.2101 -> 0.21. (An earlier draft of the
    # copy said 0.57/0.20 because it truncated instead of rounding; the corpus was
    # right and the copy was corrected, not this test.)
    by_set = defaultdict(list)
    for entry, ep in _episodes():
        by_set[entry.set_id].append(ep.reward)
    easy = st.mean([r for s in ("set_03", "set_04", "set_05") for r in by_set[s]])
    hard = st.mean([r for s in ("set_01", "set_02") for r in by_set[s]])
    assert round(hard, 2) == 0.37
    assert round(easy, 2) == 0.58


def test_finding_2_three_pairs_swing_five_places():
    lb = logic.build_leaderboard()
    ranks = defaultdict(dict)
    for mode, block in lb.items():
        for i, row in enumerate(block["rows"], 1):
            ranks[row["config"]][mode] = i
    swings = {c: max(d.values()) - min(d.values()) for c, d in ranks.items()}
    assert sum(1 for s in swings.values() if s >= 5) == 3


def test_finding_3_gemini_vs_gpt_never_looks_up_and_finishes_last_twice():
    lookups = 0
    for entry, _ in _episodes():
        if entry.config != "focal_G_vs_X" or entry.mode == "market":
            continue
        rollout = logic._load_raw(entry)
        ru = (rollout.get("rubric_scores") or {}).get("review_utilization") or {}
        lookups += ru.get("lookups_made") or 0
    assert lookups == 0, "focal_G_vs_X made zero reputation lookups in the whole corpus"

    lb = logic.build_leaderboard()
    assert lb["review"]["rows"][-1]["config"] == "focal_G_vs_X"
    assert lb["transaction"]["rows"][-1]["config"] == "focal_G_vs_X"


def test_finding_4_scam_resistance_is_about_90_percent():
    outcomes = defaultdict(int)
    for entry, _ in _episodes():
        if entry.mode != "transaction":
            continue
        for rec in logic._load_raw(entry).get("settlement_records") or []:
            outcomes[rec.get("outcome")] += 1
    assert outcomes["settled"] == 56
    assert outcomes["paid-wrong-recipient"] == 6
    assert outcomes["scam-success"] == 1


def test_finding_5_nobody_negotiates_above_075():
    scores, parts = [], defaultdict(list)
    for entry, _ in _episodes():
        nq = (logic._load_raw(entry).get("rubric_scores") or {}).get("negotiation_quality") or {}
        if nq.get("combined") is None:
            continue
        scores.append(nq["combined"])
        for k in ("anchoring", "smoothness", "deadlock_handling"):
            if nq.get(k) is not None:
                parts[k].append(nq[k])
    assert round(st.mean(scores), 2) == 0.43
    assert max(scores) <= 0.75
    assert round(st.mean(parts["deadlock_handling"]), 2) == 0.98
    assert round(st.mean(parts["anchoring"]), 2) == 0.31
    assert round(st.mean(parts["smoothness"]), 2) == 0.28
