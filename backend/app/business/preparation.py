"""Automatic intake preserves sources and labels assumptions as unreviewed."""
from collections import Counter
from copy import deepcopy

from .intake import discover, financial_inputs
from .contracts import Persona
from .repository import uid


def automatic_inputs(claims):
    included = [deepcopy(c) for c in claims if c["review_status"] != "rejected"]
    for claim in included:
        claim["input_acceptance"] = "automatic_document_assumption"
        claim["human_reviewed"] = claim["review_status"] == "approved"
        claim["review_status"] = "approved"  # Accepted for computation, not verified.
    counts = Counter(c.get("variable") for c in included if c.get("value") is not None)
    expected = {"selling_price": "IDR/unit", "variable_cost": "IDR/unit", "fixed_cost_monthly": "IDR/month", "volume_monthly": "units/month"}
    usable, issues = [], []
    for claim in included:
        variable = claim.get("variable")
        if variable in expected and claim.get("value") is not None:
            if counts[variable] > 1 or claim.get("unit") != expected[variable]:
                issues.append(f"Input {variable} belum dipakai: nilai ganda atau satuan belum sesuai. Periksa kutipan dokumen; nilai perhitungan tetap unknown.")
                continue
        usable.append(claim)
    values, refs = financial_inputs(usable)
    return included, values, refs, list(dict.fromkeys(issues))


def contextual_personas(context, claims, limit=4):
    candidates = discover(context, claims)
    funding = [c["id"] for c in claims if any(term in c["quote"].casefold() for term in ("investor", "pemodal", "pendanaan", "modal ventura"))]
    if funding:
        candidates.append(Persona(id="persona-investor", name=f"Investor/pemodal - {context['region']}", role="investor", goals=["Memeriksa kebutuhan modal dan risiko usaha"], constraints=["Peran dan tujuan masih hipotesis dari dokumen"], provenance={"role": "document_supported", "claim_ids": funding}, discovery_rationale="Sumber menyebut investor/pendanaan; partisipasi dan tujuan pemodal nyata belum dikonfirmasi.", relationships=["persona-operator"]).model_dump(mode="json"))
    # Always provide two basic perspectives; extras require a source mention.
    # This avoids adding the whole generic role catalog to every document.
    selected = [p for p in candidates if p["role"] in {"operator", "customer"}]
    for persona in candidates:
        if persona["role"] not in {"operator", "customer"} and persona["provenance"].get("claim_ids"):
            selected.append(persona)
    selected = selected[:limit]
    identities = {p["id"]: uid("persona") for p in selected}
    for persona in selected:
        persona["id"] = identities[persona["id"]]
        persona["relationships"] = [identities[p] for p in persona["relationships"] if p in identities]
        name = persona["name"].split(" — ")[0] if context["region"] == "Belum ditentukan" else persona["name"]
        persona["name"] = (f"{name} ({context['industry']})" if context["industry"] != "Belum ditentukan" else name)[:160]
        persona["reviewed"] = False
        persona["knowledge"] = [*persona["knowledge"], context["decision_question"]]
        persona["provenance"].update(generator="document-context-v1", review_required=True, selection="basic_business_role" if persona["role"] in {"operator", "customer"} and not persona["provenance"].get("claim_ids") else "document_role_mention")
    return selected


def ground_personas(context, claims, proposed, limit=4):
    """Keep source-supported roles and business labels, not invented people."""
    selected = contextual_personas(context, claims, limit)
    candidates = {p["role"]: p for p in proposed}
    identities = {p["id"]: candidates[p["role"]]["id"] if p["role"] in candidates else p["id"] for p in selected}
    for persona in selected:
        original = candidates.get(persona["role"])
        persona["id"] = identities[persona["id"]]
        persona["relationships"] = [identities.get(p, p) for p in persona["relationships"]]
        if original:
            persona["goals"] = original["goals"]
            persona["constraints"] = original["constraints"]
            persona["provenance"].update(generator="llm-contextual-v3", goals="llm_hypothesis", display_name="business_role_label", review_required=True)
        else:
            persona["provenance"].update(goals="contextual_hypothesis", display_name="business_role_label")
    return selected
