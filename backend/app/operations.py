"""Deterministic daily operations calculations for owner review."""
import json
import os
from datetime import UTC, datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import DailyReport, Order, OrderItem, Product, RestockRule
from .intake_provider import IntakeProviderError, write_daily_report

LOOKBACK_DAYS = 7
MIN_TARGET_STOCK = 10
LOW_STOCK_FLOOR = 5

def daily_summary(session: Session, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=LOOKBACK_DAYS)
    sales_rows = session.execute(
        select(OrderItem.product_id, func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order).where(Order.status == "dispatched", Order.created_at >= since)
        .group_by(OrderItem.product_id)
    ).all()
    sold = {product_id: quantity for product_id, quantity in sales_rows}
    thresholds = {rule.product_id: rule.threshold for rule in session.scalars(select(RestockRule)).all()}
    recommendations = []
    for product in session.scalars(select(Product).order_by(Product.stock, Product.name)):
        weekly_sales = sold.get(product.id, 0)
        trigger = max(thresholds.get(product.id, LOW_STOCK_FLOOR), weekly_sales)
        target = max(MIN_TARGET_STOCK, weekly_sales * 2)
        if product.stock <= trigger:
            recommendations.append({"product_id": product.id, "sku": product.sku, "name": product.name, "stock": product.stock, "weekly_sales": weekly_sales, "reorder_quantity": target - product.stock, "reason": f"{weekly_sales} sold in the last 7 days; {product.stock} remain."})
    dispatched_orders = session.scalars(select(Order).where(Order.status == "dispatched", Order.created_at >= since)).all()
    revenue_cents = sum(order.total_cents for order in dispatched_orders)
    report = f"{len(dispatched_orders)} dispatched orders brought in ${revenue_cents / 100:.2f} during the last 7 days. "
    report += f"{len(recommendations)} products need an owner restock review." if recommendations else "No products currently need a restock review."
    return {"period_days": LOOKBACK_DAYS, "dispatched_orders": len(dispatched_orders), "revenue": f"{revenue_cents / 100:.2f}", "recommendations": recommendations, "report": report}

def sales_analytics(session: Session, period_days: int) -> dict:
    since = datetime.now(UTC) - timedelta(days=period_days)
    rows = session.execute(select(OrderItem.product_id, Product.sku, Product.name, Product.category, func.coalesce(func.sum(OrderItem.quantity), 0), func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price_cents), 0)).join(Order).join(Product, Product.id == OrderItem.product_id).where(Order.status == "dispatched", Order.created_at >= since).group_by(OrderItem.product_id, Product.sku, Product.name, Product.category)).all()
    sold = {row[0]: row for row in rows}
    metric = lambda row: {"product_id": row[0], "sku": row[1], "name": row[2], "quantity_sold": row[4], "revenue": f"{row[5] / 100:.2f}"}
    categories: dict[str, int] = {}
    for row in rows: categories[row[3]] = categories.get(row[3], 0) + row[5]
    return {"period_days": period_days, "best_sellers": [metric(row) for row in sorted(rows, key=lambda row: (-row[4], row[2]))[:5]], "slow_movers": [metric(row) for row in sorted((row for row in rows if row[4] > 0), key=lambda row: (row[4], row[2]))[:5]], "no_sale_products": [{"product_id": product.id, "sku": product.sku, "name": product.name, "quantity_sold": 0, "revenue": "0.00"} for product in session.scalars(select(Product).order_by(Product.name)).all() if product.id not in sold][:5], "category_revenue": {category: f"{cents / 100:.2f}" for category, cents in categories.items()}}


def operational_alerts(session: Session) -> list[dict]:
    alerts = []
    out = session.scalars(select(Product).where(Product.stock == 0).order_by(Product.name)).all()
    low = session.scalars(select(Product).where(Product.stock.between(1, 5)).order_by(Product.stock, Product.name)).all()
    pending = session.scalar(select(func.count()).select_from(Order).where(Order.status.in_(["draft", "approved"]))) or 0
    if out: alerts.append({"severity": "critical", "title": f"{len(out)} products are out of stock", "detail": ", ".join(product.name for product in out[:3]), "href": "#products"})
    if low: alerts.append({"severity": "warning", "title": f"{len(low)} products are low in stock", "detail": "Review restock suggestions before stock runs out.", "href": "#operations"})
    if pending: alerts.append({"severity": "info", "title": f"{pending} orders need attention", "detail": "Draft and approved orders wait for a team decision.", "href": "#orders"})
    return alerts


def save_daily_report(session: Session, now: datetime | None = None) -> DailyReport:
    now = now or datetime.now(UTC)
    summary = daily_summary(session, now)
    report_date = now.date().isoformat()
    report_text = summary["report"]
    if os.getenv("DAILY_REPORT_AI_MODE", "demo").lower() == "live":
        try:
            report_text = write_daily_report(summary)
        except IntakeProviderError:
            # Preserve the deterministic report when the optional writer fails.
            pass
    report = session.scalar(select(DailyReport).where(DailyReport.report_date == report_date))
    if report is None:
        report = DailyReport(report_date=report_date, report=report_text, snapshot_json=json.dumps(summary))
        session.add(report)
    else:
        report.report = report_text
        report.snapshot_json = json.dumps(summary)
    session.commit()
    session.refresh(report)
    return report
