from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id
from app.schemas.billing import (
    AppStoreNotificationRequest,
    AppStoreNotificationResponse,
    EntitlementResponse,
    TopupPackageResponse,
    VerifyIAPRequest,
    VerifyIAPResponse,
)
from app.services.apple_services import AppleServiceError
from app.services.container import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/entitlements", response_model=EntitlementResponse)
def get_entitlements(user_id: str = Depends(get_current_user_id)) -> EntitlementResponse:
    entitlement = billing_service.get_or_create(user_id)
    return EntitlementResponse(
        subscription_units_left=entitlement.subscription_units_left,
        payg_units_left=entitlement.payg_units_left,
    )


@router.post("/iap/verify", response_model=VerifyIAPResponse)
def verify_iap(payload: VerifyIAPRequest, user_id: str = Depends(get_current_user_id)) -> VerifyIAPResponse:
    try:
        transaction = billing_service.verify_signed_transaction(payload.signed_transaction_info)
        entitlement, applied = billing_service.apply_verified_transaction(user_id=user_id, transaction=transaction)
    except AppleServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
        )
        for item in billing_service.list_packages()
    ]


@router.post("/app-store-notifications", response_model=AppStoreNotificationResponse)
def app_store_notifications(payload: AppStoreNotificationRequest) -> AppStoreNotificationResponse:
    try:
        notification = billing_service.verify_and_decode_notification(payload.signed_payload)
        _entitlement, applied = billing_service.apply_app_store_notification(notification)
    except AppleServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AppStoreNotificationResponse(success=True, applied=applied)
