import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { BusinessClaim, BusinessEvent, BusinessFinding } from "../../api/business";
import { PersonaAvatar } from "../../components/PersonaAvatar/PersonaAvatar";
import { getAvatarSource } from "../../components/PersonaAvatar/avatar";
import { BusinessText } from "./BusinessText";
import { BusinessResultIcon } from "./BusinessResultIcon";
import { friendlyText, previewText, recordedConnections, roleLabels, stanceLabels, type responseSummary } from "./resultSummary";
import { select } from "d3-selection";
import { drag } from "d3-drag";
import { zoom, zoomIdentity, type ZoomBehavior } from "d3-zoom";
import { createResultNetwork, type ResultNetworkNode } from "./resultNetwork";

type Person = ReturnType<typeof responseSummary>["people"][number];

export function BusinessResultGraph({ people, events, claims = [], findings = [], showDiscussion, summaryId }: { people: Person[]; events: BusinessEvent[]; claims?: BusinessClaim[]; findings?: BusinessFinding[]; showDiscussion: () => void; summaryId?: string }) {
  const [selected, setSelected] = useState(people[0]?.persona.id ?? "");
  const [width, setWidth] = useState(640);
  const stageRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const sceneRef = useRef<SVGGElement>(null);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const transformRef = useRef(zoomIdentity);
  const fitRef = useRef<() => void>(() => {});
  const resetRef = useRef<() => void>(() => {});
  const [zoomPercent, setZoomPercent] = useState(100);
  const focused = people.find(p => p.persona.id === selected) ?? people[0];
  const selectedId = focused?.persona.id;
  const hasPeople = people.length > 0;
  useLayoutEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const measure = () => { if (stage.clientWidth) setWidth(stage.clientWidth); };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(stage);
    return () => observer.disconnect();
  }, [hasPeople]);
  const connections = useMemo(() => recordedConnections(events, people), [events, people]);
  const network = useMemo(() => createResultNetwork(people.map(person => person.persona.id), connections, width), [people, connections, width]);
  const related = connections.filter(edge => edge.source === selectedId || edge.target === selectedId);
  const contributions = events.filter(event => event.actor_id === selectedId && !["action_rejected", "shock", "shock_expired", "abstain"].includes(event.kind));
  const contributionIds = new Set(contributions.map(event => event.id));
  const claimIds = new Set(findings.filter(finding => finding.persona_ids.includes(selectedId ?? "") || finding.event_ids.some(id => contributionIds.has(id))).flatMap(finding => finding.claim_ids));
  const referencedClaims = claims.filter(claim => claimIds.has(claim.id));
  useLayoutEffect(() => {
    const svg = svgRef.current, scene = sceneRef.current;
    if (!svg || !scene || !network.nodes.length) return;
    const surface = select(svg);
    const behavior = zoom<SVGSVGElement, unknown>().extent([[0, 0], [width, 480]]).scaleExtent([.2, 3]).filter(event => event.type === "wheel" || (!event.button && !event.target.closest?.(".result-graph-node"))).on("zoom", event => { transformRef.current = event.transform; select(scene).attr("transform", event.transform.toString()); }).on("end", event => setZoomPercent(Math.round(event.transform.k * 100)));
    zoomRef.current = behavior;
    surface.call(behavior);
    const redraw = () => {
      select(scene).selectAll<SVGGElement, ResultNetworkNode>(".result-graph-node").attr("transform", node => `translate(${node.x},${node.y})`);
      select(scene).selectAll<SVGLineElement, unknown>("line").each(function () { const source = network.byId.get(this.dataset.source!)!, target = network.byId.get(this.dataset.target!)!; select(this).attr("x1", source.x).attr("y1", source.y).attr("x2", target.x).attr("y2", target.y); });
    };
    const fit = () => {
      const xs = network.nodes.map(node => node.x), ys = network.nodes.map(node => node.y);
      const left = Math.min(...xs) - 90, right = Math.max(...xs) + 90, top = Math.min(...ys) - 50, bottom = Math.max(...ys) + 85;
      const scale = Math.min(1.2, (width - 24) / (right - left), 450 / (bottom - top));
      surface.call(behavior.transform, zoomIdentity.translate(width / 2, 240).scale(scale).translate(-(left + right) / 2, -(top + bottom) / 2));
    };
    fitRef.current = fit;
    resetRef.current = () => { network.nodes.forEach(node => Object.assign(node, network.initial.get(node.id))); redraw(); fit(); };
    select(scene).selectAll<SVGGElement, ResultNetworkNode>(".result-graph-node").datum(function () { return network.byId.get(this.dataset.personaId!)!; }).call(drag<SVGGElement, ResultNetworkNode>().container(() => scene).clickDistance(4).on("start", (event, node) => { event.sourceEvent.stopPropagation(); setSelected(node.id); }).on("drag", (event, node) => { node.x = event.x; node.y = event.y; redraw(); }));
    if (network.nodes.length <= 20) fit();
    else { const node = network.nodes[0]; surface.call(behavior.transform, zoomIdentity.translate(width / 2 - node.x, 200 - node.y)); }
    return () => { surface.on(".zoom", null); select(scene).selectAll(".result-graph-node").on(".drag", null); };
  }, [network, width]);
  useLayoutEffect(() => {
    const node = selectedId ? network.byId.get(selectedId) : undefined, svg = svgRef.current, behavior = zoomRef.current;
    if (!node || !svg || !behavior) return;
    const point = transformRef.current.apply([node.x, node.y]);
    if (point[0] < 60 || point[0] > width - 60 || point[1] < 50 || point[1] > 380) select(svg).call(behavior.transform, zoomIdentity.translate(width / 2, 200).scale(transformRef.current.k).translate(-node.x, -node.y));
  }, [selectedId, network, width]);
  const scaleBy = (factor: number) => { if (svgRef.current && zoomRef.current) select(svgRef.current).call(zoomRef.current.scaleBy, factor); };

  return <section className="result-graph" aria-label="Peta hasil persona">
    <div className="result-graph-main">
    <div className="result-graph-heading"><div><h2>Peta pendapat persona</h2><p>Pilih persona untuk melihat alasan. Garis menunjukkan interaksi yang tercatat.</p></div>{summaryId && <a className="result-summary-link" href={`#${summaryId}`}>Lihat Executive Summary</a>}</div>
    {!people.length ? <p className="result-graph-empty" role="status">Belum ada persona dengan sikap ini.</p> : <div className="result-network-panel"><div className="result-network-controls"><span>Geser node atau kanvas · gulir untuk zoom</span><div><button type="button" aria-label="Perkecil graf" onClick={() => scaleBy(.8)}><BusinessResultIcon name="zoomOut" /></button><output aria-label="Zoom graf">{zoomPercent}%</output><button type="button" aria-label="Perbesar graf" onClick={() => scaleBy(1.25)}><BusinessResultIcon name="zoomIn" /></button><button type="button" onClick={() => fitRef.current()}>Sesuaikan</button><button type="button" aria-label="Atur ulang graf" onClick={() => resetRef.current()}><BusinessResultIcon name="reset" /></button></div></div>
      <div ref={stageRef} className="result-graph-stage" role="region" aria-label="Graf pendapat persona, dapat digeser dan diperbesar" tabIndex={0} onKeyDown={event => { if (!svgRef.current || !zoomRef.current) return; const movement: Record<string, [number, number]> = { ArrowLeft: [40, 0], ArrowRight: [-40, 0], ArrowUp: [0, 40], ArrowDown: [0, -40] }; if (movement[event.key]) { event.preventDefault(); const [x, y] = movement[event.key]; select(svgRef.current).call(zoomRef.current.translateBy, x / transformRef.current.k, y / transformRef.current.k); } else if (event.key === "Home") { event.preventDefault(); fitRef.current(); } }}>
        <svg ref={svgRef} viewBox={`0 0 ${width} 480`} style={{ height: 480 }} role="group" aria-label="Graf hasil interaktif">
          <g ref={sceneRef} className="result-network-scene"><g aria-hidden="true">{connections.map(edge => {
            const source = network.byId.get(edge.source)!;
            const target = network.byId.get(edge.target)!;
            return <line key={JSON.stringify([edge.source, edge.target])} data-source={edge.source} data-target={edge.target} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className={edge.source === selectedId || edge.target === selectedId ? "selected" : ""} />;
          })}</g>
          {people.map(({ persona, stance }) => { const node = network.byId.get(persona.id)!; return <g key={persona.id} transform={`translate(${node.x},${node.y})`} className="result-graph-node" data-persona-id={persona.id} data-stance={stance} role="button" tabIndex={0} aria-label={`Lihat alasan ${persona.name}: ${stanceLabels[stance]}`} aria-pressed={selectedId === persona.id} onClick={() => setSelected(persona.id)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelected(persona.id); } }}>
            <title>{persona.name} · {roleLabels[persona.role] ?? persona.role} · {stanceLabels[stance]}</title>
            <circle className="result-node-selection" r={28} />
            <circle className="result-node-avatar" r={24} />
            <image href={getAvatarSource(persona)} x={-21} y={-21} width={42} height={42} aria-hidden="true" pointerEvents="none" />
            <circle className="result-node-stance" cx={22} cy={-20} r={5} />
            <text y={47} textAnchor="middle">{persona.name.length > 23 ? `${persona.name.slice(0, 22)}…` : persona.name}</text>
            <text className="result-node-role" y={65} textAnchor="middle">{roleLabels[persona.role] ?? persona.role}</text>
          </g>; })}</g>
        </svg>
      </div></div>}
    </div>
      {focused && <aside className="result-graph-detail" aria-label="Alasan persona terpilih">
        <h3 className="result-context-heading">Konteks &amp; kontribusi</h3>
        <div className="persona-identity"><PersonaAvatar id={focused.persona.id} size={48} /><div><h4>{focused.persona.name}</h4><span>{roleLabels[focused.persona.role] ?? focused.persona.role}</span></div></div>
        <p className="result-person-stance" data-stance={focused.stance}>{stanceLabels[focused.stance]}</p>
        <h4>Alasannya</h4>
        <p>{focused.reason ? previewText(focused.reason) : focused.stance === "unrecorded" ? "Persona ini belum memiliki sikap yang tercatat. Sikapnya tidak dihitung sebagai penolakan." : "Alasan untuk sikap ini belum tercatat."}</p>
        {friendlyText(focused.reason).length > 230 && <details><summary>Baca alasan lengkap</summary><BusinessText value={friendlyText(focused.reason)} /></details>}
        <p className="result-connection-note">{related.length ? `Berinteraksi dengan ${related.length} persona dalam diskusi tersimpan.` : "Belum ada interaksi langsung dengan persona lain dalam tampilan ini."}</p>
        {!!referencedClaims.length && <section className="result-source-context" aria-label="Asumsi yang dirujuk"><h4>Asumsi dari dokumen</h4>{referencedClaims.slice(0, 2).map(claim => <details key={claim.id}><summary><span className="result-context-tag">Asumsi proposal</span>{previewText(claim.quote, 150)}</summary><BusinessText value={claim.quote} /><small>{claim.source.document_id}{claim.source.locator.page != null ? ` · Halaman ${claim.source.locator.page}` : claim.source.locator.paragraph != null ? ` · Paragraf ${claim.source.locator.paragraph}` : ""}</small></details>)}</section>}
        {!!contributions.length && <section className="result-source-context" aria-label="Kontribusi tercatat"><h4>Jejak diskusi</h4>{contributions.slice(-2).map(event => <blockquote key={event.id}><span className="result-context-tag">Pesan simulasi</span><p>{previewText(event.content ?? event.rationale, 170)}</p><footer>Ronde {event.round}</footer></blockquote>)}</section>}
        <label>Lihat persona<select value={selectedId} onChange={e => setSelected(e.target.value)}>{people.map(({ persona }) => <option key={persona.id} value={persona.id}>{persona.name}</option>)}</select></label>
        <button type="button" className="business-text-button result-context-open" onClick={showDiscussion}>Baca seluruh diskusi ({events.filter(event => ["post_message", "reply_message"].includes(event.kind)).length} pesan)<img src={`${import.meta.env.BASE_URL}figma/pakar/arrow.svg`} alt="" /></button>
      </aside>}
  </section>;
}
