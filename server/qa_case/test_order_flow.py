"""
End-to-end test for a basic order flow using the documented API.
Covers: login -> env.resolve -> meal publish -> order create -> order update -> order cancel.
Includes setup and cleanup to avoid polluting data.

Assumptions:
- Server runs locally at http://127.0.0.1:8000
- API base prefix is /api/v1
- Passphrase mapping contains an entry for a known test passphrase, e.g. {"test":"test"} in server/config/passphrases.json
- Backend provides minimal routes per overview.md.

Run:
  pytest -q server/qa_case/test_order_flow.py
"""

import os
import time
import json
import random
from datetime import date

import pytest
import requests

BASE = os.environ.get("GHF_API_BASE", "http://127.0.0.1:8000/api/v1")
PASSPHRASE = os.environ.get("GHF_TEST_PASSPHRASE", "test")
DB_KEY = None
TOKEN = None
HEADERS = {}


@pytest.fixture(scope="module", autouse=True)
def login_and_key():
    """Module-level setup: login, resolve passphrase, set headers."""
    global TOKEN, DB_KEY, HEADERS

    # login via wx.login mock: server accepts any code in dev mode
    r = requests.post(f"{BASE}/auth/login", json={"code": f"pytest-{int(time.time())}"})
    assert r.status_code == 200, r.text
    TOKEN = r.json()["token"]

    # resolve passphrase
    r = requests.post(
        f"{BASE}/env/resolve",
        json={"passphrase": PASSPHRASE},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert r.status_code == 200, r.text
    DB_KEY = r.json()["key"]

    HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-DB-Key": DB_KEY}


def _today_str():
    return date.today().strftime("%Y-%m-%d")


def _unique_slot():
    return random.choice(
        ["lunch", "dinner"]
    )  # keep simple; if collision, publish will update existing


def _create_meal():
    """Create a meal for today with a unique combination to avoid collisions."""
    data = {
        "date": _today_str(),
        "slot": _unique_slot(),
        "title": None,
        "description": "pytest meal",
        "base_price_cents": 2000,
        "options": [
            {"id": "A", "name": "鸡腿", "price_cents": 300},
            {"id": "B", "name": "米饭加量", "price_cents": 100},
            {"id": "C", "name": "素减脂", "price_cents": -100},
        ],
        "capacity": 5,
    }
    r = requests.post(f"{BASE}/meals", json=data, headers=HEADERS)
    assert r.status_code in (200, 201), r.text
    meal_id = r.json().get("meal_id") or r.json().get("id")
    assert meal_id is not None
    return meal_id, data


def _get_meal(mid: int):
    r = requests.get(f"{BASE}/meals/{mid}", headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def _user_balance():
    r = requests.get(f"{BASE}/users/me/balance", headers=HEADERS)
    assert r.status_code == 200, r.text
    return int(r.json().get("balance_cents", 0))


def _place_order(mid: int, options=None):
    payload = {"meal_id": mid, "qty": 1}
    if options is not None:
        payload["options"] = options
    r = requests.post(f"{BASE}/orders", json=payload, headers=HEADERS)
    assert r.status_code in (200, 201), r.text
    return r.json()


def _cancel_order(mid: int):
    r = requests.delete(f"{BASE}/orders?meal_id={mid}", headers=HEADERS)
    # allow idempotent success or no-content
    assert r.status_code in (200, 204), r.text


def test_basic_order_flow():
    # Setup: create a meal
    meal_id, meta = _create_meal()

    # Check initial balance
    bal0 = _user_balance()

    # 1) create order without options
    _place_order(meal_id, options=[])
    bal1 = _user_balance()
    assert (
        bal1 == bal0 - meta["base_price_cents"]
    ), f"balance should reduce by base price: {bal0} -> {bal1}"

    # 2) update order with options A (+300)
    _place_order(meal_id, options=["A"])  # replace own order
    bal2 = _user_balance()
    assert bal2 == bal1 - 300, f"balance should reduce by +300 delta: {bal1} -> {bal2}"

    # 3) update order with option C (-100) (from base+300 -> base-100 delta = -400)
    _place_order(meal_id, options=["C"])  # replace own order
    bal3 = _user_balance()
    assert bal3 == bal2 + 400, f"balance should refund 400 delta: {bal2} -> {bal3}"

    # 4) cancel order (refund 1900)
    _cancel_order(meal_id)
    bal4 = _user_balance()
    assert bal4 == bal3 + (
        meta["base_price_cents"] - 100
    ), f"final refund should be 1900: {bal3} -> {bal4}"

    # Cleanup is implicit: order is canceled, meal remains for inspection.
