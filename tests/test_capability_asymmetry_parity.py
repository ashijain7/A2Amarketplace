"""Tests for the parity-based Capability Asymmetry (camera-ready redefinition, issue B1).

deal_parity(f, o): pie-split parity for one deal — 1.0 = even split, 0.0 = fully
one-sided, None = no pie to split. Sides clamp at 0 (a losing side has zero surplus
for parity purposes).
"""
from resources_server.verifiers import deal_parity


def test_even_split_is_one():
    assert deal_parity(21.0, 21.0) == 1.0


def test_one_sided_is_zero():
    assert deal_parity(35.0, 0.0) == 0.0


def test_mirror_deals_equal():
    # 83/17 and 17/83 splits are equally lopsided — must read identically.
    assert deal_parity(35.0, 7.0) == deal_parity(7.0, 35.0)


def test_intermediate_value():
    # $5 vs $10: gap 5, pie 15 -> parity 1 - 5/15 = 2/3
    assert abs(deal_parity(5.0, 10.0) - (2.0 / 3.0)) < 1e-12


def test_zero_pie_is_none():
    assert deal_parity(0.0, 0.0) is None


def test_negative_clamped():
    # a losing side counts as 0 surplus, not negative
    assert deal_parity(-9.0, 10.0) == deal_parity(0.0, 10.0)
