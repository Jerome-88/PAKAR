"""Bounded official-source retrieval. Source availability is not claim validity."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit

from .budget import BudgetExceeded, RunCancelled, call_worker


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class BPSEvidence:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def retrieve(self, region: str, *, deadline=None, cancelled=None) -> list[dict]:
        timestamp = datetime.now(timezone.utc).isoformat()
        base = {"id": "bps-context", "origin": "official_source", "provider": "BPS", "url": "https://webapi.bps.go.id/developer/", "region": region, "observed_period": None, "unit": None, "retrieved_at": timestamp, "value": None, "status": "UNAVAILABLE", "claim_support": "NOT_ASSESSED", "attribution": "Layanan ini menggunakan API Badan Pusat Statistik (BPS)."}
        key = os.getenv("BPS_API_KEY")
        try:
            catalog = json.loads(os.getenv("PAKAR_BPS_INDICATORS", "[]"))
        except ValueError:
            return [base | {"reason": "Konfigurasi indikator BPS tidak valid"}]
        if not isinstance(catalog, list):
            return [base | {"reason": "Konfigurasi indikator BPS harus berupa daftar"}]
        if not key or not catalog:
            return [base | {"reason": "API key atau shortlist indikator BPS belum dikonfigurasi; data tidak diisi dengan estimasi"}]
        results = []
        matching = [item for item in catalog if isinstance(item, dict) and isinstance(item.get("region"), str) and item["region"].casefold() == region.casefold()]
        for indicator in matching[:3]:
            domain, variable, period = (str(indicator.get(k, "")) for k in ("domain", "variable", "period_code"))
            if not all(re.fullmatch(r"\d{1,10}", value) for value in (domain, variable, period)):
                results.append(base | {"reason": "Kode wilayah/indikator/periode perlu ditinjau"})
                continue
            # Configuration/region/selection changes must not reuse old labels
            # or another geography's cached interpretation of the same series.
            cache_id = (json.dumps(indicator, sort_keys=True), hashlib.sha256(key.encode()).hexdigest())
            with self.lock:
                cached = self.cache.get(cache_id)
            if cached and time.monotonic() - cached[0] < 3600:
                results.append(dict(cached[1], cache_hit=True))
                continue
            public_url = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/{domain}/var/{variable}/th/{period}"
            result = base | {"id": f"bps-{domain}-{variable}-{period}", "dataset_id": variable, "geographical_unit": domain, "observed_period": indicator.get("period_label"), "unit": indicator.get("unit"), "url": public_url, "status": "UNAVAILABLE"}
            source = indicator.get("source_url")
            if isinstance(source, str):
                parsed = urlsplit(source)
                if parsed.scheme == "https" and parsed.hostname and (parsed.hostname == "bps.go.id" or parsed.hostname.endswith(".bps.go.id")) and not parsed.username and not parsed.password and not parsed.query and key not in source:
                    result["url"] = source
            try:
                # Fixed official host, numeric paths, no redirects, <=1 MB, no key
                # in persisted URLs, logs or exceptions returned to the client.
                timeout = min(10, deadline.remaining()) if deadline else 10
                if deadline:
                    raw = call_worker("bps_fetch", {"url": f"{public_url}/key/{key}", "timeout": timeout}, timeout, cancelled=cancelled)["raw"].encode("utf-8")
                else:
                    request = Request(f"{public_url}/key/{key}", headers={"Accept": "application/json", "User-Agent": "PAKAR/1.1"})
                    with build_opener(NoRedirect).open(request, timeout=timeout) as response:
                        raw = response.read(1_000_001)
                        if len(raw) > 1_000_000:
                            raise ValueError("Oversized source")
                payload = json.loads(raw)
                if not isinstance(payload, dict) or str(payload.get("status", "")).upper() not in {"OK", "SUCCESS"}:
                    raise ValueError("Invalid BPS response")
                # Preserve the raw official dimensions/values. No guessed mapping
                # from BPS dimension keys into a verified business assumption.
                data = payload.get("datacontent")
                if not isinstance(data, dict) or not data:
                    raise ValueError("No official observations")
                result.update(status="PARTIAL", reason="Sumber diterima; kesesuaian indikator, dimensi, periode dan klaim masih harus ditinjau", source_sha256=hashlib.sha256(raw).hexdigest(), observations=dict(list(data.items())[:30]), dimensions={k: payload[k] for k in ("var", "vervar", "turvar", "tahun", "turtahun") if k in payload})
                self._interpret(result, indicator, payload, variable, period)
                with self.lock:
                    self.cache[cache_id] = (time.monotonic(), result)
            except (BudgetExceeded, RunCancelled):
                raise
            except Exception:
                result.update(status="UNAVAILABLE", value=None)
                result["reason"] = "Sumber BPS tidak tersedia atau respons belum memenuhi kontrak; tidak ada angka yang dianggap terverifikasi"
            results.append(result)
        return results or [base | {"reason": "Tidak ada indikator curated yang cocok dengan wilayah proyek"}]

    @staticmethod
    def _interpret(result, indicator, payload, variable, period):
        """Optional explicit dimension selection; never decode by guessed widths."""
        if not indicator.get("selection"):
            return
        selected = indicator["selection"]
        if not isinstance(selected, dict) or set(selected) != {"vervar", "turvar", "turtahun"}:
            raise ValueError("Explicit BPS dimensions required")
        dimensions = {}
        for name, code in {"var": variable, "tahun": period, **selected}.items():
            matches = [row for row in payload.get(name, []) if isinstance(row, dict) and str(row.get("val")) == str(code)]
            if len(matches) != 1:
                raise ValueError("BPS dimension mismatch")
            dimensions[name] = matches[0]
        metadata = dimensions["var"]
        if str(dimensions["tahun"].get("label")) != str(indicator.get("period_label")):
            raise ValueError("BPS period label mismatch")
        if str(metadata.get("unit", "")).casefold() != str(indicator.get("unit", "")).casefold():
            raise ValueError("BPS unit mismatch")
        code = f"{selected['vervar']}{variable}{selected['turvar']}{period}{selected['turtahun']}"
        value = payload["datacontent"].get(code)
        # Decimal strings are retained without multiplying/rounding raw values.
        from decimal import Decimal, InvalidOperation
        try:
            if isinstance(value, bool) or not Decimal(str(value)).is_finite():
                raise ValueError("Invalid observation")
        except InvalidOperation as error:
            raise ValueError("Missing observation") from error
        result.update(value=str(value), indicator_label=metadata.get("label"),
                      selected_observation={"key": code, "raw_value": value, "labels": {k: v.get("label") for k, v in dimensions.items()}},
                      interpretation={"multiplier": 1, "scale_status": "raw_unit_metadata_checked", "claim_support": "NOT_ASSESSED",
                                      "review_note": str(indicator.get("review_note", ""))[:1000]})
        year = str(dimensions["tahun"].get("label", ""))
        if re.fullmatch(r"\d{4}", year):
            age = datetime.now(timezone.utc).year - int(year)
            result["freshness"] = {"observed_year": int(year), "age_years": age, "status": "historical" if age > 1 else "recent_period"}
        result["reason"] = ("Observasi sesuai dimensi curated dan satuan mentah sumber; data historis untuk konteks wilayah, "
                            "bukan demand usaha atau bukti kelayakan. Klaim bisnis dan kecocokan dengan publikasi pembanding belum otomatis terverifikasi.")
        BPSEvidence._reconcile(result, indicator)

    @staticmethod
    def _reconcile(result, indicator):
        comparison = indicator.get("publication_comparison")
        if comparison is None:
            return
        if not isinstance(comparison, dict) or comparison.get("selection") != indicator["selection"]:
            raise ValueError("Publication comparison dimension mismatch")
        for key in ("region", "period_label", "unit"):
            if str(comparison.get(key, "")).casefold() != str(indicator.get(key, "")).casefold():
                raise ValueError("Publication comparison scope mismatch")
        url = urlsplit(comparison.get("source_url", ""))
        if url.scheme != "https" or not url.hostname or not url.hostname.endswith(".bps.go.id") or url.username or url.password or url.query or "/publication/" not in url.path or (os.getenv("BPS_API_KEY") and os.getenv("BPS_API_KEY") in comparison["source_url"]):
            raise ValueError("Invalid publication source")
        if not re.fullmatch(r"[a-f0-9]{64}", str(comparison.get("source_sha256", ""))):
            raise ValueError("Publication checksum required")
        from decimal import Decimal, InvalidOperation
        try:
            api_value, published = Decimal(result["value"]), Decimal(str(comparison.get("value")))
            if not published.is_finite():
                raise ValueError("Invalid publication value")
        except InvalidOperation as error:
            raise ValueError("Invalid publication value") from error
        differs = api_value != published
        result["reconciliation"] = {"status": "CONFLICTING" if differs else "NUMERIC_MATCH_ONLY",
            "api_value": str(api_value), "publication_value": str(published), "difference": str(api_value - published),
            "api_url": result["url"],
            **{key: comparison.get(key) for key in ("source_url", "publication_id", "source_sha256", "table", "pdf_page", "printed_page", "region", "period_label", "unit")},
            "limitation": "Penyelarasan periode survei dan definisi agregat masih perlu review; kecocokan angka bukan validasi claim bisnis."}
        if differs:
            result.update(status="CONFLICTING", value=None, url=comparison["source_url"],
                reason=f"API: {api_value} {indicator['unit']}; publikasi pembanding: {published} {indicator['unit']} pada wilayah/tahun yang sama. Kedua nilai dipertahankan; tidak ada angka pengganti otomatis. Periode survei/metode agregasi dan relevansi bisnis masih perlu klarifikasi.")
