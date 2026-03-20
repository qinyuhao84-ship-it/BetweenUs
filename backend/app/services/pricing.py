from dataclasses import dataclass
from math import ceil


@dataclass
class BillingSettlement:
    request_units: int
    subscription_units_used: int
    payg_units_used: int
    remaining_subscription_units: int
    remaining_payg_units: int
    approved: bool
    shortage_units: int


def compute_usage_units(duration_minutes: int) -> int:
    if duration_minutes <= 0:
        return 0
    return ceil(duration_minutes / 60)


def settle_usage(
    duration_minutes: int,
    subscription_units_left: int,
    payg_units_left: int,
) -> BillingSettlement:
    request_units = compute_usage_units(duration_minutes)
    subscription_used = min(subscription_units_left, request_units)
    remaining_need = request_units - subscription_used
    payg_used = min(payg_units_left, remaining_need)
    shortage = remaining_need - payg_used

    return BillingSettlement(
        request_units=request_units,
        subscription_units_used=subscription_used,
        payg_units_used=payg_used,
        remaining_subscription_units=subscription_units_left - subscription_used,
        remaining_payg_units=payg_units_left - payg_used,
        approved=shortage == 0,
        shortage_units=shortage,
    )
