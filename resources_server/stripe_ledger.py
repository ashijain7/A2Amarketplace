"""
Stripe payment client for the marketplace payment extension.

All Stripe API calls are isolated here. When enable_payments=False,
this module is never imported — existing runs have zero dependency on it.

Balance unit: Stripe uses integer cents. All public functions that take
dollar amounts accept cents to avoid float rounding bugs.

Visibility: we use CustomerBalanceTransaction instead of Customer.modify
so every payment shows up as an auditable line item in the Stripe dashboard
under Customer → Balance transactions.
"""

import os
import stripe
from pathlib import Path
from dotenv import load_dotenv

# Use absolute path so this works whether called from project root or a NeMo Gym subserver
load_dotenv(Path(__file__).parent.parent / ".env")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STARTING_BALANCE_CENTS = 15000  # $150 per agent


def create_agent_accounts(
    agent_names: list[str],
    config_name: str,
    set_id: str,
    phase: int,
) -> dict[str, str]:
    """Create one Stripe Customer per agent with an opening balance transaction.

    Returns {agent_name: stripe_customer_id}.
    Names each customer as "AgentName [SvS | set_01 | P1]" for dashboard clarity.
    Uses CustomerBalanceTransaction for the opening balance so it appears in history.
    Raises stripe.error.StripeError if any creation fails.
    """
    # Fix: set_id already has the "set_" prefix (e.g. "set_01"), use as-is
    # Shorten config: focal_S_vs_S_pay → SvS, focal_G35_vs_X_pay → G35vX
    short = config_name.removeprefix("focal_").removesuffix("_pay").replace("_vs_", "v")
    label = f"{short} | {set_id} | P{phase}"
    accounts = {}
    for name in agent_names:
        customer = stripe.Customer.create(
            name=f"{name} [{label}]",
            metadata={
                "agent_name": name,
                "config_name": config_name,
                "set_id": set_id,
                "phase": str(phase),
            },
        )
        # Fund via balance transaction — visible in dashboard as "Opening balance"
        stripe.CustomerBalanceTransaction.create(
            customer.id,
            amount=STARTING_BALANCE_CENTS,
            currency="usd",
            description="Opening balance — marketplace funding",
        )
        accounts[name] = customer.id
    return accounts


def get_balance_cents(customer_id: str) -> int:
    """Return the agent's current balance in cents, direct from Stripe."""
    customer = stripe.Customer.retrieve(customer_id)
    return customer.balance


def transfer(
    from_customer_id: str,
    to_customer_id: str,
    amount_cents: int,
    description: str = "",
) -> dict:
    """Move amount_cents from sender to receiver using Stripe balance transactions.

    Each transfer creates TWO visible entries in the Stripe dashboard:
      - Sender: negative transaction (debit)
      - Receiver: positive transaction (credit)

    Never writes a negative balance — returns insufficient_funds error instead.

    Returns:
        success=True:  {"success": True, "amount": float, "sender_new_balance": float,
                        "receiver_new_balance": float}
        success=False: {"success": False, "error": str, "balance": float,
                        "needed": float, "shortfall": float}
    """
    sender = stripe.Customer.retrieve(from_customer_id)
    sender_balance = sender.balance

    if sender_balance < amount_cents:
        return {
            "success": False,
            "error": "insufficient_funds",
            "balance": sender_balance / 100,
            "needed": amount_cents / 100,
            "shortfall": (amount_cents - sender_balance) / 100,
        }

    assert sender_balance - amount_cents >= 0, "balance guard: would write negative"

    desc = description or f"Marketplace payment ${amount_cents / 100:.2f}"

    # Debit sender — visible as negative transaction in their history
    stripe.CustomerBalanceTransaction.create(
        from_customer_id,
        amount=-amount_cents,
        currency="usd",
        description=f"Paid: {desc}",
    )

    # Credit receiver — visible as positive transaction in their history
    stripe.CustomerBalanceTransaction.create(
        to_customer_id,
        amount=amount_cents,
        currency="usd",
        description=f"Received: {desc}",
    )

    # Read updated balances back from Stripe
    sender_new = stripe.Customer.retrieve(from_customer_id).balance
    receiver_new = stripe.Customer.retrieve(to_customer_id).balance

    return {
        "success": True,
        "amount": amount_cents / 100,
        "sender_new_balance": sender_new / 100,
        "receiver_new_balance": receiver_new / 100,
    }
