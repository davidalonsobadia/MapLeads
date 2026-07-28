"""Tests for the internal-key gated promo-code creation/listing endpoints.

The endpoints are gated by the ``x-internal-key`` internal secret (separate
from the customer-facing ``x-api-key`` gateway, which is disabled under
``TESTING=1``). Tests patch ``settings.INTERNAL_API_KEY`` via ``monkeypatch``
(mirroring ``test_billing_stripe._configure_stripe``) and send the header
explicitly. The ``client`` fixture wires the app to the in-memory SQLite DB.
"""

from app.core.config import settings

CREATE = "/api/v1/promotions/codes"
LIST = "/api/v1/promotions/codes"

INTERNAL_KEY = "internal-secret-123"


def _configure_internal_key(monkeypatch):
    """Set a placeholder internal secret on the settings singleton."""
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", INTERNAL_KEY)


def _headers():
    return {"x-internal-key": INTERNAL_KEY}


# --- Gating ---------------------------------------------------------------


def test_create_requires_configured_internal_key(client, monkeypatch):
    """When INTERNAL_API_KEY is unset the endpoint is never open → 503."""
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "")
    resp = client.post(
        CREATE,
        json={"code": "SAVE10", "discount_type": "percentage", "value": 10},
        headers=_headers(),
    )
    assert resp.status_code == 503


def test_create_rejects_missing_key(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "SAVE10", "discount_type": "percentage", "value": 10},
    )
    assert resp.status_code == 403


def test_create_rejects_wrong_key(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "SAVE10", "discount_type": "percentage", "value": 10},
        headers={"x-internal-key": "wrong"},
    )
    assert resp.status_code == 403


# --- Create success per discount_type -------------------------------------


def test_create_percentage_success(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "save10", "discount_type": "percentage", "value": 10},
        headers=_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "SAVE10"  # normalized to upper-case
    assert body["discount_type"] == "percentage"
    assert body["value"] == 10
    assert body["used_count"] == 0
    assert body["max_uses"] == 1
    assert body["is_active"] is True


def test_create_fixed_amount_success(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "EUR5", "discount_type": "fixed_amount", "value": 5,
              "max_uses": 100},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["max_uses"] == 100


def test_create_free_months_success(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "FREE3", "discount_type": "free_months", "value": 3},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == 3


def test_create_lifetime_free_success(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "FOREVER", "discount_type": "lifetime_free"},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["value"] is None


def test_create_with_target_plan(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.post(
        CREATE,
        json={"code": "PROONLY", "discount_type": "percentage", "value": 20,
              "target_plan": "pro"},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["target_plan"] == "pro"


# --- Validation (422) -----------------------------------------------------


def _assert_422(client, payload):
    resp = client.post(CREATE, json=payload, headers=_headers())
    assert resp.status_code == 422


def test_validation_percentage_zero(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(client, {"code": "X", "discount_type": "percentage", "value": 0})


def test_validation_percentage_over_100(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(client, {"code": "X", "discount_type": "percentage", "value": 101})


def test_validation_lifetime_free_with_value(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(
        client, {"code": "X", "discount_type": "lifetime_free", "value": 5}
    )


def test_validation_free_months_below_one(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(client, {"code": "X", "discount_type": "free_months", "value": 0})


def test_validation_fixed_amount_below_one(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(client, {"code": "X", "discount_type": "fixed_amount", "value": 0})


def test_validation_unknown_discount_type(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(client, {"code": "X", "discount_type": "bogus", "value": 10})


def test_validation_unknown_target_plan(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(
        client,
        {"code": "X", "discount_type": "percentage", "value": 10,
         "target_plan": "gold"},
    )


def test_validation_max_uses_below_one(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(
        client,
        {"code": "X", "discount_type": "percentage", "value": 10, "max_uses": 0},
    )


def test_validation_empty_code(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    _assert_422(
        client, {"code": "   ", "discount_type": "percentage", "value": 10}
    )


# --- Duplicate & list -----------------------------------------------------


def test_duplicate_code_conflicts(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    payload = {"code": "DUP", "discount_type": "percentage", "value": 10}
    first = client.post(CREATE, json=payload, headers=_headers())
    assert first.status_code == 200
    # Case-insensitive: normalized to the same code.
    second = client.post(
        CREATE,
        json={"code": "dup", "discount_type": "percentage", "value": 15},
        headers=_headers(),
    )
    assert second.status_code == 409


def test_list_returns_created_codes(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    client.post(
        CREATE,
        json={"code": "A", "discount_type": "percentage", "value": 10},
        headers=_headers(),
    )
    client.post(
        CREATE,
        json={"code": "B", "discount_type": "lifetime_free"},
        headers=_headers(),
    )
    resp = client.get(LIST, headers=_headers())
    assert resp.status_code == 200
    codes = {c["code"] for c in resp.json()}
    assert {"A", "B"} <= codes


def test_list_requires_internal_key(client, monkeypatch):
    _configure_internal_key(monkeypatch)
    resp = client.get(LIST)
    assert resp.status_code == 403
