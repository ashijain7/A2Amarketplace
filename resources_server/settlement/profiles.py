"""Build the bank's records book + starting balances from persona payment_profiles."""

START_MAIN = 100.0
START_GIFT = 100.0


def build_records(personas: list[dict]):
    """Return (destinations, secrets, accepts) dicts keyed by agent name."""
    destinations: dict[str, str] = {}   # destination-string -> owner
    secrets: dict[str, dict] = {}
    accepts: dict[str, list] = {}
    for p in personas:
        name = p["name"]
        prof = p.get("payment_profile")
        if not prof:
            continue
        upi = prof.get("upi", {})
        card = prof.get("card", {})
        bank = prof.get("bank", {})
        wallet = prof.get("wallet", {})
        gift = prof.get("gift_card", {})
        # destinations others can pay this agent at
        for dest in (prof.get("public_handle"), upi.get("id"), wallet.get("mobile")):
            if dest:
                destinations[str(dest)] = name
        if bank.get("account") and bank.get("ifsc"):
            destinations[f"acct:{bank['account']}:{bank['ifsc']}"] = name
        # this agent's own secrets (the leak targets / auth values)
        secrets[name] = {
            "upi_pin": upi.get("pin"),
            "card_number": card.get("number"),
            "card_cvv": card.get("cvv"),
            "bank_password": bank.get("password"),
            "wallet_pin": wallet.get("pin"),
            "gift_code": gift.get("code"),
        }
        accepts[name] = list(prof.get("accepts", ["upi", "wallet", "bank", "card", "gift_card"]))
    return destinations, secrets, accepts


def starting_balances(personas: list[dict]) -> dict:
    return {p["name"]: {"main": START_MAIN, "gift": START_GIFT} for p in personas}
