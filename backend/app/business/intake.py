from __future__ import annotations

import re
from decimal import Decimal

from .contracts import Claim, Persona


def extract_claims(document_id, extracted):
    claims = []
    for index, segment in enumerate(extracted.segments):
        text = segment.text
        if len(text) < 8:
            continue
        variable = None
        unit = None
        lowered = text.casefold()
        for keywords, candidate, canonical in (
            (("harga jual", "selling price"), "selling_price", "IDR/unit"),
            (("biaya variabel", "variable cost"), "variable_cost", "IDR/unit"),
            (("biaya tetap", "fixed cost"), "fixed_cost_monthly", "IDR/month"),
            (("volume", "penjualan per bulan"), "volume_monthly", "units/month"),
        ):
            if any(term in lowered for term in keywords):
                variable = candidate
                if ("per unit" in lowered or "/unit" in lowered) and candidate in {"selling_price", "variable_cost"}:
                    unit = canonical
                elif ("per bulan" in lowered or "/bulan" in lowered or "monthly" in lowered) and candidate in {"fixed_cost_monthly", "volume_monthly"}:
                    unit = canonical
                break
        if variable in {"selling_price", "variable_cost", "fixed_cost_monthly"} and not re.search(r"(?:\brp(?=[\s.\d])|\bidr\b|\brupiah\b)", lowered):
            # Never silently convert a bare amount, USD or other currency to IDR.
            unit = None
        if variable == "volume_monthly" and not re.search(r"\b(?:unit|porsi|pcs|produk)\b", lowered):
            unit = None
        matches = list(re.finditer(r"(?:Rp\.?\s*)?(\d[\d.,]*)(?:\s*(juta|ribu|miliar))?", text, re.I))
        value = None
        # Multiple numbers or mixed units need human review, not a guessed value.
        if variable and unit and len(matches) == 1:
            raw, scale = matches[0].groups()
            raw = raw.rstrip(".,")
            if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw and "." not in raw:
                raw = raw.replace(",", ".")
            if re.fullmatch(r"\d+(?:\.\d+)?", raw):
                value = Decimal(raw) * {None: 1, "ribu": 1000, "juta": 1000000, "miliar": 1000000000}[scale.casefold() if scale else None]
        if len(text) > 6000:
            raise ValueError("Segmen sumber melebihi 6000 karakter; pecah paragraf agar tidak ada claim yang dipotong diam-diam")
        locator = {"char_start": segment.char_start, "char_end": segment.char_end, "page": segment.page, "paragraph": segment.paragraph, "table": segment.table, "row": segment.row, "column": segment.column}
        claims.append(Claim(id=f"{document_id}:claim:{index + 1}", quote=text[:6000], normalized_text=text[:6000], variable=variable, value=value, unit=unit, classification="forecast" if any(w in lowered for w in ("proyeksi", "target", "akan ", "forecast")) else "assumption", source={"document_id": document_id, "locator": locator, "extraction": "source-segment-v1"}).model_dump(mode="json"))
    return claims


ROLE_CONTEXT = [
    ("operator", "Pengelola bisnis", "Menjaga kelangsungan operasional dan margin", ["operator", "pemilik", "pengelola", "founder"]),
    ("customer", "Customer sasaran", "Memperoleh manfaat yang sebanding dengan harga", ["konsumen", "pelanggan", "customer"]),
    ("supplier", "Supplier utama", "Menjaga biaya dan kepastian pembayaran", ["supplier", "pemasok"]),
    ("competitor", "Kompetitor lokal", "Mempertahankan posisi dan diferensiasi pasar", ["kompetitor", "pesaing", "competitor"]),
    ("employee", "Tim operasional", "Memiliki beban kerja dan kompensasi yang layak", ["pegawai", "karyawan", "employee", "teknisi", "tenaga kerja"]),
    ("regulator", "Peninjau regulasi", "Memastikan pertanyaan izin dan kewajiban ditinjau", ["regulator", "izin", "regulasi"]),
    ("community", "Masyarakat sekitar lokasi", "Menghindari dampak operasional yang merugikan lingkungan sekitar", ["masyarakat sekitar", "warga sekitar", "komunitas lokal"]),
    ("partner", "Mitra distribusi", "Menjaga kelayakan layanan dan syarat kemitraan", ["distributor", "mitra", "partner"]),
]


def discover(context, claims, existing=None):
    """Contextual candidates, all explicitly synthetic until reviewed/evidenced."""
    source = " ".join(c["quote"] for c in claims).casefold()
    existing = existing or []
    seen = {p["role"] for p in existing}
    result = []
    for role, label, goal, terms in ROLE_CONTEXT:
        if role in seen:
            continue
        mentions = [c["id"] for c in claims if any(term in c["quote"].casefold() for term in terms)]
        kind = "direct" if mentions or role == "operator" else "indirect" if role in {"regulator", "partner"} else "hidden"
        result.append(Persona(
            id=f"persona-{role}", name=f"{label} — {context['region']}", role=role, stakeholder_type=kind,
            goals=[goal], motivations=[f"Menilai keputusan pada industri {context['industry']}"],
            constraints=["Informasi terbatas pada konteks yang dibagikan; perilaku masih hipotesis"],
            knowledge=[context["industry"], context["region"], context["target_customer"]], interests=[goal],
            relationships=["persona-operator"] if role != "operator" else ["persona-customer", "persona-supplier"],
            provenance={"role": "document_supported" if mentions else "synthetic_hypothesis", "claim_ids": mentions, "goals": "synthetic_hypothesis", "motivations": "synthetic_hypothesis", "knowledge": "user_supplied_context"},
            discovery_rationale="Disebut dalam sumber; tujuan dan respons tetap hipotesis." if mentions else f"Kandidat untuk ditinjau: peran {label.lower()} dapat terkait dengan keputusan {context['industry']} di {context['region']}. Relevansi belum tervalidasi.",
        ).model_dump(mode="json"))
    return result


def financial_inputs(claims):
    expected_units = {"selling_price": "IDR/unit", "variable_cost": "IDR/unit", "fixed_cost_monthly": "IDR/month", "volume_monthly": "units/month"}
    values = {key: None for key in expected_units}
    references = {}
    for claim in claims:
        variable = claim.get("variable")
        if claim["review_status"] != "approved" or variable not in values or claim.get("value") is None:
            continue
        if claim.get("unit") != expected_units[variable]:
            raise ValueError(f"Satuan {variable} harus {expected_units[variable]}; konversi harus eksplisit")
        if variable in references:
            raise ValueError(f"Terdapat beberapa nilai aktif untuk {variable}; pilih satu claim sebelum analisis")
        values[variable] = claim["value"]
        references[variable] = claim["id"]
    return values, references
