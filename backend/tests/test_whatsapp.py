from app.whatsapp import build_stock_reply

def test_stock_reply_does_not_claim_unclear_items_are_available():
    reply = build_stock_reply({"items": [{"requested_description": "a charger", "match_status": "needs_review", "suggested_product": None}]})
    assert "team member" in reply
    assert "currently available" not in reply

def test_stock_reply_explains_unavailable_items():
    reply = build_stock_reply({"items": [{"requested_description": "25W charger", "match_status": "unavailable", "suggested_product": None}]})
    assert "unavailable" in reply
    assert "AI assistant" in reply
