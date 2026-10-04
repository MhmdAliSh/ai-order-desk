from contextlib import asynccontextmanager
import json
import csv
from io import StringIO
from datetime import UTC, datetime
from decimal import Decimal
import hmac
import os
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, func, inspect, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from .models import Base, Customer, DailyReport, ImportRecord, IntegrationSettings, Order, OrderItem, Product, RestockDecision, RestockRule, StockMovement, Supplier, UserAccount, WhatsAppInboundMessage
from .intake import RequestedItem, analyze_message
from .intake_provider import IntakeProviderError, extract_requested_items as extract_live_requested_items
from .auth import hash_password, issue_account_token, issue_token, verify_password, verify_token
from .operations import daily_summary, operational_alerts, sales_analytics, save_daily_report
from .whatsapp import ingest_messages, verify_signature
from .schemas import (
    CustomerInput,
    CustomerResponse,
    IntakeRequest,
    IntakeResponse,
    LoginInput,
    LoginResponse,
    OrderDraftInput,
    OrderActionResponse,
    OrderResponse,
    ProductInput,
    ProductResponse,
    DailyOperationsResponse,
    SavedDailyReport,
    RestockRuleInput,
    RestockRuleResponse,
    RestockDecisionInput,
    RestockDecisionResponse,
    WhatsAppMessageResponse,
    StockMovementResponse,
    IntegrationSettingsInput,
    IntegrationSettingsResponse,
    OwnerSetupInput,
    SetupStatusResponse,
    UserAccountInput,
    UserAccountResponse,
    UserAccountStatusInput,
    ProductImportPreview,
    ImportRecordResponse,
    SupplierInput,
    SupplierResponse,
    SalesAnalyticsResponse,
    AlertResponse,
)

DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "orders.sqlite3"


def create_app(
    database_url: str | None = None,
    intake_extractor: Callable[[str], list[RequestedItem]] | None = None,
) -> FastAPI:
    if database_url is None:
        DEFAULT_DATABASE.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{DEFAULT_DATABASE.as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    sessions = sessionmaker(bind=engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        columns = {column["name"] for column in inspect(engine).get_columns("products")}
        with engine.begin() as connection:
            if "barcode" not in columns: connection.execute(text("ALTER TABLE products ADD COLUMN barcode VARCHAR(128)"))
            if "imei" not in columns: connection.execute(text("ALTER TABLE products ADD COLUMN imei VARCHAR(32)"))
        yield
        engine.dispose()

    app = FastAPI(title="AI Order Desk", version="0.1.0", lifespan=lifespan)
    bearer = HTTPBearer(auto_error=False)
    intake_mode = os.getenv("AI_INTAKE_MODE", "demo").lower()
    if intake_mode not in {"demo", "live"}:
        raise ValueError("AI_INTAKE_MODE must be 'demo' or 'live'")
    if intake_mode == "live" and intake_extractor is None:
        intake_extractor = extract_live_requested_items

    def get_session():
        with sessions() as session:
            yield session

    SessionDep = Annotated[Session, Depends(get_session)]
    def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), session: SessionDep = None) -> dict[str, str]:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Sign in is required")
        payload = verify_token(credentials.credentials)
        account_id = payload.get("account_id")
        if account_id is not None:
            account = session.get(UserAccount, account_id)
            if account is None or not account.is_active or account.email != payload["sub"] or account.role != payload["role"]:
                raise HTTPException(status_code=401, detail="Your account is no longer active")
        return {"email": str(payload["sub"]), "role": str(payload["role"])}

    UserDep = Annotated[dict[str, str], Depends(require_user)]

    def require_admin(user: UserDep) -> dict[str, str]:
        if user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Administrator access is required")
        return user

    AdminDep = Annotated[dict[str, str], Depends(require_admin)]

    def find_product(product_id: int, session: Session) -> Product:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def save_product(product: Product, body: ProductInput, session: Session) -> Product:
        product.sku = body.sku
        product.name = body.name
        product.category = body.category
        product.price_cents = int(body.price * 100)
        product.stock = body.stock
        product.barcode = body.barcode or None
        product.imei = body.imei or None
        session.add(product)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="A product with this SKU already exists") from None
        session.refresh(product)
        return product

    def parse_product_import(contents: str, session: Session) -> tuple[list[dict], list[str]]:
        reader = csv.DictReader(StringIO(contents))
        expected = {"sku", "name", "category", "price", "stock"}
        if reader.fieldnames is None or {name.strip().lower() for name in reader.fieldnames} != expected:
            return [], ["CSV must use exactly these headers: sku, name, category, price, stock."]
        rows, errors = [], []
        for index, raw in enumerate(reader, start=2):
            try:
                sku = (raw.get("sku") or "").strip().upper()
                name = (raw.get("name") or "").strip()
                category = (raw.get("category") or "").strip()
                price = Decimal((raw.get("price") or "").strip())
                stock = int((raw.get("stock") or "").strip())
                if not sku or not name or not category or price < 0 or stock < 0:
                    raise ValueError
                rows.append({"row": index, "sku": sku, "name": name, "category": category, "price": price, "stock": stock, "action": "update" if session.scalar(select(Product.id).where(Product.sku == sku)) else "create"})
            except (ValueError, ArithmeticError):
                errors.append(f"Row {index}: SKU, name, category, a non-negative price, and a non-negative whole-number stock are required.")
        return rows, errors

    def find_customer(customer_id: int, session: Session) -> Customer:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    def to_order_response(order: Order) -> dict:
        return {
            "id": order.id,
            "customer": {
                "id": order.customer.id,
                "name": order.customer.name,
                "contact_name": order.customer.contact_name,
                "phone": order.customer.phone,
                "email": order.customer.email,
            },
            "status": order.status,
            "total": f"{order.total_cents / 100:.2f}",
            "created_at": order.created_at,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "sku": item.sku,
                    "product_name": item.product_name,
                    "unit_price": f"{item.unit_price_cents / 100:.2f}",
                    "quantity": item.quantity,
                    "line_total": f"{item.unit_price_cents * item.quantity / 100:.2f}",
                }
                for item in order.items
            ],
        }

    def read_order(order_id: int, session: Session) -> Order:
        statement = (
            select(Order)
            .options(selectinload(Order.customer), selectinload(Order.items))
            .where(Order.id == order_id)
        )
        order = session.scalar(statement)
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    def reserved_quantity(product_id: int, session: Session, excluding_order_id: int | None = None) -> int:
        statement = (
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .join(Order)
            .where(OrderItem.product_id == product_id, Order.status == "approved")
        )
        if excluding_order_id is not None:
            statement = statement.where(Order.id != excluding_order_id)
        return session.scalar(statement) or 0

    def to_order_action(order: Order, message: str) -> dict:
        return {**to_order_response(order), "message": message}

    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    @app.get("/auth/setup-status", response_model=SetupStatusResponse, tags=["Authentication"])
    def setup_status(session: SessionDep):
        return {"needs_owner_setup": session.scalar(select(UserAccount.id).limit(1)) is None}

    @app.post("/auth/setup-owner", response_model=LoginResponse, status_code=201, tags=["Authentication"])
    def setup_owner(body: OwnerSetupInput, session: SessionDep):
        if session.scalar(select(UserAccount.id).limit(1)) is not None:
            raise HTTPException(status_code=409, detail="An owner account already exists")
        account = UserAccount(name=body.name, email=body.email.lower(), role="admin", password_hash=hash_password(body.password))
        session.add(account)
        session.commit()
        session.refresh(account)
        return {"token": issue_account_token(account.email, account.role, account.id), "email": account.email, "role": account.role}

    @app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
    def login(body: LoginInput, session: SessionDep):
        account_count = session.scalar(select(func.count()).select_from(UserAccount)) or 0
        account = session.scalar(select(UserAccount).where(UserAccount.email == body.email.lower()))
        if account is not None:
            if not account.is_active or not verify_password(body.password, account.password_hash):
                raise HTTPException(status_code=401, detail="Incorrect email or password")
            return {"token": issue_account_token(account.email, account.role, account.id), "email": account.email, "role": account.role}
        if account_count:
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        token, role = issue_token(body.email, body.password)
        return {"token": token, "email": body.email, "role": role}

    @app.get("/users", response_model=list[UserAccountResponse], tags=["Team"])
    def list_users(session: SessionDep, _: AdminDep):
        return session.scalars(select(UserAccount).order_by(UserAccount.created_at)).all()

    @app.post("/users", response_model=UserAccountResponse, status_code=201, tags=["Team"])
    def create_user(body: UserAccountInput, session: SessionDep, _: AdminDep):
        account = UserAccount(name=body.name, email=body.email.lower(), role=body.role, password_hash=hash_password(body.password))
        session.add(account)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="An account with this email already exists") from None
        session.refresh(account)
        return account

    @app.patch("/users/{user_id}/status", response_model=UserAccountResponse, tags=["Team"])
    def set_user_status(user_id: int, body: UserAccountStatusInput, session: SessionDep, admin: AdminDep):
        account = session.get(UserAccount, user_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Team account not found")
        if account.email == admin["email"] and not body.is_active:
            raise HTTPException(status_code=422, detail="You cannot deactivate your own account")
        account.is_active = body.is_active
        session.commit()
        session.refresh(account)
        return account

    @app.get("/integrations/whatsapp/webhook", include_in_schema=False)
    def verify_whatsapp_webhook(mode: str = Query(alias="hub.mode"), verify_token: str = Query(alias="hub.verify_token"), challenge: str = Query(alias="hub.challenge")):
        if mode == "subscribe" and hmac.compare_digest(verify_token, os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")):
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="Webhook verification failed")

    @app.post("/integrations/whatsapp/webhook", include_in_schema=False)
    async def receive_whatsapp_webhook(request: Request, session: SessionDep):
        body = await request.body()
        verify_signature(body, request.headers.get("x-hub-signature-256"))
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid webhook JSON") from None
        return {"received": ingest_messages(payload, session)}

    @app.get("/integrations/whatsapp/messages", response_model=list[WhatsAppMessageResponse], tags=["WhatsApp"])
    def list_whatsapp_messages(session: SessionDep, _: UserDep):
        messages = session.query(WhatsAppInboundMessage).order_by(WhatsAppInboundMessage.received_at.desc()).all()
        return [{"id": message.id, "external_message_id": message.external_message_id, "sender_phone": message.sender_phone, "message_text": message.message_text, "analysis": json.loads(message.analysis_json), "received_at": message.received_at} for message in messages]

    @app.get("/settings/integrations", response_model=IntegrationSettingsResponse, tags=["Settings"])
    def get_integration_settings(session: SessionDep, _: AdminDep):
        settings = session.get(IntegrationSettings, 1)
        return settings or {"id": 1, "whatsapp_business_number": "", "whatsapp_intro": "Hi, I’m the AI assistant for Mobile & More. I can help check product availability, understand an order request, and ask our team for alternatives when an item is unavailable."}

    @app.put("/settings/integrations", response_model=IntegrationSettingsResponse, tags=["Settings"])
    def save_integration_settings(body: IntegrationSettingsInput, session: SessionDep, _: AdminDep):
        settings = session.get(IntegrationSettings, 1) or IntegrationSettings(id=1)
        settings.whatsapp_business_number = body.whatsapp_business_number
        settings.whatsapp_intro = body.whatsapp_intro
        session.add(settings)
        session.commit()
        session.refresh(settings)
        return settings

    @app.post("/imports/products/preview", response_model=ProductImportPreview, tags=["Imports"])
    async def preview_product_import(file: UploadFile = File(...), session: SessionDep = None, _: AdminDep = None):
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=422, detail="Upload a CSV file.")
        try:
            contents = (await file.read()).decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="CSV must use UTF-8 text.") from None
        rows, errors = parse_product_import(contents, session)
        return {"valid_rows": len(rows), "errors": errors, "rows": rows}

    @app.post("/imports/products/apply", response_model=ProductImportPreview, tags=["Imports"])
    async def apply_product_import(file: UploadFile = File(...), confirm: bool = Query(False), session: SessionDep = None, _: AdminDep = None):
        if not confirm:
            raise HTTPException(status_code=422, detail="Review the preview and confirm the import before applying it.")
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=422, detail="Upload a CSV file.")
        try:
            contents = (await file.read()).decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="CSV must use UTF-8 text.") from None
        rows, errors = parse_product_import(contents, session)
        if errors:
            raise HTTPException(status_code=422, detail={"message": "Fix CSV errors before importing.", "errors": errors})
        for row in rows:
            product = session.scalar(select(Product).where(Product.sku == row["sku"])) or Product(sku=row["sku"], name=row["name"], category=row["category"], price_cents=0, stock=0)
            product.name, product.category = row["name"], row["category"]
            product.price_cents, product.stock = int(row["price"] * 100), row["stock"]
            session.add(product)
        created_rows = sum(row["action"] == "create" for row in rows)
        session.add(ImportRecord(filename=file.filename, imported_by=_ ["email"], created_rows=created_rows, updated_rows=len(rows)-created_rows))
        session.commit()
        return {"valid_rows": len(rows), "errors": [], "rows": rows}

    @app.get("/imports/products/history", response_model=list[ImportRecordResponse], tags=["Imports"])
    def list_product_imports(session: SessionDep, _: AdminDep):
        return session.scalars(select(ImportRecord).order_by(ImportRecord.imported_at.desc())).all()

    @app.get("/suppliers", response_model=list[SupplierResponse], tags=["Suppliers"])
    def list_suppliers(session: SessionDep, _: AdminDep):
        return session.scalars(select(Supplier).order_by(Supplier.name)).all()

    @app.post("/suppliers", response_model=SupplierResponse, status_code=201, tags=["Suppliers"])
    def create_supplier(body: SupplierInput, session: SessionDep, _: AdminDep):
        supplier = Supplier(**body.model_dump()); session.add(supplier)
        try: session.commit()
        except IntegrityError:
            session.rollback(); raise HTTPException(status_code=409, detail="A supplier with this name already exists") from None
        session.refresh(supplier); return supplier

    @app.get("/operations/analytics", response_model=SalesAnalyticsResponse, tags=["Operations"])
    def get_sales_analytics(days: int = Query(7, ge=1, le=365), session: SessionDep = None, _: AdminDep = None):
        return sales_analytics(session, days)

    @app.get("/operations/alerts", response_model=list[AlertResponse], tags=["Operations"])
    def get_operational_alerts(session: SessionDep, _: UserDep):
        return operational_alerts(session)

    @app.get("/stock-movements", response_model=list[StockMovementResponse], tags=["Inventory"])
    def list_stock_movements(session: SessionDep, _: AdminDep):
        rows = session.execute(select(StockMovement, Product).join(Product, Product.id == StockMovement.product_id).order_by(StockMovement.created_at.desc())).all()
        return [{"id": movement.id, "product_id": movement.product_id, "sku": product.sku, "product_name": product.name, "order_id": movement.order_id, "quantity_delta": movement.quantity_delta, "reason": movement.reason, "created_at": movement.created_at} for movement, product in rows]

    @app.get("/operations/daily-summary", response_model=DailyOperationsResponse, tags=["Operations"])
    def get_daily_operations_summary(session: SessionDep, _: AdminDep):
        return daily_summary(session)

    @app.get("/operations/restock-decisions", response_model=list[RestockDecisionResponse], tags=["Operations"])
    def list_restock_decisions(session: SessionDep, _: AdminDep):
        return session.scalars(select(RestockDecision).order_by(RestockDecision.decided_at.desc())).all()

    @app.put("/operations/restock-decisions/{product_id}", response_model=RestockDecisionResponse, tags=["Operations"])
    def save_restock_decision(product_id: int, body: RestockDecisionInput, session: SessionDep, _: AdminDep):
        find_product(product_id, session)
        decision_date = datetime.now(UTC).date().isoformat()
        decision = session.scalar(select(RestockDecision).where(RestockDecision.product_id == product_id, RestockDecision.decision_date == decision_date))
        if decision is None:
            decision = RestockDecision(product_id=product_id, decision_date=decision_date, decision=body.decision, suggested_quantity=body.suggested_quantity)
            session.add(decision)
        else:
            decision.decision = body.decision
            decision.suggested_quantity = body.suggested_quantity
            decision.decided_at = datetime.now(UTC)
        session.commit()
        session.refresh(decision)
        return decision

    @app.post("/operations/daily-reports/run", response_model=SavedDailyReport, tags=["Operations"])
    def run_daily_report(session: SessionDep, _: AdminDep):
        return save_daily_report(session)

    @app.get("/operations/daily-reports", response_model=list[SavedDailyReport], tags=["Operations"])
    def list_daily_reports(session: SessionDep, _: AdminDep):
        return session.scalars(select(DailyReport).order_by(DailyReport.report_date.desc())).all()

    @app.get("/operations/restock-rules", response_model=list[RestockRuleResponse], tags=["Operations"])
    def list_restock_rules(session: SessionDep, _: AdminDep):
        return session.scalars(select(RestockRule).order_by(RestockRule.product_id)).all()

    @app.put("/operations/restock-rules/{product_id}", response_model=RestockRuleResponse, tags=["Operations"])
    def set_restock_rule(product_id: int, body: RestockRuleInput, session: SessionDep, _: AdminDep):
        find_product(product_id, session)
        rule = session.get(RestockRule, product_id)
        if rule is None:
            rule = RestockRule(product_id=product_id, threshold=body.threshold)
            session.add(rule)
        else:
            rule.threshold = body.threshold
        session.commit()
        session.refresh(rule)
        return rule

    @app.post("/products", response_model=ProductResponse, status_code=201, tags=["Products"])
    def create_product(body: ProductInput, session: SessionDep, _: AdminDep):
        return save_product(Product(), body, session)

    @app.get("/products", response_model=list[ProductResponse], tags=["Products"])
    def list_products(
        session: SessionDep,
        _: UserDep,
        q: Annotated[str | None, Query(max_length=200)] = None,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ):
        statement = select(Product).order_by(Product.id)
        if q and q.strip():
            term = q.strip()
            statement = statement.where(or_(
                Product.sku.icontains(term, autoescape=True),
                Product.name.icontains(term, autoescape=True),
                Product.category.icontains(term, autoescape=True),
            ))
        return session.scalars(statement.offset(offset).limit(limit)).all()

    @app.get("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
    def get_product(product_id: int, session: SessionDep, _: UserDep):
        return find_product(product_id, session)

    @app.put("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
    def replace_product(product_id: int, body: ProductInput, session: SessionDep, _: AdminDep):
        return save_product(find_product(product_id, session), body, session)

    @app.post("/customers", response_model=CustomerResponse, status_code=201, tags=["Customers"])
    def create_customer(body: CustomerInput, session: SessionDep, _: AdminDep):
        customer = Customer(**body.model_dump())
        session.add(customer)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="A customer with this name already exists") from None
        session.refresh(customer)
        return customer

    @app.put("/customers/{customer_id}", response_model=CustomerResponse, tags=["Customers"])
    def replace_customer(customer_id: int, body: CustomerInput, session: SessionDep, _: AdminDep):
        customer = find_customer(customer_id, session)
        for key, value in body.model_dump().items():
            setattr(customer, key, value)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="A customer with this name already exists") from None
        session.refresh(customer)
        return customer

    @app.get("/customers", response_model=list[CustomerResponse], tags=["Customers"])
    def list_customers(session: SessionDep, _: UserDep):
        return session.scalars(select(Customer).order_by(Customer.name)).all()

    @app.post("/order-intake/analyze", response_model=IntakeResponse, tags=["AI intake"])
    def analyze_order_intake(body: IntakeRequest, session: SessionDep, _: UserDep):
        products = session.scalars(select(Product).order_by(Product.id)).all()
        try:
            requested_items = intake_extractor(body.message) if intake_mode == "live" and intake_extractor else None
        except IntakeProviderError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        items, notes = analyze_message(body.message, products, requested_items)
        return {"mode": intake_mode, "items": items, "notes": notes}

    @app.post("/orders", response_model=OrderResponse, status_code=201, tags=["Orders"])
    def create_order_draft(body: OrderDraftInput, session: SessionDep, _: UserDep):
        customer = find_customer(body.customer_id, session)
        product_ids = [item.product_id for item in body.items]
        if len(set(product_ids)) != len(product_ids):
            raise HTTPException(status_code=422, detail="Each product may appear only once in an order")
        products = {
            product.id: product
            for product in session.scalars(
                select(Product).where(Product.id.in_(product_ids))
            ).all()
        }
        if len(products) != len(product_ids):
            raise HTTPException(status_code=422, detail="One or more products do not exist")
        unavailable = [
            item.product_id for item in body.items if item.quantity > products[item.product_id].stock
        ]
        if unavailable:
            raise HTTPException(
                status_code=422,
                detail={"message": "One or more quantities exceed stock on hand", "product_ids": unavailable},
            )
        total_cents = sum(products[item.product_id].price_cents * item.quantity for item in body.items)
        order = Order(customer_id=customer.id, status="draft", total_cents=total_cents)
        order.items = [
            OrderItem(
                product_id=products[item.product_id].id,
                sku=products[item.product_id].sku,
                product_name=products[item.product_id].name,
                unit_price_cents=products[item.product_id].price_cents,
                quantity=item.quantity,
            )
            for item in body.items
        ]
        session.add(order)
        session.commit()
        return to_order_response(read_order(order.id, session))

    @app.get("/orders", response_model=list[OrderResponse], tags=["Orders"])
    def list_orders(session: SessionDep, _: UserDep):
        statement = select(Order).options(selectinload(Order.customer), selectinload(Order.items)).order_by(Order.id.desc())
        return [to_order_response(order) for order in session.scalars(statement).all()]

    @app.get("/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
    def get_order(order_id: int, session: SessionDep, _: UserDep):
        return to_order_response(read_order(order_id, session))

    @app.post("/orders/{order_id}/approve", response_model=OrderActionResponse, tags=["Orders"])
    def approve_order(order_id: int, session: SessionDep, _: UserDep):
        order = read_order(order_id, session)
        if order.status != "draft":
            raise HTTPException(status_code=409, detail="Only draft orders can be approved")
        unavailable = []
        for item in order.items:
            product = find_product(item.product_id, session)
            if item.quantity > product.stock - reserved_quantity(product.id, session, excluding_order_id=order.id):
                unavailable.append(product.id)
        if unavailable:
            raise HTTPException(
                status_code=422,
                detail={"message": "One or more items are no longer available", "product_ids": unavailable},
            )
        order.status = "approved"
        session.commit()
        return to_order_action(read_order(order.id, session), "Stock reserved for this order")

    @app.post("/orders/{order_id}/dispatch", response_model=OrderActionResponse, tags=["Orders"])
    def dispatch_order(order_id: int, session: SessionDep, _: UserDep):
        order = read_order(order_id, session)
        if order.status != "approved":
            raise HTTPException(status_code=409, detail="Only approved orders can be dispatched")
        for item in order.items:
            product = find_product(item.product_id, session)
            if item.quantity > product.stock:
                raise HTTPException(status_code=409, detail="Stock changed unexpectedly; dispatch needs review")
            product.stock -= item.quantity
            session.add(StockMovement(
                product_id=product.id,
                order_id=order.id,
                quantity_delta=-item.quantity,
                reason="order_dispatched",
            ))
        order.status = "dispatched"
        session.commit()
        return to_order_action(read_order(order.id, session), "Order dispatched and stock deducted")

    @app.post("/orders/{order_id}/cancel", response_model=OrderActionResponse, tags=["Orders"])
    def cancel_order(order_id: int, session: SessionDep, _: UserDep):
        order = read_order(order_id, session)
        if order.status not in {"draft", "approved"}:
            raise HTTPException(status_code=409, detail="Only draft or approved orders can be cancelled")
        was_approved = order.status == "approved"
        order.status = "cancelled"
        session.commit()
        message = "Reservation released" if was_approved else "Draft cancelled"
        return to_order_action(read_order(order.id, session), message)

    return app


app = create_app()
