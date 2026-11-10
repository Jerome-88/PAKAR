"""Reserve dollars before dispatch; unknown invoices retain their reservation.

OpenRouter provider price ceilings are USD per million text tokens. Reserves
include a conservative UTF-8 prompt bound and the maximum output allowance.
The durable account ledger prevents concurrent PAKAR jobs spending one balance.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
import threading
from urllib.parse import urlsplit

from .budget import BudgetExceeded, call_worker


class SpendingLimit(BudgetExceeded):
    pass


def dollars(value):
    try:
        if isinstance(value, bool):
            raise ValueError("Invalid dollar amount")
        value = Decimal(str(value))
        if not value.is_finite() or value < 0:
            raise ValueError("Invalid dollar amount")
        return value
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid dollar amount") from None


def price_ceiling():
    raw = json.loads(os.environ.get("PAKAR_OPENROUTER_MAX_PRICE", "null"))
    if not isinstance(raw, dict) or not {"prompt", "completion"} <= raw.keys() or set(raw) - {"prompt", "completion", "request"}:
        raise SpendingLimit("Konfigurasi batas harga provider diperlukan sebelum memakai kredit")
    prices = {key: dollars(raw.get(key, 0)) for key in ("prompt", "completion", "request")}
    if prices["request"] != 0:
        raise SpendingLimit("Pengaman biaya hanya mendukung provider tanpa biaya per request")
    return prices


class DollarBudget:
    def __init__(self, limit, prices):
        self.limit = dollars(limit)
        self.prices = {key: dollars(value) for key, value in prices.items()}
        self.charges = {}
        self.lock = threading.RLock()

    @property
    def charged(self):
        return sum(self.charges.values(), Decimal(0))

    @property
    def remaining(self):
        return max(Decimal(0), self.limit - self.charged)

    def reserve_amount(self, amount):
        amount = dollars(amount)
        with self.lock:
            if amount > self.remaining:
                raise SpendingLimit("Batas biaya dolar tercapai sebelum panggilan AI berikutnya")
            key = str(len(self.charges) + 1)
            self.charges[key] = amount
            return key

    def reserve(self, input_tokens, output_tokens):
        amount = (self.prices["prompt"] * input_tokens + self.prices["completion"] * output_tokens) / Decimal(1_000_000)
        key = self.reserve_amount(amount)
        return key, amount

    def settle(self, key, reported_cost):
        if reported_cost is None:
            return  # Failed/unknown calls retain the entire upper bound.
        amount = dollars(reported_cost)
        with self.lock:
            previous = self.charges[key]
            self.charges[key] = amount
            if amount > previous:
                raise SpendingLimit("Biaya provider melebihi reservasi; panggilan berikutnya dihentikan")

    def summary(self):
        return {"limit_usd": float(self.limit), "charged_or_reserved_usd": float(self.charged),
                "remaining_usd": float(self.remaining), "unknown_cost_policy": "retain_upper_bound"}


class SpendLedger:
    def __init__(self, engine, account_id, scope, ceiling, budget):
        self.engine, self.account_id, self.scope = engine, account_id, scope
        self.ceiling, self.budget = ceiling, budget

    @classmethod
    def open(cls, settings, engine, scope, requested=None, *, timeout=10, cancelled=None):
        from sqlalchemy import select, update
        from sqlalchemy.dialects.postgresql import insert
        from .tables import provider_spend_accounts as accounts, provider_spend_reservations as reservations
        if urlsplit(settings.llm_base_url or "").hostname != "openrouter.ai":
            return None  # Local/test providers never query a real credit account.
        prices = price_ceiling()
        ceiling = min(dollars(requested if requested is not None else ".005"), dollars(os.getenv("PAKAR_MAX_RUN_COST_USD", ".03")))
        floor = dollars(os.getenv("PAKAR_CREDIT_RESERVE_USD", ".10"))
        data = call_worker("openrouter_credit", {"api_key": settings.llm_api_key}, timeout, cancelled=cancelled)
        available = dollars(data["remaining_usd"])
        account_id = hashlib.sha256(settings.llm_api_key.encode()).hexdigest()
        with engine.begin() as connection:
            connection.execute(insert(accounts).values(id=account_id, available_usd=available).on_conflict_do_nothing())
            account = connection.execute(select(accounts).where(accounts.c.id == account_id).with_for_update()).mappings().one()
            if connection.execute(select(reservations.c.id).where(reservations.c.id == scope)).first():
                raise SpendingLimit("Reservasi ini sudah pernah dipakai; tidak ada retry berbayar otomatis")
            safe_available = min(available, account["available_usd"])
            if ceiling <= 0 or safe_available - ceiling < floor:
                raise SpendingLimit("Kredit tidak cukup untuk plafon run dan saldo cadangan; tidak ada AI yang dipanggil")
            connection.execute(update(accounts).where(accounts.c.id == account_id).values(available_usd=safe_available - ceiling))
            connection.execute(insert(reservations).values(id=scope, account_id=account_id, ceiling_usd=ceiling))
        return cls(engine, account_id, scope, ceiling, DollarBudget(ceiling, prices))

    def close(self):
        from sqlalchemy import select, update
        from .tables import provider_spend_accounts as accounts, provider_spend_reservations as reservations
        # Lock order is the same as admission. A dead process leaves the full
        # reservation held, rather than guessing that an interrupted call is free.
        with self.engine.begin() as connection:
            connection.execute(select(accounts.c.id).where(accounts.c.id == self.account_id).with_for_update()).one()
            row = connection.execute(select(reservations).where(reservations.c.id == self.scope).with_for_update()).mappings().one()
            if row["charged_usd"] is not None:
                return
            charged = self.budget.charged
            connection.execute(update(reservations).where(reservations.c.id == self.scope).values(charged_usd=charged))
            connection.execute(update(accounts).where(accounts.c.id == self.account_id).values(available_usd=accounts.c.available_usd + self.ceiling - charged))
