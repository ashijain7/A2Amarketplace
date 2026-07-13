import adapter


def _plan(phase="transaction", scammer=True):
    mp, settle = adapter.PHASE_MAP[phase]
    return {"marketplace_phase": mp, "enable_settlement": settle,
            "opponents_model": "google/gemini-3.1-pro-preview",
            "focal_max_steps": 25, "scammer": scammer}


def test_scammer_on_by_default_in_transaction():
    env = adapter._stack_env(_plan(scammer=True))
    assert env["ENABLE_SETTLEMENT"] == "yes"
    assert env["SETTLEMENT_SCAM"] == "yes"


def test_scammer_can_be_turned_off():
    env = adapter._stack_env(_plan(scammer=False))
    assert env["SETTLEMENT_SCAM"] == "no"


def test_scammer_flag_is_inert_outside_settlement():
    env = adapter._stack_env(_plan(phase="market_deal", scammer=True))
    assert env["ENABLE_SETTLEMENT"] == "no"
    assert env["SETTLEMENT_SCAM"] == "no", "no settlement => no scammer, whatever was asked"
