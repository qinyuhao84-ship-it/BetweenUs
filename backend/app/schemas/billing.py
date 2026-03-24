from pydantic import BaseModel, Field


class EntitlementResponse(BaseModel):
    subscription_units_left: int
    payg_units_left: int


class VerifyIAPRequest(BaseModel):
    signed_transaction_info: str = Field(min_length=16)


class VerifyIAPResponse(BaseModel):
    success: bool
    applied: bool
    entitlement: EntitlementResponse


class TopupPackageResponse(BaseModel):
    package_id: str
    title: str
    units: int


class AppStoreNotificationRequest(BaseModel):
    signed_payload: str = Field(min_length=16)


class AppStoreNotificationResponse(BaseModel):
    success: bool
    applied: bool
