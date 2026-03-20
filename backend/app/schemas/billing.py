from pydantic import BaseModel, Field


class EntitlementResponse(BaseModel):
    subscription_units_left: int
    payg_units_left: int


class VerifyIAPRequest(BaseModel):
    product_id: str = Field(min_length=3)
    transaction_id: str = Field(min_length=3)


class VerifyIAPResponse(BaseModel):
    success: bool
    applied: bool
    entitlement: EntitlementResponse
