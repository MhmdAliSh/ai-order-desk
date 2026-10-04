from decimal import Decimal

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="staff")
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="positive_price"),
        CheckConstraint("stock >= 0", name="positive_stock"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    price_cents: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    barcode: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    imei: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)

    @property
    def price(self) -> Decimal:
        return (Decimal(self.price_cents) / 100).quantize(Decimal("0.01"))


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    contact_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str] = mapped_column(String(254))
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    total_cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    movements: Mapped[list["StockMovement"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="positive_order_quantity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    sku: Mapped[str] = mapped_column(String(64))
    product_name: Mapped[str] = mapped_column(String(200))
    unit_price_cents: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    order: Mapped[Order] = relationship(back_populates="items")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    quantity_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    order: Mapped[Order | None] = relationship(back_populates="movements")

class DailyReport(Base):
    __tablename__ = "daily_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    report_date: Mapped[str] = mapped_column(String(10), unique=True)
    report: Mapped[str] = mapped_column(Text)
    snapshot_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class RestockRule(Base):
    __tablename__ = "restock_rules"
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    threshold: Mapped[int] = mapped_column(Integer)

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    contact_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str] = mapped_column(String(254))
    supplied_skus: Mapped[str] = mapped_column(Text, default="")
    lead_time_days: Mapped[int] = mapped_column(Integer, default=3)


class ImportRecord(Base):
    __tablename__ = "import_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    imported_by: Mapped[str] = mapped_column(String(254))
    created_rows: Mapped[int] = mapped_column(Integer)
    updated_rows: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class RestockDecision(Base):
    __tablename__ = "restock_decisions"
    __table_args__ = (UniqueConstraint("product_id", "decision_date", name="one_restock_decision_per_product_per_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    decision: Mapped[str] = mapped_column(String(20))
    suggested_quantity: Mapped[int] = mapped_column(Integer)
    decision_date: Mapped[str] = mapped_column(String(10))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class WhatsAppInboundMessage(Base):
    __tablename__ = "whatsapp_inbound_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_message_id: Mapped[str] = mapped_column(String(128), unique=True)
    sender_phone: Mapped[str] = mapped_column(String(40))
    message_text: Mapped[str] = mapped_column(Text)
    analysis_json: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

class IntegrationSettings(Base):
    __tablename__ = "integration_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    whatsapp_business_number: Mapped[str] = mapped_column(String(40), default="")
    whatsapp_intro: Mapped[str] = mapped_column(Text, default="")
