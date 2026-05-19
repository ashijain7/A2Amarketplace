from resources_server.focal_selection import select_focal_personas


def _persona(name, has_private=False):
    p = {"name": name, "items_to_sell": [], "items_to_buy": [], "style": "x"}
    if has_private:
        p["private"] = {
            "real_address": "1 Main", "age": 30, "occupation": "x",
            "financial_situation": "x", "debt_context": "x",
        }
    return p


def test_select_focal_picks_three_from_ten():
    personas = [_persona(f"agent_{i}") for i in range(10)]
    chosen = select_focal_personas(personas, set_id="set_01", seed=42)
    assert len(chosen) == 3
    assert len(set(c["name"] for c in chosen)) == 3


def test_select_focal_is_deterministic():
    personas = [_persona(f"agent_{i}") for i in range(10)]
    a = select_focal_personas(personas, set_id="set_01", seed=42)
    b = select_focal_personas(personas, set_id="set_01", seed=42)
    assert [p["name"] for p in a] == [p["name"] for p in b]


def test_select_focal_set01_no_constraint():
    """Sets without private personas — no force-replacement."""
    personas = [_persona(f"agent_{i}") for i in range(10)]
    chosen = select_focal_personas(personas, set_id="set_01", seed=42)
    assert all("private" not in c for c in chosen)


def test_select_focal_set03_forces_one_private_bearing():
    """Set 3 has 3 private-bearing personas (indices picked by seed=42)."""
    personas = []
    for i in range(10):
        # In real set_03, indices [4, 6, 8] would be private by seed=42 logic;
        # but the constraint only requires at least one private-bearing focal.
        # For this test, mark 3 specific personas as private-bearing.
        personas.append(_persona(f"agent_{i}", has_private=(i in {3, 5, 7})))

    chosen = select_focal_personas(personas, set_id="set_03", seed=999)
    # Even with a bad seed (999), the constraint must force a swap.
    assert any("private" in c for c in chosen), \
        "set_03+ must always include at least one private-bearing focal"


def test_select_focal_set03_keeps_random_pick_if_already_has_private():
    """If random pick already contains a private persona, no force-swap needed."""
    personas = []
    for i in range(10):
        personas.append(_persona(f"agent_{i}", has_private=(i in {0, 1, 2, 3, 4})))
    chosen = select_focal_personas(personas, set_id="set_04", seed=42)
    # 5 of 10 are private — seed=42 should naturally pick at least one.
    assert any("private" in c for c in chosen)
