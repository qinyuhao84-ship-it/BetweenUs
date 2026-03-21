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


class TopupPackageResponse(BaseModel):
    package_id: str
    title: str
    units: int
    amount_cny: int
    price_label: str


class CreatePaymentOrderRequest(BaseModel):
    package_id: str = Field(min_length=3)
    channel: str = Field(pattern="^(alipay|wechat)$")


class CreatePaymentOrderResponse(BaseModel):
    order_no: str
    channel: str
    package_id: str
    units: int
    amount_cny: int
    status: str
    payment_payload: str
    expires_at: str


class ConfirmPaymentRequest(BaseModel):
    order_no: str = Field(min_length=6)
    provider_order_id: str = ""


class ConfirmPaymentResponse(BaseModel):
    success: bool
    applied: bool
    entitlement: EntitlementResponse
