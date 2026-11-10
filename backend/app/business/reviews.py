"""Bounded specialist waves, immutable peer context and deterministic merging."""
from __future__ import annotations

import time
import math
import json
import os
from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
from threading import Event

from .agents import validate_finding_references, SYSTEM_PROMPT
from .budget import RunCancelled
from .contracts import Finding
from .structured import review_schema, response_format
from .groq_limits import request_tokens, is_groq_reasoning_model
from .information import scoped as information_scoped


ROLES = ("Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent")
PAIRED_POLICY = "paired-v2"


def pick(value, keys):
    return {key: value[key] for key in keys if key in value}


def compact_context(role, snapshot, simulation, evidence, peers, *, event_limit=None, peer_limit=12, claim_limit=35):
    """Keep original references/numbers/status; omit duplicated registry plumbing.

    No values or source text are rewritten. Large contexts use an explicit
    bounded window, just as the existing specialist adapter did.
    """
    claims = [pick(c, ("id", "normalized_text", "quote", "classification", "variable", "value", "unit", "period", "evidence_status")) for c in snapshot["claims"][:claim_limit]]
    reactive_context = simulation.get("discussion_policy") == "reactive-v2"
    window = event_limit or (8 if reactive_context else 12)
    selected = {e["id"]: e for e in simulation["events"][-window:]}
    for event in list(selected.values()):
        for parent in [event.get("thread_id"), *event.get("parent_event_ids", [])]:
            source = next((e for e in simulation["events"] if e["id"] == parent), None)
            if source and len(selected) < (window + 2 if event_limit else 16 if reactive_context else 24):
                selected[parent] = source
    order = {e["id"]: i for i, e in enumerate(simulation["events"])}
    events = [pick(e, ("id", "round", "actor_id", "target_id", "kind", "amount", "rationale", "content", "thread_id", "reply_to", "visibility", "stance_update", "parent_event_ids", "state_before", "state_after")) for e in sorted(selected.values(), key=lambda e: order[e["id"]])]
    for event in events:
        for field in ("state_before", "state_after"):
            if isinstance(event.get(field), dict):
                event[field] = pick(event[field], ("version", "position", "stance", "stance_reason"))
    if reactive_context:
        # Preserve each source string once. Identical copies inflate the UTF-8
        # admission bound without adding information to the reviewer context.
        for claim in claims:
            if claim.get("normalized_text") == claim.get("quote"):
                claim.pop("normalized_text", None)
        for event in events:
            if event.get("content") == event.get("rationale"):
                event.pop("rationale", None)
            # Stance deltas remain in stance_update; current finances remain in
            # the typed calculation. Full state snapshots stay in the audit.
            event.pop("state_before", None)
            event.pop("state_after", None)
    sources = [pick(e, ("id", "provider", "status", "claim_support", "region", "geographical_unit", "observed_period", "unit", "value", "indicator_label", "reason", "url", "source_sha256", "freshness", "interpretation", "reconciliation")) for e in evidence]
    peer_view = [pick(f, ("id", "author", "title", "category", "severity", "status", "reasoning", "confidence", "claim_ids", "persona_ids", "event_ids", "evidence_ids", "calculation_ids", "evidence_gaps", "next_validation")) for f in (peers[-peer_limit:] if peer_limit else [])]
    payload = {"role": role, "context": snapshot["context"], "claims": claims, "events": events, "evidence": sources,
               "personas": [pick(p, ("id", "name", "role")) for p in snapshot["personas"]], "calculation": simulation["calculation"],
               "peer_findings": peer_view, "context_window": {"claims_total": len(snapshot["claims"]), "claims_supplied": len(claims),
               "events_total": len(simulation["events"]), "events_supplied": len(events), "peers_total": len(peers), "peers_supplied": len(peer_view), "peer_policy": "immutable_previous_waves"}}
    if information_scoped(snapshot):
        payload["public_brief_seen_by_stakeholders"] = snapshot["information_policy"]["public_brief"]
        payload["internal_review_task"] = {
            "Market Agent": "Bandingkan respons sintetis stakeholder terhadap brief dengan riset internal. Cari perbedaan kebutuhan dan asumsi; jangan menyebut respons sintetis sebagai hasil survei pasar.",
            "Finance Agent": "Tetap pada harga, biaya, margin, pendanaan dan unit economics dari input/kalkulator. Jika input hilang, jelaskan angka apa yang dibutuhkan; jangan mengganti review finansial dengan review klinis atau hukum.",
            "Legal/Compliance Agent": "Tinjau batas klaim yang dibagikan pada brief dan kesenjangan sumber regulasi. Jangan menetapkan kepatuhan atau mengarang peraturan; tandai pertanyaan untuk reviewer kompeten.",
            "Risk Agent": "Telusuri risiko operasional, adopsi, reputasi dan asumsi yang belum diuji dari interaksi. Bedakan skenario dari kejadian nyata; jangan mengulang finding peer tanpa tambahan risiko yang spesifik.",
        }[role]
        payload["room_notice"] = "Anda berada di ruang analisis internal. Stakeholder eksternal tidak menerima dokumen/riset, ide lengkap atau input biaya ini. Respons mereka harus ditafsirkan dari brief yang benar-benar dibagikan."
    if event_limit:
        payload["context_window"]["budget_window"] = True
    if snapshot.get("idea"):
        payload["idea"] = {key: snapshot["idea"][key] for key in ("id", "title", "version", "provenance")}
        payload["idea"]["notice"] = "User-proposed assumption. Consult the supplied idea claim excerpts; do not treat it as verified evidence."
    if simulation.get("interaction_mode") == "swarm-v1":
        payload["discussion_notice"] = "Posts and stance changes are synthetic hypotheses; repeated agreement is not independent evidence. Preserve disagreements and trace findings to supplied event IDs."
        payload["stances"] = {key: pick(state, ("stance", "stance_reason")) for key, state in simulation.get("stances", {}).items()}
        if simulation.get("discussion_quality"):
            payload["discussion_quality"] = deepcopy(simulation["discussion_quality"])
    # A schema may only offer IDs whose actual records are supplied in context.
    scope = dict(snapshot, claims=claims)
    schema = review_schema(role, scope, dict(simulation, events=events), sources)
    finding = schema["properties"]["findings"]
    finding["maxItems"] = 1
    props = finding["items"]["properties"]
    for field, limit in (("id", 80), ("title", 180), ("reasoning", 900), ("next_validation", 450), ("owner_suggestion", 120)):
        props[field]["maxLength"] = limit
    for field in ("claim_ids", "persona_ids", "event_ids", "evidence_ids", "calculation_ids", "evidence_gaps"):
        props[field]["maxItems"] = min(3, props[field].get("maxItems", 3))
    props["evidence_gaps"]["items"]["maxLength"] = 240
    schema["properties"]["disagreements"]["maxItems"] = 2
    schema["properties"]["disagreements"]["items"]["maxLength"] = 500
    return payload, schema


INSTRUCTION = (
    "Review only your domain using the supplied immutable context. Return at most ONE concise additional finding "
    "(or none) and at most TWO brief disagreements. Copy your exact role as author and supplied reference IDs only. "
    "Every finding is NEEDS_VALIDATION; retain uncertainty. If a source is absent, leave its ID array empty and state "
    "the evidence gap. Do not repeat existing findings. Preserve peer disagreements with their authors; peers in the "
    "same wave have not reviewed each other. Legal output is questions for qualified review, never a compliance ruling."
)

GROQ_INSTRUCTION = INSTRUCTION + (
    " Return ZERO or ONE finding, never two. Every reference list (claim_ids, persona_ids, event_ids, evidence_ids, calculation_ids) "
    "must contain at most ONE supplied ID. If no allowed source ID is supplied for a list, return [] for that list. "
    " Every finding MUST include every one of these required keys: "
    + ", ".join(Finding.model_fields)
    + ". Never omit reasoning or owner_suggestion. For owner_suggestion, propose a responsible team or role as an unverified suggestion. Use empty arrays for unsupported reference lists. "
    "Write finding text in Bahasa Indonesia; preserve schema enum values and source IDs exactly."
    " Keep values short: title at most 100 characters; reasoning at most 400 characters in two sentences; "
    "at most two evidence_gaps, each a short phrase under 120 characters; next_validation under 240 characters; "
    "owner_suggestion under 80 characters; each disagreement under 240 characters. Stay well below these limits."
)


def fit_groq_context(role, snapshot, simulation, evidence, peers, payload, schema):
    ceiling = int(os.getenv("PAKAR_GROQ_REQUEST_TOKEN_LIMIT", "7500"))
    def fits(view, formatting):
        view["context_window"]["provider_request_token_ceiling"] = ceiling
        messages = [{"role": "system", "content": SYSTEM_PROMPT + GROQ_INSTRUCTION}, {"role": "user", "content": json.dumps(view, ensure_ascii=False, separators=(",", ":"))}]
        return request_tokens(messages, response_format("pakar_review", formatting), 1800) <= ceiling
    if fits(payload, schema):
        return payload, schema
    bounds = payload["context_window"]
    for events, claims, peer_count in ((4, 24, 6), (2, 12, 4), (1, 6, 2), (1, 3, 0)):
        payload, schema = compact_context(role, snapshot, simulation, evidence, peers, event_limit=min(events, max(1, bounds["events_supplied"])), peer_limit=min(peer_count, bounds["peers_supplied"]), claim_limit=min(claims, bounds["claims_supplied"]))
        if fits(payload, schema):
            return payload, schema
    raise ValueError("Konteks specialist masih melebihi batas satu request Groq; sumber tidak dipotong diam-diam")


def run_paired_reviews(llm, snapshot, simulation, evidence, findings, remaining, cancelled=None):
    """Two workers at most; each wave sees only fully merged previous waves."""
    failures, waves = [], []
    base_cancelled = cancelled if cancelled is not None else llm.cancelled
    concurrency = snapshot.get("config", {}).get("review_concurrency", 2)
    if concurrency not in (1, 2):
        raise ValueError("Review concurrency must be one or two")
    for wave_index in range(2):
        roles = [role for role in ROLES[wave_index * 2:wave_index * 2 + 2] if role in snapshot.get("review_roles", ROLES)]
        if not roles:
            continue
        peers = deepcopy(findings)
        try:
            available = remaining()
        except RunCancelled:
            raise
        except ValueError:
            failures.extend({"role": role, "status": "failed", "message": "Batas waktu review tercapai sebelum dispatch"} for role in ROLES[wave_index * 2:] if role in snapshot.get("review_roles", ROLES))
            break
        # Leave the next wave an equal share; one slow earlier role cannot
        # consume all remaining time. The provider's own ceiling still applies.
        call_seconds = min(60, available / (2 - wave_index) / math.ceil(len(roles) / concurrency))
        wave = {"roles": list(roles), "peer_finding_ids": [f["id"] for f in peers[-12:]], "call_budget_seconds": round(call_seconds, 3)}
        waves.append(wave)
        abort = Event()
        def stopped():
            return abort.is_set() or bool(base_cancelled and base_cancelled())
        # The shared callback also observes abort if one future loses its lease.
        previous_cancelled = llm.cancelled
        llm.cancelled = stopped
        started = time.monotonic()
        try:
            with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="pakar-review") as pool:
                requests = {}
                for role in roles:
                    payload, schema = compact_context(role, snapshot, simulation, evidence, peers)
                    if simulation.get("discussion_policy") == "reactive-v2" and hasattr(llm, "limit"):
                        with llm.lock:
                            available_tokens = max(0, llm.limit - llm.tokens)
                        pending_roles = [r for r in ROLES[wave_index * 2:] if r in snapshot.get("review_roles", ROLES)]
                        target = available_tokens / max(concurrency, len(pending_roles))
                        for window, peer_limit in ((4, 12), (2, 12), (1, 12), (1, 2)):
                            reserve = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + len(INSTRUCTION.encode("utf-8")) + 1024 + 200
                            if llm.structured_outputs:
                                reserve += len(json.dumps(schema).encode("utf-8"))
                            if reserve <= target:
                                break
                            payload, schema = compact_context(role, snapshot, simulation, evidence, peers, event_limit=window, peer_limit=peer_limit)
                    settings = getattr(llm, "settings", None)
                    instruction = INSTRUCTION
                    output_tokens = 1100
                    if settings and is_groq_reasoning_model(settings.llm_base_url, settings.llm_model):
                        instruction = GROQ_INSTRUCTION
                        output_tokens = 1800
                        try:
                            payload, schema = fit_groq_context(role, snapshot, simulation, evidence, peers, payload, schema)
                        except ValueError:
                            failures.append({"role": role, "status": "failed", "message": "Konteks specialist belum muat dalam batas request Groq; tidak ada respons AI yang dibuat"})
                            continue
                    requests[role] = (pool.submit(llm.generate, role, instruction, payload, response_schema=schema,
                                                  call_seconds=call_seconds, max_output_tokens=output_tokens), schema, payload)
                    if concurrency == 1:
                        # Pack the next serial request against settled usage,
                        # while every role in this wave still sees frozen peers.
                        wait((requests[role][0],))
                # Merge in declared role order regardless of request completion.
                for role in roles:
                    if role not in requests:
                        continue
                    try:
                        output = requests[role][0].result()
                        if not isinstance(output, dict) or set(output) != {"findings", "disagreements"}:
                            raise ValueError("Invalid review envelope")
                        proposed = output["findings"]
                        disagreements = output["disagreements"]
                        if not isinstance(proposed, list) or len(proposed) > 1 or not isinstance(disagreements, list) or len(disagreements) > 2 or any(not isinstance(d, str) or len(d) > 500 for d in disagreements):
                            raise ValueError("Review response exceeded its bounded contract")
                        validated = []
                        for raw in proposed:
                            finding = Finding.model_validate(raw).model_dump(mode="json")
                            props = requests[role][1]["properties"]["findings"]["items"]["properties"]
                            for field, value in finding.items():
                                limits = props.get(field, {})
                                if isinstance(value, str) and len(value) > limits.get("maxLength", len(value)):
                                    raise ValueError("Finding text exceeded its bounded contract")
                                if isinstance(value, list) and (len(value) > limits.get("maxItems", len(value)) or any(isinstance(v, str) and len(v) > limits.get("items", {}).get("maxLength", len(v)) for v in value)):
                                    raise ValueError("Finding references exceeded their bounded contract")
                            if finding["author"] != role:
                                raise ValueError("Finding author mismatch")
                            finding["id"] = f"finding-{len(findings) + len(validated) + 1}"
                            context = requests[role][2]
                            validated.append(validate_finding_references(finding, dict(snapshot, claims=context["claims"]), dict(simulation, events=context["events"]), context["evidence"]))
                        findings.extend(validated)
                        wave.setdefault("disagreements", []).extend({"author": role, "summary": d} for d in disagreements)
                    except RunCancelled:
                        abort.set()
                        raise
                    except Exception as error:
                        failures.append({"role": role, "status": "failed", "error_type": type(error).__name__, "message": "Review specialist gagal atau budget tercapai; hasil tidak dipromosikan menjadi valid"})
        finally:
            llm.cancelled = previous_cancelled
            wave["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return {"failures": failures, "waves": waves, "disagreements": [item for wave in waves for item in wave.get("disagreements", [])]}
