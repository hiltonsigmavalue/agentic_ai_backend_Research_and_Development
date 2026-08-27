from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field

class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    productinfo: str = Field(min_length=1, max_length=255)
    firstname: str = Field(min_length=1, max_length=100)
    lastname: str | None = Field(default=None, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    payment_category: str = Field(default="domestic", pattern="^(domestic|international)$")
    address1: str | None = Field(default=None, max_length=255)
    address2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    zipcode: str | None = Field(default=None, max_length=20)

class CreatePaymentResponse(BaseModel):
    txnid: str
    payu_url: str
    fields: dict[str, str]

class RefundRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
