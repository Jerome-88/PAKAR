"""Narrow deterministic checks, not a general semantic fact checker."""
from __future__ import annotations

import re
from copy import deepcopy
from decimal import Decimal


VERSION = "explicit-money-comparison-v1"
MONEY_PAIR = re.compile(r"\bRp\.?\s*(\d[\d.,]*)\s*([^\n;]{0,120}?)\bRp\.?\s*(\d[\d.,]*)", re.I)
LESS = re.compile(r"\b(di bawah|lebih (?:kecil|rendah) (?:dari|daripada)|below|less than)\b|(?<![<>=])<(?![=>])", re.I)
GREATER = re.compile(r"\b(di atas|lebih (?:besar|tinggi) (?:dari|daripada)|above|greater than)\b|(?<![<>=])>(?![=>])", re.I)


def number(text):
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", text):
        return Decimal(re.sub(r"[.,]", "", text))
    if re.fullmatch(r"\d+(?:[.,]\d{1,2})?", text):
        return Decimal(text.replace(",", "."))
    return None  # Ambiguous formatting must not become a guessed amount.


def arithmetic_issues(finding):
    issues = []
    for field in ("title", "reasoning"):
        text = finding.get(field, "")
        if not isinstance(text, str):
            continue
        for match in MONEY_PAIR.finditer(text):
            between = match[2]
            # Do not reinterpret a negated comparison or cross-sentence
            # text, different time/unit bases, or an uncertain conditional.
            prefix = text[max(0, match.start() - 80):match.start()]
            if re.search(r"\b(tidak|bukan|not|isn't|jika|bila|apabila|if|assuming|keliru|incorrectly|false)\b", prefix + between, re.I) or re.search(r"\.\s|/(?:unit|bulan|month|year|tahun)|per\s+(?:bulan|month|year|tahun)|\b(?:USD|EUR|GBP)\b|\$", between, re.I):
                continue
            left, right = number(match[1]), number(match[3])
            if left is None or right is None:
                continue
            op = "<" if LESS.search(between) else ">" if GREATER.search(between) else None
            if op and not (left < right if op == "<" else left > right):
                issue = f"Perbandingan eksplisit salah: Rp{left} {op} Rp{right}."
                if issue not in issues:
                    issues.append(issue)
    return issues


def project_valid_findings(result):
    rejected = [{"id": f["id"], "author": f["author"], "title": f["title"], "issues": problems}
                for f in result.get("findings", []) if (problems := arithmetic_issues(f))]
    if not rejected:
        return result
    # A read projection must not rewrite an immutable baseline/result registry.
    projected = deepcopy(result)
    ids = {f["id"] for f in rejected}
    projected["findings"] = [f for f in projected["findings"] if f["id"] not in ids]
    projected["finding_validation"] = {"version": VERSION, "rejected": rejected, "coverage": "explicit same-currency numeric comparisons only"}
    for disagreement in projected.get("disagreements", []):
        summary = disagreement.get("summary", "")
        referenced = [f["id"] for f in rejected if re.search(r"(?<![\w-])" + re.escape(f["id"]) + r"(?![\w-])", summary, re.I) or f["title"].casefold() in summary.casefold()]
        if referenced:
            disagreement["held_finding_ids"] = referenced
            disagreement["summary"] = f"[Catatan tentang temuan {', '.join(referenced)} yang ditahan karena perbandingan angka salah; bukan dukungan temuan.] {summary}"
    for item in rejected:
        projected.setdefault("limitations", []).append(f"Temuan {item['id']} ({item['author']}) ditahan dari tampilan/laporan: {' '.join(item['issues'])} Snapshot mentah tetap disimpan untuk audit.")
    projected.setdefault("provenance", {})["finding_validator"] = VERSION
    return projected
