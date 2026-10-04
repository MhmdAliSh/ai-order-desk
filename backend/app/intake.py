"""Local, structured demo extraction for customer order messages.

The module can later be replaced by an LLM provider. Catalog matching and order
validation remain in application code.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import Product

STOP_WORDS = {"a", "an", "the", "for", "with", "need", "please", "send", "me", "i", "want", "some", "of", "to", "hello", "hi", "hey", "thanks", "thank", "you", "can", "could"}
ALIASES = {"chargers": "charger", "cables": "cable", "cases": "case", "earphones": "headphones", "earbuds": "headphones", "fast": ""}


@dataclass(frozen=True)
class RequestedItem:
    description: str
    quantity: int | None


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {ALIASES.get(word, word) for word in words if ALIASES.get(word, word) and ALIASES.get(word, word) not in STOP_WORDS}


def extract_requested_items(message: str) -> list[RequestedItem]:
    parts = re.split(r"(?:\n|,|;|\band\b)+", message, flags=re.IGNORECASE)
    items = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip(" .!?")
        if not cleaned:
            continue
        found = re.search(r"\b(\d+)\s+(.+)$", cleaned)
        description = found.group(2).strip() if found else cleaned
        if not tokens(description):
            continue
        items.append(RequestedItem(description, int(found.group(1)) if found else None))
    return items


def match_product(description: str, products: list[Product]) -> tuple[Product | None, str, str]:
    request_tokens = tokens(description)
    if not request_tokens:
        return None, "needs_review", "The request does not contain enough product detail."
    candidates = []
    for product in products:
        product_tokens = tokens(f"{product.sku} {product.name} {product.category}")
        overlap = request_tokens & product_tokens
        score = max(len(overlap) / len(request_tokens), SequenceMatcher(None, " ".join(sorted(request_tokens)), " ".join(sorted(product_tokens))).ratio() * 0.7)
        candidates.append((score, product, overlap))
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    score, product, overlap = candidates[0]
    competitor = candidates[1][0] if len(candidates) > 1 else 0
    if score < 0.45:
        return None, "needs_review", "No reliable catalog match was found."
    evidence = "Matched on " + ", ".join(sorted(overlap)) if overlap else "Matched on the product description."
    if score < 0.72 or score - competitor < 0.08:
        return product, "needs_review", evidence + " Please confirm the suggested variant."
    return product, "matched", evidence


def analyze_message(
    message: str, products: list[Product], requested_items: list[RequestedItem] | None = None
) -> tuple[list[dict], list[str]]:
    requested = extract_requested_items(message) if requested_items is None else requested_items
    if not requested:
        return [], ["No order items were found. Include one item per line or include quantities."]
    items, notes = [], []
    for item in requested:
        product, status, evidence = match_product(item.description, products)
        if item.quantity is None:
            status, evidence = "needs_review", "Quantity is missing. " + evidence
        if product is not None and item.quantity is not None and item.quantity > product.stock:
            status, evidence = "unavailable", evidence + f" Requested {item.quantity}; only {product.stock} are on hand."
        items.append({"requested_description": item.description, "quantity": item.quantity, "suggested_product": None if product is None else {"id": product.id, "sku": product.sku, "name": product.name, "stock": product.stock}, "match_status": status, "evidence": evidence})
    if any(item["match_status"] != "matched" for item in items):
        notes.append("Review highlighted items before using these suggestions in an order draft.")
    return items, notes
