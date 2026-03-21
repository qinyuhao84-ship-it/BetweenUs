from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.db.models import EntitlementModel, IAPTransactionModel, PaymentOrderModel
from app.db.session import session_scope
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


@dataclass
class PaymentOrder:
    order_no: str
    channel: str
    package_id: str
    units: int
    amount_cny: int
    status: str
    payment_payload: str
    expires_at: datetime


class BillingService:
    def __init__(self) -> None:
        self._default_sub_units = get_settings().default_subscription_units
        self._settings = get_settings()
        self._packages = {
            "betweenus.payg.3": TopupPackage(package_id="betweenus.payg.3", title="轻量包", units=3, amount_cny=1990),
            "betweenus.payg.8": TopupPackage(package_id="betweenus.payg.8", title="标准包", units=8, amount_cny=4990),
            "betweenus.payg.20": TopupPackage(package_id="betweenus.payg.20", title="家庭包", units=20, amount_cny=10900),
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
        return sorted(self._packages.values(), key=lambda x: x.amount_cny)

    def create_payment_order(self, user_id: str, package_id: str, channel: str) -> PaymentOrder:
        if channel not in {"alipay", "wechat"}:
            raise ValueError("不支持的支付渠道")
        pack = self._packages.get(package_id)
        if pack is None:
            raise ValueError("套餐不存在")

        order_no = f"bu_{uuid4().hex[:24]}"
        now = datetime.now(UTC)
        expires_at = now.replace(microsecond=0)
        expires_at = expires_at.replace(second=(expires_at.second // 30) * 30)
        expires_at = expires_at + timedelta(minutes=15)

        payload = self._build_payment_payload(order_no=order_no, package=pack, channel=channel)

        with session_scope() as db:
            db.add(
                PaymentOrderModel(
                    order_no=order_no,
                    user_id=user_id,
                    package_id=pack.package_id,
                    channel=channel,
                    units=pack.units,
                    amount_cny=pack.amount_cny,
                    status="pending",
                    provider_order_id="",
                    payment_payload=payload,
                    created_at=now,
                    updated_at=now,
                )
            )
            db.commit()

        return PaymentOrder(
            order_no=order_no,
            channel=channel,
            package_id=pack.package_id,
            units=pack.units,
            amount_cny=pack.amount_cny,
            status="pending",
            payment_payload=payload,
            expires_at=expires_at,
        )

    def confirm_payment(self, user_id: str, order_no: str, provider_order_id: str = "") -> tuple[Entitlement, bool]:
        with session_scope() as db:
            row = db.get(PaymentOrderModel, order_no)
            if row is None:
                raise KeyError("订单不存在")
            if row.user_id != user_id:
                raise PermissionError("无权操作该订单")

            entitlement = self._get_or_create_row(db=db, user_id=user_id)
            if row.status == "paid":
                db.add(entitlement)
                db.commit()
                db.refresh(entitlement)
                return self._to_entitlement(entitlement), False

            row.status = "paid"
            row.provider_order_id = provider_order_id.strip()[:120]
            row.updated_at = datetime.now(UTC)
            entitlement.payg_units_left += max(row.units, 0)
            entitlement.updated_at = datetime.now(UTC)
            db.add(row)
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

    def _build_payment_payload(self, order_no: str, package: TopupPackage, channel: str) -> str:
        # 生产环境应替换为真实支付宝/微信下单结果。
        if self._settings.payment_mode == "real":
            if channel == "alipay":
                if not self._settings.alipay_app_id:
                    raise ValueError("支付宝配置不完整，请先设置 ALIPAY_APP_ID")
                return (
                    f"alipay://pay?order_no={order_no}&amount={package.amount_cny}&"
                    f"app_id={self._settings.alipay_app_id}"
                )
            if not self._settings.wechat_mch_id:
                raise ValueError("微信支付配置不完整，请先设置 WECHAT_MCH_ID")
            return (
                f"weixin://wxpay/bizpayurl?order_no={order_no}&amount={package.amount_cny}&"
                f"mch_id={self._settings.wechat_mch_id}"
            )

        return f"mock://pay?channel={channel}&order_no={order_no}&amount={package.amount_cny}"
