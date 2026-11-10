import { BusinessText } from "./BusinessText";
import { personaPositions, roleLabels } from "./resultSummary";
import { useMemo, useState } from "react";
import type { BusinessEvent, BusinessPersona, StanceValue, SwarmStance, DialogueQuality } from "../../api/business";
import { PersonaAvatar } from "../../components/PersonaAvatar/PersonaAvatar";
import "./SwarmDiscussion.css";

const stanceLabel: Record<StanceValue, string> = { support: "Mendukung", oppose: "Menolak", conditional: "Bersyarat", undecided: "Belum memutuskan" };
const excerpt = (value: string, limit: number) => value.length <= limit ? value : `${value.slice(0, limit).replace(/\s+\S*$/, "")}…`;
const intentLabel: Record<string, string> = { statement: "Pernyataan", question: "Pertanyaan", answer: "Jawaban", challenge: "Sanggahan", clarification: "Klarifikasi", proposal: "Usulan", abstain: "Tidak menambah pesan" };

export function SwarmDiscussion({ events, personas, stances, quality, openEvent, compact = false }: { events: BusinessEvent[]; personas: BusinessPersona[]; stances?: Record<string, SwarmStance>; quality?: DialogueQuality | null; openEvent: (id: string) => void; compact?: boolean }) {
  const [selected, setSelected] = useState("all");
  const messages = useMemo(() => events.filter(e => e.kind === "post_message" || e.kind === "reply_message"), [events]);
  const roots = useMemo(() => messages.filter(e => e.kind === "post_message"), [messages]);
  const people = useMemo(() => Object.fromEntries(personas.map(p => [p.id, p])), [personas]);
  const byId = useMemo(() => Object.fromEntries(messages.map(e => [e.id, e])), [messages]);
  const positions = useMemo(() => personaPositions(events, personas, stances), [events, personas, stances]);
  const jump = (id: string) => {
    const element = document.getElementById(`swarm-message-${id}`);
    if (element) { element.scrollIntoView({ behavior: "smooth", block: "center" }); element.focus({ preventScroll: true }); }
    else openEvent(id);
  };

  return <section className="swarm-discussion" aria-label="Diskusi swarm">
    <h2>Diskusi stakeholder</h2>
    <p>{messages.length} pesan tersimpan · {personas.length} persona · {new Set(messages.map(event => event.round)).size} ronde dengan pesan. Pilih topik atau baca seluruh percakapan di bawah.</p>
    {!compact && <p>Persona saling menanggapi dari sudut pandangnya. Posisi dan perubahan sikap ini sintetis; jumlah peserta yang sepakat bukan bukti pasar.</p>}
    {!compact && quality && <section className="swarm-quality" aria-label="Struktur percakapan"><details><summary>Catatan kualitas percakapan</summary><h3>Struktur percakapan yang tercatat</h3>
      <dl><div><dt>Pesan</dt><dd>{quality.messages}</dd></div><div><dt>Pasangan saling membalas</dt><dd>{quality.reciprocal_pairs}</dd></div><div><dt>Balasan antarcustomer</dt><dd>{quality.customer_peer_replies}</dd></div><div><dt>Pesan sangat mirip</dt><dd>{quality.near_duplicate_event_ids.length}</dd></div></dl>
      {!!quality.warnings.length && <ul>{quality.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>}
      {!!quality.questions_without_recipient_reply.length && <details><summary>Pertanyaan tanpa balasan penerima ({quality.questions_without_recipient_reply.length})</summary>{quality.questions_without_recipient_reply.map(id => <button key={id} type="button" className="business-text-button" onClick={() => jump(id)}>{excerpt(byId[id]?.content ?? id, 120)}</button>)}</details>}
      <p>{quality.notice}</p></details></section>}
    {!messages.length ? <p role="status">Belum ada pesan diskusi. Pesan akan muncul saat peserta mendapat giliran.</p> : <>
      <label className="swarm-thread-filter">Thread diskusi<select value={selected} onChange={e => setSelected(e.target.value)}><option value="all">Semua thread ({roots.length})</option>{roots.map(root => <option key={root.id} value={root.id}>{people[root.actor_id]?.name ?? "Peserta"}: {excerpt(root.content ?? root.rationale, 70)}</option>)}</select></label>
      {roots.filter(root => selected === "all" || root.id === selected).map(root => <section className="swarm-thread" key={root.id} aria-label={`Thread oleh ${people[root.actor_id]?.name ?? "peserta"}`}>
        <div className="swarm-thread-heading"><h3>{excerpt(root.content ?? root.rationale, 100)}</h3><span>{root.visibility === "public" ? "Publik untuk peserta" : "Privat antarpartisipan"}</span></div>
        {messages.filter(event => event.thread_id === root.id).map(event => <article className="swarm-message" key={event.id} id={`swarm-message-${event.id}`} tabIndex={-1}>
          <div className="swarm-message-heading"><div className="persona-identity"><PersonaAvatar id={event.actor_id} size={36} /><div><strong>{people[event.actor_id]?.name ?? "Peserta"}</strong><span>{roleLabels[people[event.actor_id]?.role] ?? people[event.actor_id]?.role ?? "Peserta"} · ronde {event.round}</span></div></div>{event.stance_update && <span className="swarm-stance-label">{stanceLabel[event.stance_update.after]}</span>}</div>
          {event.reply_to && <button className="business-text-button" type="button" onClick={() => jump(event.reply_to!)}>Membalas {people[byId[event.reply_to]?.actor_id]?.name ?? "pesan sebelumnya"}</button>}
          {event.dialogue_act && <p className="swarm-message-intent">{intentLabel[event.dialogue_act]} · kepada {event.target_id === "all" ? "semua peserta" : people[event.target_id]?.name ?? "peserta"}</p>}
          {!compact && event.dispatch?.trigger_event_id && <button className="business-text-button" type="button" onClick={() => jump(event.dispatch!.trigger_event_id!)}>Giliran dipicu pertanyaan atau sanggahan</button>}
          <div className="swarm-message-content"><BusinessText value={event.content ?? event.rationale} /></div>
          {event.stance_update && <details><summary>Alasan dan pengaruh pada sikap</summary><p>{event.stance_update.reason}</p>{event.stance_update.before !== event.stance_update.after && <p>{stanceLabel[event.stance_update.before]} → {stanceLabel[event.stance_update.after]}</p>}{event.stance_update.influenced_by_event_ids.map(id => <button className="business-text-button" key={id} type="button" onClick={() => jump(id)}>Periksa pesan yang dirujuk: {(byId[id]?.content ?? byId[id]?.rationale ?? id).slice(0, 100)}</button>)}</details>}
        </article>)}
      </section>)}
    </>}
    {!compact && !!Object.keys(positions).length && <section className="swarm-positions"><h3>Posisi sintetis terakhir</h3><p>Alasan dipertahankan agar perbedaan pendapat dapat diperiksa. Ini bukan hasil survei customer.</p>{Object.entries(positions).map(([id, state]) => <article key={id} className="swarm-position"><div className="swarm-message-heading"><strong className="persona-identity"><PersonaAvatar id={id} size={28} />{people[id]?.name ?? "Peserta"}</strong><span className="swarm-stance-label">{stanceLabel[state.stance]}</span></div><p>{state.stance_reason}</p><details><summary>Riwayat perubahan ({state.stance_history.length})</summary>{state.stance_history.length ? state.stance_history.map(change => <div key={change.event_id}><p>Ronde {change.round}: {stanceLabel[change.before]} → {stanceLabel[change.after]} · {change.visibility === "public" ? "publik" : "privat"}</p><p>{change.reason}</p><button className="business-text-button" type="button" onClick={() => jump(change.event_id)}>Periksa interaksi perubahan</button></div>) : <p>Belum ada perubahan posisi yang tercatat.</p>}</details></article>)}</section>}
  </section>;
}
