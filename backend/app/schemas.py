from decimal import Decimal
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    sku: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock: Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
    barcode: str | None = Field(default=None, max_length=128)
    imei: str | None = Field(default=None, min_length=14, max_length=32, pattern=r"^[0-9A-Za-z-]+$")

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.upper()


class ProductResponse(ProductInput):
    model_config = ConfigDict(from_attributes=True)
    id: int

class LoginInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=200)

class LoginResponse(BaseModel):
    token: str
    email: str
    role: str


class SetupStatusResponse(BaseModel):
    needs_owner_setup: bool


class OwnerSetupInput(LoginInput):
    name: str = Field(min_length=1, max_length=120)


class UserAccountInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=200)
    role: str = Field(pattern=r"^(admin|staff)$")


class UserAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserAccountStatusInput(BaseModel):
    is_active: bool


class CustomerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    contact_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    email: str = Field(min_length=3, max_length=254)


class CustomerResponse(CustomerInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class OrderLineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: Annotated[int, Field(strict=True, ge=1)]
    quantity: Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
    phone_unit_id: Annotated[int | None, Field(strict=True, ge=1)] = None


class OrderDraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: Annotated[int, Field(strict=True, ge=1)]
    items: list[OrderLineInput] = Field(min_length=1, max_length=100)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    phone_unit_id: int | None = None
    sku: str
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class PhoneUnitInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    product_id: Annotated[int, Field(strict=True, ge=1)]
    imei: str = Field(min_length=14, max_length=32, pattern=r"^[0-9A-Za-z-]+$")
    colour: str = Field(min_length=1, max_length=80)
    storage: str = Field(min_length=1, max_length=40)
    supplier_name: str | None = Field(default=None, max_length=120)
    purchase_cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    warranty_status: str = Field(default="Standard warranty", min_length=1, max_length=80)


class PhoneUnitResponse(PhoneUnitInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer: CustomerResponse
    status: str
    total: Decimal
    created_at: datetime
    items: list[OrderItemResponse]


class OrderActionResponse(OrderResponse):
    message: str


class IntakeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message: str = Field(min_length=1, max_length=4_000)


class IntakeProductSuggestion(BaseModel):
    id: int
    sku: str
    name: str
    stock: int


class IntakeItem(BaseModel):
    requested_description: str
    quantity: int | None
    suggested_product: IntakeProductSuggestion | None
    match_status: str
    evidence: str


class IntakeResponse(BaseModel):
    mode: str = Field(pattern=r"^(demo|live)$")
    items: list[IntakeItem]
    notes: list[str]

class RestockRecommendation(BaseModel):
    product_id: int
    sku: str
    name: str
    stock: int
    weekly_sales: int
    reorder_quantity: int
    reason: str

class DailyOperationsResponse(BaseModel):
    period_days: int
    dispatched_orders: int
    revenue: Decimal
    recommendations: list[RestockRecommendation]
    report: str

class SavedDailyReport(BaseModel):
    id: int
    report_date: str
    report: str
    created_at: datetime

class RestockRuleInput(BaseModel):
    threshold: Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]

class RestockRuleResponse(RestockRuleInput):
    product_id: int

class RestockDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern=r"^(accepted|dismissed)$")
    suggested_quantity: Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]


class RestockDecisionResponse(RestockDecisionInput):
    id: int
    product_id: int
    decision_date: str
    decided_at: datetime


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    sku: str
    product_name: str
    order_id: int | None
    quantity_delta: int
    reason: str
    created_at: datetime


class WhatsAppMessageResponse(BaseModel):
    id: int
    external_message_id: str
    sender_phone: str
    message_text: str
    analysis: dict
    received_at: datetime

class IntegrationSettingsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    whatsapp_business_number: str = Field(max_length=40)
    whatsapp_intro: str = Field(min_length=10, max_length=600)

class IntegrationSettingsResponse(IntegrationSettingsInput):
    id: int


class ProductImportRow(BaseModel):
    row: int
    sku: str
    name: str
    category: str
    price: Decimal
    stock: int
    action: str


class ProductImportPreview(BaseModel):
    valid_rows: int
    errors: list[str]
    rows: list[ProductImportRow]


class SupplierInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    contact_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    email: str = Field(min_length=3, max_length=254)
    supplied_skus: str = Field(max_length=4000)
    lead_time_days: Annotated[int, Field(strict=True, ge=0, le=365)]

class SupplierResponse(SupplierInput):
    model_config = ConfigDict(from_attributes=True)
    id: int

class ImportRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    imported_by: str
    created_rows: int
    updated_rows: int
    imported_at: datetime

class SalesProductMetric(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity_sold: int
    revenue: Decimal

class SalesAnalyticsResponse(BaseModel):
    period_days: int
    best_sellers: list[SalesProductMetric]
    slow_movers: list[SalesProductMetric]
    no_sale_products: list[SalesProductMetric]
    category_revenue: dict[str, Decimal]

class AlertResponse(BaseModel):
    severity: str
    title: str
    detail: str
    href: str
