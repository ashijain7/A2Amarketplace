"""
Stripe payment client for the marketplace payment extension.

All Stripe API calls are isolated here. When enable_payments=False,
this module is never imported — existing runs have zero dependency on it.

Balance unit: Stripe uses integer cents. All public functions that take
dollar amounts accept cents to avoid float rounding bugs.
"""

import os
import stripe
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STARTING_BALANCE_CENTS = 15000  # $150 per agent


def create_agent_accounts(agent_names: list[str], session_id: str) -> dict[str, str]:
    """Create one Stripe Customer per agent name.

    Returns {agent_name: stripe_customer_id}.
    Names each customer as "AgentName [session_prefix]" for dashboard readability.
    Raises stripe.error.StripeError if any creation fails — caller should abort session.
    """
    accounts = {}
    for name in agent_names:
        customer = stripe.Customer.create(
            name=f"{name} [{session_id[:8]}]",
            metadata={"agent_name": name, "session_id": session_id},
            balance=STARTING_BALANCE_CENTS,
        )
        accounts[name] = customer.id
    return accounts


def get_balance_cents(customer_id: str) -> int:
    """Return the agent's current balance in cents, direct from Stripe."""
    customer = stripe.Customer.retrieve(customer_id)
    return customer.balance


def transfer(from_customer_id: str, to_customer_id: str, amount_cents: int) -> dict:
    """Move amount_cents from sender to receiver via Stripe balance modification.

    Reads both balances fresh from Stripe before writing.
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

    new_sender_balance = sender_balance - amount_cents
    assert new_sender_balance >= 0, "balance guard: would write negative"

    stripe.Customer.modify(from_customer_id, balance=new_sender_balance)

    receiver = stripe.Customer.retrieve(to_customer_id)
    new_receiver_balance = receiver.balance + amount_cents
    stripe.Customer.modify(to_customer_id, balance=new_receiver_balance)

    return {
        "success": True,
        "amount": amount_cents / 100,
        "sender_new_balance": new_sender_balance / 100,
        "receiver_new_balance": new_receiver_balance / 100,
    }
