from app.services.pricing import compute_usage_units, settle_usage


def test_compute_usage_units_rounds_up_to_one_hour_blocks():
    assert compute_usage_units(45) == 1
    assert compute_usage_units(60) == 1
    assert compute_usage_units(61) == 2


def test_settle_usage_consumes_subscription_then_payg():
    result = settle_usage(duration_minutes=130, subscription_units_left=2, payg_units_left=5)

    assert result.request_units == 3
    assert result.subscription_units_used == 2
    assert result.payg_units_used == 1
    assert result.remaining_subscription_units == 0
    assert result.remaining_payg_units == 4


def test_settle_usage_rejects_if_balance_not_enough():
    result = settle_usage(duration_minutes=130, subscription_units_left=1, payg_units_left=1)

    assert result.request_units == 3
    assert result.approved is False
    assert result.shortage_units == 1
