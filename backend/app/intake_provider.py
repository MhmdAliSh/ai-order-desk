"""Optional OpenAI extraction for customer order messages.

This module only turns a message into requested descriptions and quantities.
It never receives catalog data and cannot create, approve, dispatch, or cancel
an order. The application still performs catalog matching and stock checks.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .intake import RequestedItem


class IntakeProviderError(RuntimeError):
    """A safe error that can be shown when the configured AI service fails."""


EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "name": "order_items",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "items": {
                "type": "array",
                "maxItems": 30,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": ["integer", "null"], "minimum": 1},
                    },
                    "required": ["description", "quantity"],
                },
            }
        },
        "required": ["items"],
    },
}


def extract_requested_items(message: str) -> list[RequestedItem]:
    """Call the Responses API and validate its small, reviewable output."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise IntakeProviderError("Live AI mode needs OPENAI_API_KEY. Add it to your local environment, then restart the backend.")

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "max_output_tokens": 500,
        "input": [
            {
                "role": "system",
                "content": (
                    "Extract customer order requests into JSON. Return only items explicitly requested. "
                    "Keep the customer's wording as description. Use null if quantity is missing. "
                    "Do not choose catalog products, calculate prices, check stock, or take business actions."
                ),
            },
            {"role": "user", "content": message},
        ],
        "text": {"format": EXTRACTION_SCHEMA},
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed OpenAI API endpoint
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise IntakeProviderError("The AI provider rejected the request. Check OPENAI_API_KEY and try again.") from error
    except (URLError, TimeoutError) as error:
        raise IntakeProviderError("The AI provider could not be reached. Check your connection and try again.") from error
    except json.JSONDecodeError as error:
        raise IntakeProviderError("The AI provider returned an unreadable response. Try again.") from error

    try:
        data = json.loads(body["output_text"])
        items = data["items"]
        if not isinstance(items, list):
            raise ValueError("items is not a list")
        extracted = [
            RequestedItem(description=item["description"].strip(), quantity=item["quantity"])
            for item in items
            if isinstance(item, dict) and isinstance(item.get("description"), str) and item["description"].strip()
        ]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise IntakeProviderError("The AI response did not contain usable order items. Try again.") from error
    if any(item.quantity is not None and (not isinstance(item.quantity, int) or isinstance(item.quantity, bool) or item.quantity < 1) for item in extracted):
        raise IntakeProviderError("The AI response contained an invalid quantity. Try again.")
    return extracted


def write_daily_report(facts: dict) -> str:
    """Turn calculated facts into a short owner-facing explanation only."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise IntakeProviderError("Live AI mode needs OPENAI_API_KEY.")
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "max_output_tokens": 180,
        "input": [
            {"role": "system", "content": "Write a concise, plain-language daily retail owner report from the supplied JSON facts. Do not invent facts, give instructions to purchase, or claim any action was taken."},
            {"role": "user", "content": json.dumps(facts)},
        ],
    }
    request = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed OpenAI endpoint
            text = json.loads(response.read().decode("utf-8")).get("output_text", "").strip()
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise IntakeProviderError("The AI daily-report provider could not be reached.") from error
    if not text:
        raise IntakeProviderError("The AI daily-report provider returned no text.")
    return text
