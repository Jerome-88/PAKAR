import { useEffect, useMemo, useRef, useState } from "react";
import { PersonaAvatar } from "../../components/PersonaAvatar/PersonaAvatar";
import { getAvatarSource } from "../../components/PersonaAvatar/avatar";
import { PakarMascot } from "../../components/PakarMascot/PakarMascot";
import { BusinessText } from "./BusinessText";
import type { DemoAnalysis } from "./demoData";
import { createResultNetwork } from "./resultNetwork";
import { personaPositions, previewText, recordedConnections, responseSummary, roleLabels, stanceLabels } from "./resultSummary";
import "./BusinessProcessReplay.css";

const phases = ["Ide & konteks", "Menyusun persona", "Simulasi debat", "Review spesialis", "Hasil analisis"];
const specialists = [
  { role: "Market Agent", label: "Pasar & strategi", mascot: "peb" },
  { role: "Finance Agent", label: "Keuangan", mascot: "lumi" },
  { role: "Legal/Compliance Agent", label: "Legal & kepatuhan", mascot: "kubo" },
  { role: "Risk Agent", label: "Risiko", mascot: "noki" },
] as const;
type Step = { phase: number; index: number };
function ControlIcon({ kind }: { kind: "play" | "pause" | "back" | "next" | "restart" }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{kind === "play" ? <path d="m8 5 11 7-11 7Z" fill="currentColor" stroke="none" /> : kind === "pause" ? <><path d="M8 5v14M16 5v14" strokeWidth="4" /></> : kind === "restart" ? <><path d="M4 10a8 8 0 1 1 1 8M4 4v6h6" /></> : <path d={kind === "next" ? "m9 5 7 7-7 7" : "m15 5-7 7 7 7"} />}</svg>;
}

export function BusinessProcessReplay({ analysis, onResult }: { analysis: DemoAnalysis; onResult: () => void }) {
  const personas = analysis.input_snapshot.personas;
  const messages = useMemo(() => (analysis.result.simulation?.events ?? []).filter(event => ["post_message", "reply_message"].includes(event.kind)), [analysis]);
  const steps = useMemo<Step[]>(() => [{ phase: 0, index: 0 }, ...personas.map((_, index) => ({ phase: 1, index })), ...messages.map((_, index) => ({ phase: 2, index })), ...specialists.map((_, index) => ({ phase: 3, index })), { phase: 4, index: 0 }], [personas, messages]);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const phaseRail = useRef<HTMLOListElement>(null);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const step = steps[cursor];
  const finished = cursor === steps.length - 1;
  const active = playing && !finished;
  useEffect(() => {
    const align = () => {
      const rail = phaseRail.current;
      const button = rail?.querySelector<HTMLButtonElement>('[aria-current="step"]');
      if (rail && button && rail.scrollWidth > rail.clientWidth) rail.scrollTo({ left: button.offsetLeft - rail.offsetLeft - rail.clientWidth / 2 + button.offsetWidth / 2, behavior: "instant" });
    };
    align(); window.addEventListener("resize", align);
    return () => window.removeEventListener("resize", align);
  }, [step.phase]);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReducedMotion(preference.matches);
    preference.addEventListener("change", change);
    const visibility = () => { if (document.hidden) setPlaying(false); };
    document.addEventListener("visibilitychange", visibility);
    return () => { preference.removeEventListener("change", change); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  useEffect(() => {
    if (!active) return;
    const delay = step.phase === 0 ? 800 : step.phase === 1 ? 750 : step.phase === 2 ? 2400 : 1400;
    const timer = window.setTimeout(() => setCursor(value => Math.min(value + 1, steps.length - 1)), delay / speed);
    return () => window.clearTimeout(timer);
  }, [active, cursor, speed, step.phase, steps.length]);
  const jump = (value: number) => { setPlaying(false); setCursor(Math.max(0, Math.min(value, steps.length - 1))); };
  const messageCount = step.phase < 2 ? 0 : step.phase === 2 ? step.index + 1 : messages.length;
  const visiblePersonas = step.phase === 0 ? 0 : step.phase === 1 ? step.index + 1 : personas.length;
  const visibleMessages = useMemo(() => messages.slice(0, messageCount), [messages, messageCount]);
  const positions = useMemo(() => personaPositions(visibleMessages, personas), [visibleMessages, personas]);
  const people = useMemo(() => responseSummary(messages, personas).people, [messages, personas]);
  const allConnections = useMemo(() => recordedConnections(messages, people), [messages, people]);
  const connections = useMemo(() => recordedConnections(visibleMessages, people), [visibleMessages, people]);
  const network = useMemo(() => createResultNetwork(personas.map(persona => persona.id), allConnections, 720), [personas, allConnections]);
  const graphBounds = useMemo(() => {
    const xs = network.nodes.map(node => node.x), ys = network.nodes.map(node => node.y);
    if (!xs.length) return "0 0 720 540";
    return `${Math.min(...xs) - 75} ${Math.min(...ys) - 50} ${Math.max(...xs) - Math.min(...xs) + 150} ${Math.max(...ys) - Math.min(...ys) + 145}`;
  }, [network]);
  const currentMessage = step.phase === 2 ? messages[step.index] : undefined;
  const focused = step.phase === 1 ? personas[step.index] : personas.find(persona => persona.id === currentMessage?.actor_id);
  const previousMessage = currentMessage?.reply_to ? messages.find(event => event.id === currentMessage.reply_to) : undefined;
  const recipient = personas.find(persona => persona.id === currentMessage?.target_id);
  const senderPosition = focused ? network.byId.get(focused.id) : undefined;
  const recipientPosition = recipient ? network.byId.get(recipient.id) : undefined;
  const motionPath = senderPosition && recipientPosition ? `M ${senderPosition.x} ${senderPosition.y} L ${recipientPosition.x} ${recipientPosition.y}` : undefined;
  const status = step.phase === 2 ? `Ronde ${currentMessage?.round ?? 0} · ${messageCount}/${messages.length} pesan` : step.phase === 1 ? `${visiblePersonas}/${personas.length} persona` : phases[step.phase];
  const brief = analysis.demo?.public_brief || analysis.input_snapshot.context.decision_question;
  const finalSummary = useMemo(() => responseSummary(messages, personas, analysis.result.simulation?.stances), [analysis, messages, personas]);

  return <section className="demo-process" aria-label="Pemutaran proses analisis">
    <header className="demo-process-heading"><div><h2>Dari satu ide, lihat berbagai sudut pandang.</h2><p>Ikuti pembentukan persona, debat, dan peninjauan hasil Pepsodent.</p></div><button type="button" className="business-text-button" onClick={onResult}>Lihat hasil langsung<ControlIcon kind="next" /></button></header>
    <div className="demo-process-recording"><span className="demo-recording-dot" /><p><strong>Replay proses AI tersimpan.</strong> Pemutaran ini tidak memakai kredit baru.</p></div>
    <ol ref={phaseRail} className="demo-process-phases" aria-label="Tahapan proses">{phases.map((phase, index) => <li key={phase} data-state={index < step.phase ? "done" : index === step.phase ? "active" : "waiting"}><button type="button" onClick={() => jump(steps.findIndex(item => item.phase === index))} aria-current={index === step.phase ? "step" : undefined}><span className="demo-phase-dot">{index < step.phase ? <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m3 8 3 3 7-7" /></svg> : index + 1}</span><span>{phase}</span></button></li>)}</ol>
    <div className="demo-process-stage" data-phase={step.phase} data-playing={active}>
      <div className="demo-process-network"><div className="demo-stage-heading"><h3>{step.phase < 2 ? "Sudut pandang mulai terbentuk" : step.phase === 2 ? "Argumen saling bertemu" : step.phase === 3 ? "Temuan ditinjau dari empat bidang" : "Dari percakapan ke langkah berikutnya"}</h3><p role="status" aria-live="polite">{step.phase === 2 ? `Ronde ${currentMessage?.round}` : phases[step.phase]}</p></div>
        <svg className="demo-network-canvas" viewBox={graphBounds} role="img" aria-label={`Graf pemutaran: ${visiblePersonas} persona terlihat dan ${messageCount} pesan diputar`}>
          <g className="demo-recorded-edges">{connections.map(edge => { const from = network.byId.get(edge.source)!, to = network.byId.get(edge.target)!; return <line key={`${edge.source}:${edge.target}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} />; })}</g>
          {motionPath && <path className="demo-active-edge" d={motionPath} />}
          {motionPath && active && !reducedMotion && <circle key={currentMessage?.id} className="demo-message-traveller" r="5"><animateMotion dur={`${1000 / speed}ms`} path={motionPath} repeatCount="1" fill="freeze" /></circle>}
          {personas.map((persona, index) => { const point = network.byId.get(persona.id)!; const shown = index < visiblePersonas; return <g key={persona.id} transform={`translate(${point.x},${point.y})`} className="demo-persona-node" data-revealed={shown} data-focused={shown && focused?.id === persona.id} data-recipient={recipient?.id === persona.id}>
            <circle className="demo-persona-focus" r="34" /><circle className="demo-persona-face" r="26" />
            {shown ? <image href={getAvatarSource(persona)} x="-23" y="-23" width="46" height="46" /> : <text className="demo-persona-placeholder" y="5" textAnchor="middle">{index + 1}</text>}
            <text className="demo-persona-name" y="48" textAnchor="middle">{shown ? persona.role === "customer" ? persona.name : persona.role === "operator" ? "Pengelola" : persona.role === "regulator" ? "Peninjau" : roleLabels[persona.role] ?? persona.name : "Menunggu"}</text>
            {shown && <text className="demo-persona-role" y="65" textAnchor="middle">{positions[persona.id] ? stanceLabels[positions[persona.id].stance] : roleLabels[persona.role] ?? persona.role}</text>}
          </g>; })}
        </svg>
        <div className="demo-process-network-footer"><span>{visiblePersonas} persona · {connections.length} hubungan tercatat</span><span className="demo-speaking-key"><i />{step.phase === 2 ? "Giliran bicara tersimpan" : "Sesuai urutan pemutaran"}</span></div>
      </div>
      <aside className="demo-process-context" aria-label="Konteks tahap pemutaran">
        {step.phase === 0 && <div className="demo-context-enter"><PakarMascot name="moki" /><h3>Mulai dari ide Pepsodent</h3><p className="demo-case-question">{analysis.input_snapshot.context.decision_question}</p><dl className="demo-case-facts"><div><dt>Persona</dt><dd>{personas.length} perspektif sintetis</dd></div><div><dt>Diskusi tersimpan</dt><dd>{messages.length} pesan · {analysis.input_snapshot.config.rounds} ronde</dd></div></dl><details><summary>Baca brief yang dibagikan</summary><BusinessText value={brief} /></details><p>Angka harga dan biaya merupakan asumsi ilustratif dalam kasus ini.</p><button type="button" className="button primary" onClick={() => setPlaying(true)}>Mulai demo<ControlIcon kind="play" /></button></div>}
        {step.phase === 1 && focused && <div className="demo-context-enter" key={focused.id}><span className="demo-context-step">Persona {step.index + 1} dari {personas.length}</span><PersonaAvatar id={focused.id} size={64} /><h3>{focused.name}</h3><p className="demo-persona-role-label">{roleLabels[focused.role] ?? focused.role}</p><h4>Prioritas perspektif</h4><BusinessText value={focused.goals[0] || "Meninjau konsep dari kepentingan perannya."} />{focused.interests.length > 0 && <p className="demo-persona-interest">{focused.interests.join(" · ")}</p>}<p className="demo-context-footnote">Profil hipotetis dari run tersimpan; bukan responden nyata.</p></div>}
        {step.phase === 2 && currentMessage && focused && <div className="demo-context-enter" key={currentMessage.id}><div className="demo-message-meta"><span>Ronde {currentMessage.round}</span><span>Pesan {messageCount}/{messages.length}</span></div><div className="demo-current-speaker"><PersonaAvatar id={focused.id} size={48} /><div><h3>{focused.name}</h3><p>{roleLabels[focused.role] ?? focused.role}{recipient ? ` · kepada ${recipient.name}` : ""}</p></div></div>{previousMessage && <blockquote className="demo-reply-context"><span>Menanggapi {personas.find(persona => persona.id === previousMessage.actor_id)?.name ?? "peserta"}</span><p>{previewText(previousMessage.content, 140)}</p></blockquote>}<article className="demo-current-message"><BusinessText value={currentMessage.content ?? currentMessage.rationale} /></article>{currentMessage.stance_update && <p className="demo-current-stance" data-stance={currentMessage.stance_update.after}>{stanceLabels[currentMessage.stance_update.after]}</p>}<p className="demo-context-footnote">Jeda pemutaran untuk membaca, atau gunakan tombol langkah berikutnya.</p></div>}
        {step.phase === 3 && <div className="demo-context-enter"><h3>Review spesialis</h3><p>Memutar tahap peninjauan yang tercatat pada analisis ini.</p><ul className="demo-specialist-list">{specialists.map((specialist, index) => { const review = analysis.demo?.specialists.find(item => item.role === specialist.role); const revealed = index <= step.index; const findings = analysis.result.findings?.filter(finding => finding.author === specialist.role) ?? []; return <li key={specialist.role} data-revealed={revealed} data-active={index === step.index}><PakarMascot name={specialist.mascot} /><div><h4>{specialist.label}</h4><p>{revealed ? review?.status === "completed" ? `Review selesai · ${findings.length} temuan tersimpan` : "Review belum lengkap pada run ini" : "Menunggu pemutaran"}</p></div></li>; })}</ul></div>}
        {step.phase === 4 && <div className="demo-context-enter"><PakarMascot name="lumi" /><h3>Pemutaran selesai.</h3><p>{analysis.status === "completed" ? "Semua ronde pada run ini selesai. Temuannya siap ditinjau sebagai hipotesis." : "Run ini berstatus parsial. Periksa batas hasil sebelum menggunakannya."}</p><dl className="demo-final-positions"><div><dt>Bersyarat</dt><dd>{finalSummary.counts.conditional}</dd></div><div><dt>Menolak</dt><dd>{finalSummary.counts.oppose}</dd></div><div><dt>Mendukung</dt><dd>{finalSummary.counts.support}</dd></div></dl><p>{analysis.result.findings?.length ?? 0} temuan tersimpan. Buka hasil untuk memeriksa blind spot, sumber, dan langkah validasi.</p><button type="button" className="button primary" onClick={onResult}>Buka hasil analisis<ControlIcon kind="next" /></button><p className="demo-context-footnote">Pendapat persona dan angka ilustratif bukan bukti pasar.</p></div>}
      </aside>
    </div>
    <div className="demo-process-player"><div className="demo-player-buttons"><button type="button" className="demo-player-main" aria-label={finished ? "Putar ulang demo" : active ? "Jeda pemutaran" : "Putar demo"} onClick={() => { if (finished) setCursor(0); setPlaying(finished || !playing); }}><ControlIcon kind={active ? "pause" : "play"} /><span>{finished ? "Putar ulang" : active ? "Jeda" : "Putar"}</span></button><button type="button" aria-label="Langkah sebelumnya" disabled={cursor === 0} onClick={() => jump(cursor - 1)}><ControlIcon kind="back" /></button><button type="button" aria-label="Langkah berikutnya" disabled={finished} onClick={() => jump(cursor + 1)}><ControlIcon kind="next" /></button><button type="button" aria-label="Kembali ke awal demo" onClick={() => jump(0)}><ControlIcon kind="restart" /></button></div><label className="demo-player-position"><span>{status}</span><input type="range" min="0" max={steps.length - 1} value={cursor} onChange={event => jump(Number(event.target.value))} aria-label="Posisi pemutaran" aria-valuetext={`${phases[step.phase]}, langkah ${cursor + 1} dari ${steps.length}`} /></label><label className="demo-player-speed"><span>Kecepatan</span><select aria-label="Kecepatan pemutaran" value={speed} onChange={event => setSpeed(Number(event.target.value))}>{[1, 2, 4].map(value => <option key={value} value={value}>{value}×</option>)}</select></label></div>
  </section>;
}
