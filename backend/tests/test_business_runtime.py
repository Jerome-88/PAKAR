import asyncio
import json
import sqlite3
import sys
import types
from enum import Enum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from app.business.intake import discover
from app.business.oasis_bridge import run
from app.oasis_direct import DirectOasisEngine


def test_oasis_business_bridge_passes_scoped_state_and_validates_interactions(tmp_path, monkeypatch):
    """Exercise the real bridge/reducer with an in-process OASIS protocol fake.

    This tests integration contracts without claiming live model quality.
    """
    monkeypatch.setenv("OASIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_API_KEY", "test-only")
    personas = discover({"industry": "F&B", "region": "Jakarta", "target_customer": "Pekerja kantor"}, [])[:3]
    profiles = []
    prompts = []
    closed = []

    class ActionType(Enum):
        INTERVIEW = "interview"
        DO_NOTHING = "do_nothing"

    class ManualAction:
        def __init__(self, action_type, action_args):
            self.action_type = action_type
            self.action_args = action_args

    class Graph:
        def get_agent(self, index):
            return index

    async def generate_reddit_agent_graph(profile_path, **kwargs):
        profiles.extend(json.loads(open(profile_path, encoding="utf-8").read()))
        # camel-oasis 0.2.5 indexes these fields rather than defaulting them.
        for profile in profiles:
            for field in ("mbti", "gender", "age", "country"):
                assert profile[field] == "unspecified"
        return Graph()

    class Environment:
        def __init__(self, database_path, **kwargs):
            self.database = database_path

        async def reset(self):
            with sqlite3.connect(self.database) as db:
                db.execute("CREATE TABLE trace (user_id INTEGER, action TEXT, info TEXT)")

        async def step(self, actions):
            for index, action in actions.items():
                prompt = json.loads(action.action_args["prompt"])
                prompts.append(prompt)
                actor = prompt["actor_id"]
                targets = prompt["targets"]
                role = next(p["role"] for p in personas if p["id"] == actor)
                offered = [e for e in prompt["visible_events"] if e["kind"] == "offer_terms" and e["target_id"] == actor]
                if role == "supplier":
                    proposal = {"kind": "offer_terms", "target_id": next(p["id"] for p in targets if p["role"] == "operator"), "amount": prompt["environment"]["supplier_cost"]}
                elif role == "operator" and offered:
                    proposal = {"kind": "accept_terms", "target_id": offered[-1]["actor_id"], "parent_event_ids": [offered[-1]["id"]]}
                else:
                    proposal = {"kind": "express_concern", "target_id": targets[0]["id"]}
                response = {"actor_id": actor, "expected_version": prompt["state"]["version"], "rationale": "Hypothetical response for protocol validation", **proposal}
                with sqlite3.connect(self.database) as db:
                    db.execute("INSERT INTO trace VALUES (?, ?, ?)", (index, action.action_type.value, json.dumps({"response": json.dumps(response)})))

        async def close(self):
            closed.append(True)

    camel = types.ModuleType("camel")
    models = types.ModuleType("camel.models")
    models.ModelFactory = types.SimpleNamespace(create=lambda **kwargs: object())
    camel_types = types.ModuleType("camel.types")
    camel_types.ModelPlatformType = types.SimpleNamespace(OPENAI="openai")
    oasis = types.ModuleType("oasis")
    oasis.ActionType, oasis.ManualAction = ActionType, ManualAction
    oasis.generate_reddit_agent_graph = generate_reddit_agent_graph
    oasis.DefaultPlatformType = types.SimpleNamespace(REDDIT="reddit")
    oasis.make = lambda **kwargs: Environment(**kwargs)
    for name, module in (("camel", camel), ("camel.models", models), ("camel.types", camel_types), ("oasis", oasis)):
        monkeypatch.setitem(sys.modules, name, module)
    snapshot = {"personas": personas, "values": {"selling_price": "30000", "variable_cost": "12000", "fixed_cost_monthly": "36000000", "volume_monthly": None}, "config": {"rounds": 2, "max_events": 30, "seed": 42, "max_tokens": 100000, "max_seconds": 10}}
    emitted = []
    result = asyncio.run(run({"snapshot": snapshot, "runtime_id": "isolated-attempt", "run_id": "analysis-1"}, emitted.append))
    assert result["engine"] == "oasis-business"
    assert any(e["kind"] == "accept_terms" for e in result["events"])
    assert result["calculation"]["break_even_units_monthly"] == "2000"
    customer_prompt = next(p for p in prompts if p["actor_id"] == "persona-customer")
    assert "supplier_cost" not in customer_prompt["environment"]
    assert not any(e["kind"] == "offer_terms" for e in customer_prompt["visible_events"])
    assert closed == [True]
    assert len(profiles) == len(personas)
    assert any(e["kind"] == "interaction" for e in emitted)
    assert result["usage"]["actual_tokens"] is None
    assert result["usage"]["reserved_tokens_upper_bound"] > 0


@pytest.mark.parametrize("mode", ["pairwise", "swarm", "reactive", "compact", "choices", "scoped", "scoped_pairwise"])
def test_installed_oasis_and_sdk_follow_turn_schemas_against_local_provider(tmp_path, monkeypatch, mode):
    """Real pinned runtime/SDK, local scripted HTTP responses; no paid LLM."""
    runtime = Path(__file__).resolve().parents[1] / "oasis_engine_runtime"
    if not any((runtime / relative).exists() for relative in (".venv/Scripts/python.exe", ".venv/bin/python")):
        pytest.skip("isolated OASIS runtime is not installed")
    personas = [p for p in discover({"industry": "F&B", "region": "Bandung", "target_customer": "Mahasiswa"}, []) if p["role"] in {"operator", "supplier"}]
    if mode in {"swarm", "reactive", "compact", "choices", "scoped"}:
        from app.business.swarm import expand_customer_cohort
        base = [p for p in discover({"industry": "F&B", "region": "Bandung", "target_customer": "Mahasiswa"}, []) if p["role"] in {"operator", "supplier", "customer"}]
        personas = expand_customer_cohort(base, 2, 4)
    if mode.startswith("scoped"):
        for p in personas:
            p.update(name="CONFIDENTIAL_SOURCE_SENTINEL", goals=["CONFIDENTIAL_SOURCE_SENTINEL"], constraints=["CONFIDENTIAL_SOURCE_SENTINEL"], knowledge=["CONFIDENTIAL_SOURCE_SENTINEL"], interests=["CONFIDENTIAL_SOURCE_SENTINEL"])
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_completion(self, body, action):
            response = {"id": f"local-{len(calls)}", "object": "chat.completion", "created": 1, "model": body["model"], "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(action)}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 40, "completion_tokens": 50, "total_tokens": 90}}
            encoded = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(body)
            prompt = json.loads(body["messages"][-1]["content"])
            actor = prompt["actor_id"]
            role = next(p["role"] for p in personas if p["id"] == actor)
            if mode in {"compact", "choices", "scoped"}:
                result = {"content": f"Respons lokal dari {role}; belum ada bukti pasar.", "stance": prompt["current_stance"], "stance_reason": "Bukti belum tersedia"}
                if prompt["assigned_message"] is None:
                    others = [e for e in prompt["visible_messages"] if e["author_id"] != actor and e["kind"] in {"post_message", "reply_message"}]
                    parent = others[-1] if others else None
                    if mode in {"choices", "scoped"}:
                        target_number = next(i for i, p in enumerate(personas, 1) if p["role"] == "customer" and p["id"] != actor)
                        choice = f"reply_question_message_{parent['number']}" if parent else f"open_question_participant_{target_number}"
                        allowed = body["response_format"]["json_schema"]["schema"]["properties"]["choice"]["enum"]
                        if choice not in allowed:
                            choice = next(item for item in allowed if item.startswith(("reply_question_", "open_question_")))
                        result.update(choice=choice, amount=None)
                    else:
                        result.update(action="reply_message" if parent else "post_message", target_id=parent["author_id"] if parent else next(p["id"] for p in personas if p["role"] == "customer" and p["id"] != actor), reply_to_message=parent["number"] if parent else None, dialogue_act="question", amount=None)
                return self.send_completion(body, result)
            if mode == "scoped_pairwise":
                return self.send_completion(body, {"actor_id": actor, "target_id": prompt["targets"][0]["id"], "kind": "express_concern", "expected_version": prompt["state"]["version"], "amount": None, "parent_event_ids": [], "rationale": "Local public concept response; no internal figures."})
            target = prompt["targets"][0]["id"]
            offers = [e for e in prompt["visible_events"] if e["kind"] == "offer_terms" and e["target_id"] == actor]
            action = {"actor_id": actor, "target_id": target, "kind": "offer_terms" if role == "supplier" else "accept_terms", "expected_version": prompt["state"]["version"], "amount": 12000 if role == "supplier" else None, "parent_event_ids": [offers[-1]["id"]] if offers else [], "rationale": "Local protocol fixture; not a live model response"}
            if mode in {"swarm", "reactive"}:
                parent = next((e for e in prompt["visible_events"] if e["id"] == prompt["suggested_reply_to"]), None)
                business = role == "supplier" or (role == "operator" and offers)
                if business:
                    action.update(target_id=next(p["id"] for p in prompt["targets"] if p["role"] == ("operator" if role == "supplier" else "supplier")), visibility="participants", thread_id=None, reply_to=None, content="", stance=prompt["state"]["stance"], stance_reason=prompt["state"]["stance_reason"], influenced_by_event_ids=[])
                else:
                    action.update(kind="reply_message" if parent else "post_message", target_id=parent["actor_id"] if parent else "all", amount=None, parent_event_ids=[parent["id"]] if parent else [], visibility="public", thread_id=parent["thread_id"] if parent else None, reply_to=parent["id"] if parent else None, content="Respons diskusi dari provider lokal; bukan opini pasar nyata.", stance="conditional", stance_reason="Menunggu validasi kebutuhan", influenced_by_event_ids=[parent["id"]] if parent else [])
                if mode == "reactive":
                    trigger = prompt["turn_request"]["trigger_event_id"]
                    intent = "answer" if trigger else "question" if role in {"operator", "customer"} else "statement"
                    action.update(kind="reply_message" if parent else "post_message", target_id=parent["actor_id"] if parent else next(p["id"] for p in personas if p["role"] == "customer" and p["id"] != actor), amount=None, parent_event_ids=[parent["id"]] if parent else [], visibility="public", thread_id=parent["thread_id"] if parent else None, reply_to=parent["id"] if parent else None, content=f"Pertukaran lokal khusus {role}; bukan pengamatan pasar.", stance=prompt["state"]["stance"], stance_reason=prompt["state"]["stance_reason"], influenced_by_event_ids=[], dialogue_act=intent)
                    assert any('"role": "' + role + '"' in message["content"] and "ONE stakeholder" in message["content"] for message in body["messages"] if message["role"] == "system")
            self.send_completion(body, action)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("LLM_API_KEY", "local-test-only")
    monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("LLM_MODEL", "mistralai/mistral-nemo")
    monkeypatch.setenv("LLM_STRUCTURED_OUTPUTS", "false")
    engine = DirectOasisEngine(runtime, tmp_path / "oasis")
    # Cold imports of the installed OASIS/ML stack can consume most of 60s on
    # Windows. This protocol test must leave room for every local scripted turn;
    # short-deadline/actual process termination is covered separately.
    snapshot = {"response_mode": "json_schema", "personas": personas, "values": {"selling_price": "30000", "variable_cost": "12000", "fixed_cost_monthly": "36000000"}, "config": {"rounds": 2, "max_events": 8, "seed": 42, "max_tokens": 100000, "max_seconds": 120, "interaction_mode": mode}}
    if mode in {"swarm", "reactive", "compact", "choices", "scoped"}:
        snapshot["config"]["persona_turn_seconds"] = 5  # Fast local provider, no remote latency.
    if mode in {"reactive", "compact", "choices", "scoped"}:
        snapshot["config"].update(interaction_mode="swarm", discussion_policy="reactive-v2", strict_trigger_reply=True, business_system_prompt=True, max_events=16, max_tokens=18000)
        snapshot["context"] = {"decision_question": "Asumsi apa yang perlu diperiksa?"}
        if mode in {"compact", "choices", "scoped"}:
            snapshot["config"]["compact_dialogue"] = True
            snapshot["config"]["choice_dialogue"] = mode in {"choices", "scoped"}
        if mode == "choices":
            snapshot["config"]["document_grounding"] = True
            snapshot["claims"] = [
                {"id": "survey-heading", "quote": "Alasan bersedia membayar lebih; angka studi kasus, bukan hasil uji produk.", "source": {"document_id": "survey", "locator": {"char_start": 0}}},
                {"id": "survey-value", "quote": "52%: Menginginkan hasil terlihat.", "source": {"document_id": "survey", "locator": {"char_start": 100}}},
                {"id": "private-cost", "quote": "PRIVATE_FINANCIAL_QUOTE", "variable": "variable_cost", "source": {"document_id": "internal"}},
            ]
    if mode.startswith("scoped"):
        from app.business.information import freeze
        snapshot["config"]["spending"] = {"limit_usd": ".03", "prices": {"prompt": ".1", "completion": ".5", "request": "0"}}
        snapshot["context"] = {"decision_question": "CONFIDENTIAL_SOURCE_SENTINEL"}
        snapshot["idea"] = {"text": "CONFIDENTIAL_SOURCE_SENTINEL"}
        snapshot["claims"] = [{"id": "private-research", "quote": "CONFIDENTIAL_SOURCE_SENTINEL", "source": {}}]
        snapshot["values"] = {"selling_price": "71991", "variable_cost": "38123", "fixed_cost_monthly": "9912345"}
        if mode == "scoped_pairwise":
            snapshot["config"]["interaction_mode"] = "pairwise"
        freeze(snapshot, "Proposed toothpaste with two selectable flavors. The feature has not been tested.")
    try:
        result = engine.run_business_simulation("local-schema-integration", snapshot, lambda _: None)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert result["stop_reason"] == "round_limit"
    assert result["response_mode"] == "json_schema"
    if mode.startswith("scoped"):
        assert 0 < result["usage"]["spending"]["charged_or_reserved_usd"] <= .03
        assert all(call.get("reserved_cost_upper_bound_usd", 0) > 0 for call in result["usage"]["calls"])
    if mode == "scoped_pairwise":
        assert [e["kind"] for e in result["events"]] == ["express_concern"] * 4
    elif mode == "pairwise":
        assert [e["kind"] for e in result["events"]] == ["offer_terms", "accept_terms", "offer_terms", "accept_terms"]
    else:
        assert result["interaction_mode"] == "swarm-v1" and result["threads"] and result["stances"]
        assert not any(e["kind"] == "action_rejected" for e in result["events"])
        customers = {p["id"] for p in personas if p["role"] == "customer"}
        assert any(e["kind"] == "reply_message" and e["actor_id"] in customers and e["target_id"] in customers for e in result["events"])
    expected_calls = len(result["events"]) if mode in {"reactive", "compact", "choices", "scoped"} else 4 if mode in {"pairwise", "scoped_pairwise"} else 8
    if mode in {"reactive", "compact", "choices", "scoped"}:
        assert expected_calls > 8 and any(e["dispatch"]["followup"] for e in result["events"])
        assert result["discussion_quality"]["reciprocal_pairs"] > 0
        assert len({call["turn_index"] for call in result["usage"]["calls"]}) == expected_calls
    assert len(calls) == expected_calls
    assert result["usage"]["call_count"] == expected_calls
    assert result["usage"]["actual_tokens"] == expected_calls * 90
    assert result["usage"]["reserved_tokens_upper_bound"] == expected_calls * 90
    assert result["usage"]["dispatched_reservation_upper_bound"] > expected_calls * 90
    assert result["usage"]["cost"] is None  # Local provider deliberately omits billing.
    assert result["usage"]["cost_status"] == "unknown"
    for body in calls:
        if mode.startswith("scoped"):
            assert all(secret not in json.dumps(body) for secret in ["CONFIDENTIAL_SOURCE_SENTINEL", "71991", "38123", "9912345", "private-research"])
        prompt = json.loads(body["messages"][-1]["content"])
        if mode.startswith("scoped"):
            assert "two selectable flavors" in prompt["public_brief"]
            assert "document_context" not in prompt and "user_proposed_idea" not in prompt
        formatting = body["response_format"]
        assert formatting["type"] == "json_schema"
        properties = formatting["json_schema"]["schema"]["properties"]
        if mode in {"compact", "choices", "scoped"}:
            if mode == "choices":
                assert [e["claim_id"] for e in prompt["document_context"]["excerpts"]] == ["survey-heading", "survey-value"]
                assert "PRIVATE_FINANCIAL_QUOTE" not in json.dumps(prompt)
                assert prompt["own_perspective"]["name"]
            assert "actor_id" not in properties and "expected_version" not in properties
            if prompt["assigned_message"] is not None:
                assert set(properties) == {"content", "stance", "stance_reason"}
            continue
        assert properties["actor_id"]["enum"] == [prompt["actor_id"]]
        assert properties["expected_version"]["enum"] == [prompt["state"]["version"]]
