from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_id
from app.schemas.billing import EntitlementResponse, VerifyIAPRequest, VerifyIAPResponse
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
