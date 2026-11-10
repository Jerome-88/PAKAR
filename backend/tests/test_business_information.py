import json
from copy import deepcopy

import pytest
from app.business.information import freeze, public_profiles, safe_view, public_schema, public_context
from app.business.dialogue_protocol import request_view, decode
from app.business.discussion import DialogueSimulation, ReactiveAgenda
from app.business.structured import swarm_action_schema
from app.business.contracts import DialogueAction
from app.business.reviews import compact_context
from test_business_swarm import make_sim, action
from app.business.information import public_scenario_event

SECRET = "INTERNAL_ONLY_8f31_surveys_31percent_margin_strategy"


def test_explicit_scenario_announcement_arrives_only_when_event_begins():
    sim, snapshot = case()
    snapshot["shock"] = {"kind": "supplier_cost_increase", "magnitude_percent": "20", "region": "Indonesia", "effective_round": 2, "duration_rounds": 1, "description": "Biaya bahan meningkat sebagai asumsi skenario.", "announce_to_personas": True}
    assert public_scenario_event(snapshot, 1) is None
    assert public_scenario_event(snapshot, 2)["status"] == "active"
    assert public_scenario_event(snapshot, 3)["status"] == "expired"
    actor = next(iter(sim.personas))
    view = safe_view(sim, actor, {"round": 2}, sim.turn_context(actor), snapshot, compact=True)
    assert view["scenario_event"]["magnitude_percent"] == "20"
    assert all(secret not in json.dumps(view) for secret in [SECRET, "38123", "9912345", "internal-survey"])
    snapshot["shock"]["announce_to_personas"] = False
    assert public_scenario_event(snapshot, 2) is None


def case():
    old = make_sim()
    people = [p.model_dump(mode="json") for p in old.personas.values()]
    for p in people:
        p.update(name=SECRET + p['id'], goals=[SECRET], constraints=[SECRET], knowledge=[SECRET], interests=[SECRET])
    people[0]['provenance']['perspective']={'untrusted_metadata':SECRET}
    sim = DialogueSimulation("privacy-case", people, {"selling_price":"71991", "variable_cost":"38123", "fixed_cost_monthly":"9912345", "volume_monthly":"87991"}, 80, strict_trigger_reply=True, public_room=True)
    snapshot = {"personas":people, "context":{"decision_question":SECRET, "industry":SECRET, "region":SECRET, "target_customer":SECRET},
                "claims":[{"id":"internal-survey", "quote":SECRET, "normalized_text":SECRET, "classification":"assumption", "evidence_status":"UNAVAILABLE"}],
                "idea":{"id":"internal-idea", "title":SECRET, "text":SECRET, "version":1, "provenance":"user"},
                "values":sim.values, "config":{"interaction_mode":"swarm", "choice_dialogue":True, "document_grounding":True}}
    freeze(snapshot, "Konsep pasta gigi dua rasa yang dapat dipilih pengguna. Warna berubah sekitar dua menit sebagai fitur usulan, manfaatnya belum diuji.")
    return sim, snapshot


def test_groq_choice_options_survive_public_projection_without_internal_data(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    sim, snapshot = case()
    actor = next(iter(sim.personas))
    context = sim.turn_context(actor)
    view, schema, references, _ = request_view(sim, actor, {"actor_id": actor}, context, snapshot, swarm_action_schema(sim, actor, context))
    assert set(view["choice_options"]) == set(references.choices) == set(schema["properties"]["choice"]["enum"])
    assert len(view["choice_option_columns"]) == 4
    assert SECRET not in json.dumps(view)


def test_every_external_profile_and_prompt_excludes_internal_sources_and_business_inputs():
    sim, snapshot = case()
    original = deepcopy(snapshot)
    profiles = public_profiles(snapshot['personas'])
    assert SECRET not in json.dumps(profiles)
    assert len({p['name'] for p in profiles.values()}) == len(profiles)
    for actor in sim.personas:
        context = sim.turn_context(actor)
        view, schema, *_ = request_view(sim, actor, {"actor_id":actor}, context, snapshot, swarm_action_schema(sim, actor, context))
        wire = json.dumps({'view':view, 'schema':schema})
        assert all(secret not in wire for secret in [SECRET,'71991','38123','9912345','87991','internal-survey','internal-idea'])
        assert view['public_brief'] == snapshot['information_policy']['public_brief']
        assert 'document_context' not in view and 'user_proposed_idea' not in view
        assert all('perspective' not in p for p in view['participants'])
        assert not any('offer_terms' in choice or 'adjust_price' in choice for choice in schema.get('properties',{}).get('choice',{}).get('enum',[]))
    assert snapshot == original


def test_guided_rounds_keep_role_routing_and_exclude_private_sources():
    sim, snapshot = case()
    snapshot["config"]["rounds"] = 4
    supplier = next(key for key, persona in sim.personas.items() if persona.role == "supplier")
    operator = next(key for key, persona in sim.personas.items() if persona.role == "operator")
    context = sim.turn_context(supplier)
    first, schema, refs, _ = request_view(sim, supplier, {"actor_id": supplier, "round": 1}, context, snapshot, swarm_action_schema(sim, supplier, context))
    last, *_ = request_view(sim, supplier, {"actor_id": supplier, "round": 4}, context, snapshot, swarm_action_schema(sim, supplier, context))
    assert first["discussion_phase"]["focus"] != last["discussion_phase"]["focus"]
    assert "posisi akhir" in last["discussion_phase"]["focus"]
    assert "uji" in first["response_contract"]["stance"].lower()
    questions = [choice for choice in refs.choices.values() if choice["dialogue_act"] == "question"]
    assert questions and all(choice["target_id"] == operator for choice in questions)
    assert set(schema["properties"]["choice"]["enum"]) == set(refs.choices)
    assert schema["properties"]["content"]["maxLength"] == 1000
    legacy = deepcopy(snapshot)
    legacy["information_policy"]["dialogue_guidance"] = "reasoned-exchange-v2"
    _, legacy_schema, *_ = request_view(sim, supplier, {"actor_id": supplier, "round": 1}, context, legacy, swarm_action_schema(sim, supplier, context))
    assert legacy_schema["properties"]["content"]["maxLength"] == 600
    wire = json.dumps({"first": first, "last": last, "schema": schema})
    assert all(value not in wire for value in [SECRET, "71991", "38123", "internal-survey"])


def test_internal_specialist_retains_original_sources_for_cross_checking():
    sim, snapshot = case()
    for role in ('Market Agent','Finance Agent','Legal/Compliance Agent','Risk Agent'):
        payload, _ = compact_context(role, snapshot, sim.snapshot(), [], [])
        assert SECRET in json.dumps(payload)
        assert payload['claims'][0]['id'] == 'internal-survey'


def test_external_reply_receives_actual_peer_message_and_personal_lens_without_private_context():
    sim, snapshot = case()
    customers = [p.id for p in sim.personas.values() if p.role == 'customer']
    a, b = customers[:2]
    parent = sim.apply(DialogueAction(**action(sim,a,target_id=b,content='Dua rasa menarik, tetapi bagaimana memilih rasanya?').model_dump(),dialogue_act='question'),1)
    turn={'actor_id':b,'trigger_event_id':parent['id'],'reason':'peer_exchange','round':2}
    sim.current_dispatch=turn
    context=sim.turn_context(b)
    view, _, references, trigger=request_view(sim,b,turn,context,snapshot,swarm_action_schema(sim,b,context))
    assert view['in_reply_to']['content']==parent['content'] and view['in_reply_to']['role']=='customer'
    assert view['assigned_message']==parent['sequence']
    raw={'content':'Saya juga ingin cara memilih yang sederhana; label pagi dan malam bisa membantu, tetapi mekanismenya belum dijelaskan.','stance':'conditional','stance_reason':'Menunggu kejelasan cara memilih'}
    reply=decode(raw,sim,b,references,trigger)
    assert reply.content==raw['content'] and reply.reply_to==parent['id'] and reply.target_id==a
    assert sim.apply(reply,2)['dialogue_act']=='answer'
    assert SECRET not in json.dumps(view)


def test_peer_exchange_uses_base_slots_without_starving_customers_or_forcing_stances():
    sim, _ = case()
    for actor in sim.turn_order():
        sim.current_dispatch=None
        sim.apply(DialogueAction(**action(sim,actor,content=f'Prioritas saya berbeda untuk peserta {actor}.').model_dump(),dialogue_act='statement'),1)
    before=deepcopy(sim.values)
    turns=list(ReactiveAgenda(sim,followups=0,peer_exchange=True).turns(2))
    assert len(turns)==len(sim.personas)
    assert {t['actor_id'] for t in turns}==set(sim.personas)
    customers={p.id for p in sim.personas.values() if p.role=='customer'}
    for turn in turns:
        if turn['actor_id'] in customers:
            assert turn['reason']=='peer_exchange' and not turn['followup']
            parent=next(e for e in sim.events if e['id']==turn['trigger_event_id'])
            assert parent['actor_id'] in customers and parent['actor_id']!=turn['actor_id']
    assert sim.values==before and all(s['stance']=='undecided' for s in sim.states.values())
    assert all(t['reason']=='participant_turn' for t in ReactiveAgenda(sim,0).turns(2))


def test_public_room_rejects_private_messages_and_financial_actions_atomically():
    sim, _=case()
    supplier=next(p.id for p in sim.personas.values() if p.role=='supplier')
    operator=next(p.id for p in sim.personas.values() if p.role=='operator')
    before=deepcopy(sim.snapshot())
    for changes in ({'visibility':'participants'}, {'kind':'offer_terms','amount':'38123','target_id':operator,'visibility':'participants'}):
        raw=action(sim,supplier,**changes).model_dump()
        with pytest.raises(ValueError,match='Ruang stakeholder'):
            sim.apply(DialogueAction(**raw,dialogue_act='statement'),1)
        assert sim.snapshot()==before


def test_noncompact_paths_do_not_bypass_information_projection():
    sim,snapshot=case()
    actor=sim.turn_order()[0]
    snapshot['config']['interaction_mode']='pairwise'
    ctx={'visible_events':[{'id':'private','kind':'offer_terms','visibility':'participants','actor_id':actor,'target_id':'other','content':SECRET,'amount':'38123'}]}
    view=safe_view(sim,actor,{'actor_id':actor},ctx,snapshot,compact=False)
    assert SECRET not in json.dumps(view) and '71991' not in json.dumps(view)
    assert view['environment']=={} and view['visible_events']==[]
    schema=public_schema({'properties':{'kind':{'enum':['offer_terms','accept_terms','express_concern']},'amount':{'enum':['38123']}}},False)
    assert schema['properties']['kind']['enum']==['express_concern']
    assert schema['properties']['amount']=={'type':'null'}
    scoped_schema=public_schema({'properties':{'kind':{'enum':['express_concern']},'amount':{'type':'null'},'parent_event_ids':{'type':'array','items':{'enum':['PRIVATE_SHOCK_EVENT']}}}},False,[])
    assert 'PRIVATE_SHOCK_EVENT' not in json.dumps(scoped_schema)
    assert scoped_schema['properties']['parent_event_ids']['maxItems']==0


def test_live_api_requires_explicit_brief_before_enqueuing_any_paid_job(tmp_path, database_url, monkeypatch):
    from fastapi.testclient import TestClient
    from test_business_api import make_app, register
    from test_business_quick import upload_only, CASES
    from test_business_partial_recovery import configure_local_live
    from app.business.tables import business_analyses
    from sqlalchemy import select, func
    app=make_app(tmp_path,database_url)
    with TestClient(app) as client:
        register(client)
        service, _=configure_local_live(app,monkeypatch)
        service.oasis=object()  # Availability only; missing brief must stop before dispatch.
        p=upload_only(client,CASES[0])
        base=f"/api/v1/business/projects/{p['id']}"
        response=client.post(base+'/quick-analysis',json={'expected_revision':p['revision'],'engine':'oasis'},headers={'Idempotency-Key':'no-brief'})
        assert response.status_code==422 and response.json()['error']['code']=='public_brief_required'
        with app.state.repository.engine.connect() as db:
            assert db.execute(select(func.count()).select_from(business_analyses)).scalar_one()==0
        assert service.repository.project(p['id'],client.get('/api/auth/me').json()['user']['id'])['claims']
