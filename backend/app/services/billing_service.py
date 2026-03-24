from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.models import EntitlementModel, IAPTransactionModel
from app.db.session import session_scope
from app.services.apple_services import AppStoreVerificationService, DecodedAppStoreNotification, VerifiedAppStoreTransaction
from app.services.pricing import BillingSettlement, settle_usage


@dataclass
class Entitlement:
    subscription_units_left: int
    payg_units_left: int


@dataclass(frozen=True)
class TopupPackage:
    package_id: str
    title: str
    units: int
    amount_cny: int

    @property
    def price_label(self) -> str:
        return f"¥{self.amount_cny / 100:.2f}"


class BillingService:
    def __init__(self) -> None:
        self._default_sub_units = get_settings().default_subscription_units
        self._settings = get_settings()
        self._app_store_service = AppStoreVerificationService(settings=self._settings)
        self._packages = {
            "betweenus.payg.1": TopupPackage(package_id="betweenus.payg.1", title="单次包", units=1, amount_cny=0),
            "betweenus.payg.2": TopupPackage(package_id="betweenus.payg.2", title="双次包", units=2, amount_cny=0),
            "betweenus.payg.3": TopupPackage(package_id="betweenus.payg.3", title="三次包", units=3, amount_cny=0),
        }

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

    def list_packages(self) -> list[TopupPackage]:
        return sorted(self._packages.values(), key=lambda x: x.units)

    def verify_signed_transaction(self, signed_transaction_info: str) -> VerifiedAppStoreTransaction:
        return self._app_store_service.verify_signed_transaction(signed_transaction_info)

    def verify_and_decode_notification(self, signed_payload: str) -> DecodedAppStoreNotification:
        return self._app_store_service.verify_notification(signed_payload)

    def apply_verified_transaction(
        self,
        user_id: str,
        transaction: VerifiedAppStoreTransaction,
    ) -> tuple[Entitlement, bool]:
        pack = self._packages.get(transaction.product_id)
        if pack is None:
            raise ValueError("App Store 商品不存在")

        with session_scope() as db:
            row = db.get(IAPTransactionModel, transaction.transaction_id)
            entitlement = self._get_or_create_row(db=db, user_id=user_id)

            if row is None:
                row = IAPTransactionModel(
                    transaction_id=transaction.transaction_id,
                    user_id=user_id,
                    original_transaction_id=transaction.original_transaction_id,
                    product_id=transaction.product_id,
                    signed_transaction_info=transaction.signed_transaction_info,
                    units=pack.units,
                    environment=transaction.environment,
                    purchase_date_ms=transaction.purchase_date_ms,
                    signed_date_ms=transaction.signed_date_ms,
                    revocation_date_ms=transaction.revocation_date_ms or 0,
                    revocation_reason=transaction.revocation_reason if transaction.revocation_reason is not None else -1,
                    revoked=transaction.revocation_date_ms is not None,
                    created_at=datetime.now(UTC),
                )
                db.add(row)
                if transaction.revocation_date_ms is None:
                    entitlement.payg_units_left += pack.units
                    entitlement.updated_at = datetime.now(UTC)
                    db.add(entitlement)
                    db.commit()
                    db.refresh(entitlement)
                    return self._to_entitlement(entitlement), True

                db.add(entitlement)
                db.commit()
                db.refresh(entitlement)
                return self._to_entitlement(entitlement), False

            if not row.user_id:
                row.user_id = user_id
            elif row.user_id != user_id:
                raise PermissionError("该交易属于其他账号")

            changed = False
            row.original_transaction_id = transaction.original_transaction_id
            row.product_id = transaction.product_id
            row.signed_transaction_info = transaction.signed_transaction_info
            row.environment = transaction.environment
            row.purchase_date_ms = transaction.purchase_date_ms
            row.signed_date_ms = transaction.signed_date_ms
            row.revocation_reason = transaction.revocation_reason if transaction.revocation_reason is not None else -1

            if transaction.revocation_date_ms is not None and not row.revoked:
                row.revoked = True
                row.revocation_date_ms = transaction.revocation_date_ms
                entitlement.payg_units_left = max(entitlement.payg_units_left - row.units, 0)
                entitlement.updated_at = datetime.now(UTC)
                changed = True
            elif transaction.revocation_date_ms is None and row.revoked:
                row.revoked = False
                row.revocation_date_ms = 0
                entitlement.payg_units_left += row.units
                entitlement.updated_at = datetime.now(UTC)
                changed = True

            db.add(row)
            db.add(entitlement)
            db.commit()
            db.refresh(entitlement)
            return self._to_entitlement(entitlement), changed

    def apply_app_store_notification(self, notification: DecodedAppStoreNotification) -> tuple[Entitlement | None, bool]:
        transaction = self.verify_signed_transaction(notification.signed_transaction_info)
        with session_scope() as db:
            row = db.get(IAPTransactionModel, transaction.transaction_id)
            if row is None:
                pack = self._packages.get(transaction.product_id)
                db.add(
                    IAPTransactionModel(
                        transaction_id=transaction.transaction_id,
                        user_id="",
                        original_transaction_id=transaction.original_transaction_id,
                        product_id=transaction.product_id,
                        signed_transaction_info=transaction.signed_transaction_info,
                        units=pack.units if pack else 0,
                        environment=transaction.environment,
                        purchase_date_ms=transaction.purchase_date_ms,
                        signed_date_ms=transaction.signed_date_ms,
                        revocation_date_ms=transaction.revocation_date_ms or 0,
                        revocation_reason=transaction.revocation_reason if transaction.revocation_reason is not None else -1,
                        revoked=transaction.revocation_date_ms is not None,
                        created_at=datetime.now(UTC),
                    )
                )
                db.commit()
                return None, False

            user_id = row.user_id
        return self.apply_verified_transaction(user_id=user_id, transaction=transaction)

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
