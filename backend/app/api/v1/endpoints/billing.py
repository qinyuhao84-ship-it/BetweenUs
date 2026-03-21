from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id
from app.schemas.billing import (
    ConfirmPaymentRequest,
    ConfirmPaymentResponse,
    CreatePaymentOrderRequest,
    CreatePaymentOrderResponse,
    EntitlementResponse,
    TopupPackageResponse,
    VerifyIAPRequest,
    VerifyIAPResponse,
)
from app.services.container import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])

_PRODUCT_TO_UNITS = {
    "betweenus.payg.1": 1,
    "betweenus.payg.3": 3,
    "betweenus.payg.10": 10,
}


@router.get("/entitlements", response_model=EntitlementResponse)
def get_entitlements(user_id: str = Depends(get_current_user_id)) -> EntitlementResponse:
    entitlement = billing_service.get_or_create(user_id)
    return EntitlementResponse(
        subscription_units_left=entitlement.subscription_units_left,
        payg_units_left=entitlement.payg_units_left,
    )


@router.post("/iap/verify", response_model=VerifyIAPResponse)
def verify_iap(payload: VerifyIAPRequest, user_id: str = Depends(get_current_user_id)) -> VerifyIAPResponse:
    units = _PRODUCT_TO_UNITS.get(payload.product_id, 0)
    entitlement, applied = billing_service.apply_iap_transaction(
        user_id=user_id,
        transaction_id=payload.transaction_id,
        units=units,
    )
    return VerifyIAPResponse(
        success=True,
        applied=applied,
        entitlement=EntitlementResponse(
            subscription_units_left=entitlement.subscription_units_left,
            payg_units_left=entitlement.payg_units_left,
        ),
    )


@router.get("/packages", response_model=list[TopupPackageResponse])
def list_topup_packages() -> list[TopupPackageResponse]:
    return [
        TopupPackageResponse(
            package_id=item.package_id,
            title=item.title,
            units=item.units,
            amount_cny=item.amount_cny,
            price_label=item.price_label,
        )
        for item in billing_service.list_packages()
    ]


@router.post("/payments/create", response_model=CreatePaymentOrderResponse)
def create_payment_order(
    payload: CreatePaymentOrderRequest,
    user_id: str = Depends(get_current_user_id),
) -> CreatePaymentOrderResponse:
    try:
        order = billing_service.create_payment_order(
            user_id=user_id,
            package_id=payload.package_id,
            channel=payload.channel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreatePaymentOrderResponse(
        order_no=order.order_no,
        channel=order.channel,
        package_id=order.package_id,
        units=order.units,
        amount_cny=order.amount_cny,
        status=order.status,
        payment_payload=order.payment_payload,
        expires_at=order.expires_at.isoformat(),
    )


@router.post("/payments/confirm", response_model=ConfirmPaymentResponse)
def confirm_payment(
    payload: ConfirmPaymentRequest,
    user_id: str = Depends(get_current_user_id),
) -> ConfirmPaymentResponse:
    try:
        entitlement, applied = billing_service.confirm_payment(
            user_id=user_id,
            order_no=payload.order_no,
            provider_order_id=payload.provider_order_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="订单不存在") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return ConfirmPaymentResponse(
        success=True,
        applied=applied,
        entitlement=EntitlementResponse(
            subscription_units_left=entitlement.subscription_units_left,
            payg_units_left=entitlement.payg_units_left,
        ),
    )
