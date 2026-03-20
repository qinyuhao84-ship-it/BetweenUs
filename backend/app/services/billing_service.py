from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.models import EntitlementModel, IAPTransactionModel
from app.db.session import session_scope
from app.services.pricing import BillingSettlement, settle_usage


@dataclass
class Entitlement:
    subscription_units_left: int
    payg_units_left: int


class BillingService:
    def __init__(self) -> None:
        self._default_sub_units = get_settings().default_subscription_units

    def get_or_create(self, user_id: str) -> Entitlement:
        with session_scope() as db:
            row = self._get_or_create_row(db=db, user_id=user_id)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_entitlement(row)

    def add_payg_units(self, user_id: str, units: int) -> Entitlement:
        with session_scope() as db:
            row = self._get_or_create_row(db=db, user_id=user_id)
            row.payg_units_left += max(units, 0)
            row.updated_at = datetime.now(UTC)
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_entitlement(row)

    def apply_iap_transaction(self, user_id: str, transaction_id: str, units: int) -> tuple[Entitlement, bool]:
        with session_scope() as db:
            existing = db.get(IAPTransactionModel, transaction_id)
            entitlement = self._get_or_create_row(db=db, user_id=user_id)
            if existing is not None:
                db.add(entitlement)
                db.commit()
                db.refresh(entitlement)
                return self._to_entitlement(entitlement), False

            db.add(
                IAPTransactionModel(
                    transaction_id=transaction_id,
                    user_id=user_id,
                    units=max(units, 0),
                    created_at=datetime.now(UTC),
                )
            )
            entitlement.payg_units_left += max(units, 0)
            entitlement.updated_at = datetime.now(UTC)
            db.add(entitlement)
            db.commit()
            db.refresh(entitlement)
            return self._to_entitlement(entitlement), True

    def settle(self, user_id: str, duration_minutes: int) -> BillingSettlement:
        with session_scope() as db:
            entitlement = self._get_or_create_row(db=db, user_id=user_id)
            result = settle_usage(
                duration_minutes=duration_minutes,
                subscription_units_left=entitlement.subscription_units_left,
                payg_units_left=entitlement.payg_units_left,
            )
            if result.approved:
                entitlement.subscription_units_left = result.remaining_subscription_units
                entitlement.payg_units_left = result.remaining_payg_units
                entitlement.updated_at = datetime.now(UTC)
                db.add(entitlement)
                db.commit()
                db.refresh(entitlement)
            return result

    def _get_or_create_row(self, db, user_id: str) -> EntitlementModel:
        row = db.get(EntitlementModel, user_id)
        if row is None:
            row = EntitlementModel(
                user_id=user_id,
                subscription_units_left=self._default_sub_units,
                payg_units_left=0,
                updated_at=datetime.now(UTC),
            )
            db.add(row)
            db.flush()
        return row

    @staticmethod
    def _to_entitlement(row: EntitlementModel) -> Entitlement:
        return Entitlement(
            subscription_units_left=row.subscription_units_left,
            payg_units_left=row.payg_units_left,
        )
