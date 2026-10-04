"""WhatsApp Cloud API webhook support with local, review-only intake analysis."""
import hashlib
import hmac
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .intake import analyze_message
from .models import IntegrationSettings, Product, WhatsAppInboundMessage

ASSISTANT_INTRO = "Hi, I’m the AI assistant for Mobile & More. I can help check product availability, understand an order request, and ask our team for alternatives when an item is unavailable. "


def verify_signature(body: bytes, signature: str | None) -> None:
    secret = os.getenv("WHATSAPP_APP_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="WhatsApp integration is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid WhatsApp webhook signature")


def ingest_messages(payload: dict, session: Session) -> int:
    products = session.query(Product).order_by(Product.id).all()
    added = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") != "text" or not message.get("text", {}).get("body"):
                    continue
                if session.query(WhatsAppInboundMessage).filter_by(external_message_id=message["id"]).first():
                    continue
                items, notes = analyze_message(message["text"]["body"], products)
                analysis = {"items": items, "notes": notes}
                settings = session.get(IntegrationSettings, 1)
                intro = settings.whatsapp_intro if settings and settings.whatsapp_intro else ASSISTANT_INTRO
                session.add(WhatsAppInboundMessage(external_message_id=message["id"], sender_phone=message.get("from", "unknown"), message_text=message["text"]["body"], analysis_json=json.dumps(analysis)))
                if os.getenv("WHATSAPP_AUTO_REPLY_MODE", "off").lower() == "live":
                    send_stock_reply(message.get("from", ""), build_stock_reply(analysis, intro))
                added += 1
    session.commit()
    return added


def build_stock_reply(analysis: dict, intro: str = ASSISTANT_INTRO) -> str:
    """Create a reply from verified matching and stock facts, never AI guesswork."""
    items = analysis.get("items", [])
    if not items:
        return intro + " Please tell me the product and quantity you need, and our team will review your request."
    unavailable = [item for item in items if item.get("match_status") == "unavailable"]
    unclear = [item for item in items if item.get("match_status") == "needs_review"]
    if unavailable:
        names = ", ".join(item.get("requested_description", "requested item") for item in unavailable)
        return intro + f" {names} is currently unavailable or does not have enough stock. Our team can suggest an alternative."
    if unclear:
        return intro + " We received your request and a team member will confirm the exact product and availability shortly."
    names = ", ".join(item["suggested_product"]["name"] for item in items if item.get("suggested_product"))
    return intro + f" {names} is currently available. Our team will review your request and confirm the order details."


def send_stock_reply(phone: str, text: str) -> None:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id or not phone:
        return
    request = Request(
        f"https://graph.facebook.com/v22.0/{phone_number_id}/messages",
        data=json.dumps({"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": text}}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=20):  # noqa: S310 - fixed Meta Graph API endpoint
            pass
    except (HTTPError, URLError, TimeoutError) as error:
        raise HTTPException(status_code=502, detail="WhatsApp reply could not be sent") from error
