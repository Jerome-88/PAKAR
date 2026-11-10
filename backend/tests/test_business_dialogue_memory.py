from app.business.dialogue_memory import decision_contract, public_discussion_memory, repetition_check, withhold_repetition
from app.business.discussion import ReactiveAgenda
from app.business.swarm import LENSES
from test_business_discussion import simulation, dialogue
from app.business.contracts import Shock


def test_duplicate_text_is_withheld_but_a_different_tradeoff_is_not():
    previous = "Saya memilih satu produk dengan dua rasa jika pilihan rasanya jelas. Saya bisa menerima harga lebih tinggi agar tidak perlu membawa dua tube, selama pemilihnya mudah dipakai."
    history = [{"id": "message-1", "actor_id": "buyer-a", "kind": "post_message", "content": previous}]
    assert repetition_check(previous, history, "buyer-a")["comparison"] == "same_persona"
    assert repetition_check(previous, history, "buyer-b")["comparison"] == "another_persona"
    assert withhold_repetition(repetition_check(previous, history, "buyer-b"), "undecided", "conditional")
    assert not withhold_repetition(repetition_check(previous, history, "buyer-a"), "conditional", "oppose")
    assert repetition_check("Saya memilih dua tube terpisah. Prioritas saya harga total yang lebih rendah, bukan membawa satu produk; saya ingin membandingkan alternatif tanpa mekanisme tambahan.", history, "buyer-b") is None


def test_public_memory_contains_unanswered_questions_and_excludes_private_notes():
    profiles = {"a": {"name": "Pembeli"}, "b": {"name": "Pengelola"}}
    public = {"id": "public", "sequence": 1, "actor_id": "a", "target_id": "b", "kind": "post_message", "visibility": "public", "dialogue_act": "question", "content": "Bagaimana cara memilih rasa?"}
    private = {**public, "id": "private", "sequence": 2, "visibility": "participants", "content": "CONFIDENTIAL_COST_SENTINEL"}
    memory = public_discussion_memory([public, private], "b", profiles)
    assert memory["questions_for_you"][0]["number"] == 1
    assert "CONFIDENTIAL_COST_SENTINEL" not in str(memory)
    answer = {**public, "id": "answer", "sequence": 3, "actor_id": "b", "target_id": "a", "kind": "reply_message", "dialogue_act": "answer", "reply_to": "public", "content": "Pemilih rasa belum diputuskan; dua kompartemen adalah usulan."}
    assert not public_discussion_memory([public, private, answer], "b", profiles)["questions_for_you"]


def test_buyers_have_distinct_priorities_and_acceptable_compromises():
    contracts = [decision_contract("customer", label) for label, _ in LENSES]
    assert len({contract["priority"] for contract in contracts}) == 6
    assert len({contract["acceptable_compromise"] for contract in contracts}) == 6


def test_adaptive_middle_rounds_do_not_force_everyone_to_repeat_but_closing_includes_all():
    sim = simulation()
    for actor in sim.turn_order():
        sim.current_dispatch = None
        sim.apply(dialogue(sim, actor, content=f"Saya sudah menyampaikan prioritas awal dari perspektif {actor}."), 1)
    middle = list(ReactiveAgenda(sim, followups=0, adaptive=True, final_round=4).turns(2))
    assert middle and all(sim.personas[turn["actor_id"]].role == "operator" for turn in middle)
    closing = list(ReactiveAgenda(sim, followups=0, adaptive=True, final_round=4).turns(4))
    assert {turn["actor_id"] for turn in closing} == set(sim.personas)


def test_a_shared_sudden_event_gives_all_personas_a_chance_to_react():
    sim = simulation()
    for actor in sim.turn_order():
        sim.current_dispatch = None
        sim.apply(dialogue(sim, actor, content=f"Prioritas awal dari perspektif {actor}."), 1)
    sim.inject(Shock(kind="supplier_cost_increase", region="Indonesia", magnitude_percent="20", effective_round=2, duration_rounds=1, announce_to_personas=True), 2)
    turns = list(ReactiveAgenda(sim, followups=0, adaptive=True, final_round=4).turns(2))
    assert {turn["actor_id"] for turn in turns} == set(sim.personas)
