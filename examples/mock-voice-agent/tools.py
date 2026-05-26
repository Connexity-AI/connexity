"""Mock tool implementations shared with examples/mock-text-agent/."""

from __future__ import annotations

from typing import Any


def lookup_order(order_id: str, **_extra: Any) -> dict[str, Any]:
    oid = order_id.strip().upper()
    if oid == "ORD-12345":
        return {
            "order_id": oid,
            "status": "delivered",
            "amount": 49.99,
            "product": "Wireless Mouse Pro",
            "purchase_date": "2026-03-15",
            "payment_method": "credit_card",
            "eligible_refund": True,
        }
    if oid == "ORD-55555":
        return {
            "order_id": oid,
            "status": "processing",
            "order_total": 129.99,
            "shipping_address": "123 Main St, Chicago, IL 60601",
            "items": [{"name": "Primary item", "qty": 1}],
        }
    return {
        "order_id": oid,
        "status": "not_found",
        "detail": "No mock record for this order id",
    }
