import json
from unittest.mock import patch
from scripts.generate_private_fields import (
    pick_indices, enrich_personas, DENSITY_BY_SET,
)


def test_density_table_matches_spec():
    assert DENSITY_BY_SET == {"set_01": 0, "set_02": 0, "set_03": 3, "set_04": 5, "set_05": 7}


def test_pick_indices_deterministic_with_seed_42():
    a = pick_indices(n_total=10, n_private=5, seed=42)
    b = pick_indices(n_total=10, n_private=5, seed=42)
    assert a == b
    assert len(a) == 5
    assert all(0 <= i < 10 for i in a)
    assert len(set(a)) == 5


def test_enrich_personas_adds_private_to_correct_count():
    personas = [{"name": f"P{i}", "items_to_sell": [], "items_to_buy": [], "style": ""}
                for i in range(10)]
    fake_private = {
        "real_address": "1 Maple St, Boston",
        "age": 30,
        "occupation": "teacher",
        "financial_situation": "ok",
        "debt_context": "none",
    }
    with patch("scripts.generate_private_fields.call_gpt4o_for_private", return_value=fake_private):
        enriched = enrich_personas(personas, n_private=3, seed=42)
    has_private = [p for p in enriched if "private" in p]
    assert len(has_private) == 3
    for p in has_private:
        assert set(p["private"].keys()) == {
            "real_address", "age", "occupation", "financial_situation", "debt_context",
        }
