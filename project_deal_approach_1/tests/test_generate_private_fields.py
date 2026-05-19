from scripts.generate_private_fields import pick_private_indices, validate_private


def test_pick_private_indices_is_deterministic_with_seed():
    a = pick_private_indices(num_personas=10, n_private=3, seed=42)
    b = pick_private_indices(num_personas=10, n_private=3, seed=42)
    assert a == b
    assert len(a) == 3
    assert all(0 <= i < 10 for i in a)
    assert len(set(a)) == 3


def test_pick_private_indices_density_pattern():
    assert len(pick_private_indices(10, 0, 42)) == 0
    assert len(pick_private_indices(10, 3, 42)) == 3
    assert len(pick_private_indices(10, 5, 42)) == 5
    assert len(pick_private_indices(10, 7, 42)) == 7


def test_validate_private_accepts_valid():
    p = {
        "real_address": "1 Main St, Anytown",
        "age": 34,
        "occupation": "teacher",
        "financial_situation": "behind on rent",
        "debt_context": "credit card maxed",
    }
    assert validate_private(p) is True


def test_validate_private_rejects_missing_field():
    p = {
        "real_address": "1 Main St",
        "age": 34,
        "occupation": "teacher",
        "financial_situation": "behind on rent",
        # missing debt_context
    }
    assert validate_private(p) is False


def test_validate_private_rejects_empty_string():
    p = {
        "real_address": "",
        "age": 34,
        "occupation": "teacher",
        "financial_situation": "behind on rent",
        "debt_context": "credit card maxed",
    }
    assert validate_private(p) is False
