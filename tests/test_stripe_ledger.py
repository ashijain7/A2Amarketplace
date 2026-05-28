import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_stripe():
    with patch("resources_server.stripe_ledger.stripe") as m:
        yield m


def test_create_agent_accounts_creates_one_per_agent(mock_stripe):
    from resources_server.stripe_ledger import create_agent_accounts
    mock_stripe.Customer.create.side_effect = [
        MagicMock(id="cus_kai"),
        MagicMock(id="cus_rex"),
    ]
    result = create_agent_accounts(["Kai", "Rex"], config_name="focal_S_vs_S_pay", set_id="01", phase=1)
    assert result == {"Kai": "cus_kai", "Rex": "cus_rex"}
    assert mock_stripe.Customer.create.call_count == 2


def test_get_balance_cents(mock_stripe):
    from resources_server.stripe_ledger import get_balance_cents
    mock_stripe.Customer.retrieve.return_value = MagicMock(balance=15000)
    result = get_balance_cents("cus_kai")
    assert result == 15000
    mock_stripe.Customer.retrieve.assert_called_once_with("cus_kai")


def test_transfer_success(mock_stripe):
    from resources_server.stripe_ledger import transfer
    # First retrieve: balance check. Next two: read updated balances after transactions.
    mock_stripe.Customer.retrieve.side_effect = [
        MagicMock(balance=15000),   # sender balance check
        MagicMock(balance=10500),   # sender new balance read-back
        MagicMock(balance=19500),   # receiver new balance read-back
    ]
    result = transfer("cus_kai", "cus_rex", amount_cents=4500)
    assert result["success"] is True
    assert result["amount"] == 45.0
    assert result["sender_new_balance"] == 105.0
    assert result["receiver_new_balance"] == 195.0
    # Two CustomerBalanceTransaction.create calls: one debit, one credit
    assert mock_stripe.Customer.create_balance_transaction.call_count == 2


def test_transfer_insufficient_funds(mock_stripe):
    from resources_server.stripe_ledger import transfer
    mock_stripe.Customer.retrieve.return_value = MagicMock(balance=3000)
    result = transfer("cus_kai", "cus_rex", amount_cents=4500)
    assert result["success"] is False
    assert result["error"] == "insufficient_funds"
    assert result["balance"] == 30.0
    assert result["shortfall"] == 15.0
    mock_stripe.Customer.create_balance_transaction.assert_not_called()


def test_transfer_never_writes_negative_balance(mock_stripe):
    from resources_server.stripe_ledger import transfer
    mock_stripe.Customer.retrieve.side_effect = [
        MagicMock(balance=4500),   # balance check — exactly enough
        MagicMock(balance=0),      # sender new balance read-back
        MagicMock(balance=9000),   # receiver new balance read-back
    ]
    result = transfer("cus_kai", "cus_rex", amount_cents=4500)
    assert result["success"] is True
    assert result["sender_new_balance"] == 0.0
    # Debit call should have amount=-4500
    debit_call = mock_stripe.Customer.create_balance_transaction.call_args_list[0]
    assert debit_call[1]["amount"] == -4500
