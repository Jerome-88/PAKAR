import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { BusinessAnalysis } from "../../api/business";
import { PersonaAvatar } from "../../components/PersonaAvatar/PersonaAvatar";
import { getAvatarSource } from "../../components/PersonaAvatar/avatar";

export function BusinessGraph({ analysis, openEvent }: { analysis: BusinessAnalysis; openEvent: (id: string) => void }) {
  const personas = analysis.input_snapshot.personas;
  const [selected, setSelected] = useState(personas[0]?.id ?? "");
  const stageRef = useRef<HTMLDivElement>(null);
  const lastViewportFocus = useRef("");
  // Retain the existing circular layout; give dense graphs a scrollable canvas
  // rather than shrinking hundreds of portraits and labels to unreadable dots.
  const radius = Math.max(290, personas.length * 140 / (2 * Math.PI));
  const width = Math.max(860, radius * 2 + 280);
  const height = Math.max(550, radius * 1.45 + 130);
  const nodes = useMemo(() => personas.map((p, index) => {
    const angle = index * Math.PI * 2 / personas.length - Math.PI / 2;
    return { ...p, avatar: getAvatarSource(p), x: width / 2 + Math.cos(angle) * radius, y: height / 2 - 5 + Math.sin(angle) * radius * (210 / 290) };
  }), [personas, width, height, radius]);
  useLayoutEffect(() => {
    const stage = stageRef.current;
    const node = nodes.find(item => item.id === selected);
    const focusKey = JSON.stringify([selected, width, height]);
    if (!stage || !node || width <= 860 || lastViewportFocus.current === focusKey) return;
    stage.scrollTo({ left: Math.max(0, node.x - (stage.clientWidth || 860) / 2), top: Math.max(0, node.y - (stage.clientHeight || 480) / 2), behavior: "auto" });
    // Polling may return a new snapshot with the same IDs. Keep manual panning
    // until selection or canvas dimensions actually change.
    lastViewportFocus.current = focusKey;
  }, [nodes, selected, width, height]);
  const positions = Object.fromEntries(nodes.map(node => [node.id, node]));
  const edges = analysis.result.simulation?.relationships ?? personas.flatMap(p => p.relationships.map(target => ({ source: p.id, target, status: "proposed_context", event_ids: [] })));
  const focused = personas.find(p => p.id === selected);
  const related = edges.filter(edge => edge.source === selected || edge.target === selected);
  return <section className="business-graph"><h2>Peta interaksi stakeholder</h2><a className="result-summary-link" href="#executive-summary">Lihat Executive Summary</a><p>Pilih persona untuk memeriksa relasi dan event yang mendasarinya. Garis menunjukkan hubungan dalam konteks atau run sintetis.</p><label className="business-graph-selector">Stakeholder yang diperiksa<select value={selected} onChange={e => setSelected(e.target.value)}>{personas.map(p => <option key={p.id} value={p.id}>{p.name} · {p.role}</option>)}</select></label><div ref={stageRef} className={`business-graph-stage${width > 860 ? " dense" : ""}`} role="region" aria-label="Kanvas stakeholder, dapat digeser" tabIndex={0}><svg viewBox={`0 0 ${width} ${height}`} style={{ minWidth: width > 860 ? width : undefined, height: width > 860 ? height : undefined }} role="group" aria-label="Graf stakeholder interaktif">
    <g aria-hidden="true">{edges.filter(e => positions[e.source] && positions[e.target]).map(edge => <line key={`${edge.source}-${edge.target}`} x1={positions[edge.source].x} y1={positions[edge.source].y} x2={positions[edge.target].x} y2={positions[edge.target].y} stroke={edge.source === selected || edge.target === selected ? "var(--blue)" : "var(--line)"} strokeWidth={edge.source === selected || edge.target === selected ? 2 : 1} />)}</g>
    {nodes.map(node => <g key={node.id} role="button" aria-label={`Periksa persona ${node.name}`} aria-pressed={selected === node.id} tabIndex={0} onClick={() => setSelected(node.id)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(node.id); } }} className="business-graph-node"><title>{node.name} · {node.role}</title><circle cx={node.x} cy={node.y} r={23} fill="#fff" stroke={selected === node.id ? "var(--blue)" : "var(--line)"} strokeWidth={selected === node.id ? 3 : 1} /><image href={node.avatar} x={node.x - 20} y={node.y - 20} width={40} height={40} aria-hidden="true" pointerEvents="none" /><text x={node.x} y={node.y + 42} textAnchor="middle" fill="var(--ink)" fontSize={13}>{node.name.length > 18 ? `${node.name.slice(0, 17)}…` : node.name}</text><text x={node.x} y={node.y + 60} textAnchor="middle" fill="var(--muted)" fontSize={12}>{node.role}</text></g>)}
  </svg></div>{focused && <div className="business-graph-detail"><h3 className="persona-identity"><PersonaAvatar id={focused.id} size={40} /><span>{focused.name}</span></h3><p>{focused.goals.join("; ")}</p><p>{focused.stakeholder_type === "hidden" ? "Kandidat stakeholder terlewat" : focused.stakeholder_type} · Relasi dan respons masih hipotesis.</p><details><summary>Provenance profil stakeholder</summary><pre>{JSON.stringify(focused.provenance, null, 2)}</pre></details><ul>{related.map(edge => <li key={`${edge.source}-${edge.target}`}>{positions[edge.source]?.name ?? edge.source} → {positions[edge.target]?.name ?? edge.target}: <strong>{edge.status.replaceAll("_", " ")}</strong>{edge.event_ids.length ? <details><summary>Periksa {edge.event_ids.length} event penyebab</summary><div className="business-event-links">{edge.event_ids.map(id => <button key={id} className="business-text-button" onClick={() => openEvent(id)}>Buka event {id.split(":").at(-1)}</button>)}</div></details> : <p>Relasi konteks yang diusulkan, belum memiliki event interaksi.</p>}</li>)}</ul></div>}</section>;
}
