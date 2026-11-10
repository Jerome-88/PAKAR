import { useRef } from "react";
import { Link } from "react-router-dom";
import type { ChatTurn } from "../../api/business";
import { BusinessText } from "./BusinessText";
import { citationText } from "./citationReferences";

const sourceLabels: Record<string, string> = { synthetic_finding: "Temuan sintetis; perlu validasi", synthetic_stance_summary: "Jumlah sikap persona simulasi; bukan survei", synthetic_persona_position: "Sikap persona sintetis; bukan bukti pasar", synthetic_interaction: "Pesan simulasi; bukan fakta terverifikasi", idea_assumption: "Usulan pengguna", conditional_calculation: "Perhitungan bersyarat dari input" };

export function ConversationAnswer({ turn }: { turn: ChatTurn }) {
  const sources = useRef<HTMLDetailsElement>(null);
  const citations = turn.response?.citations ?? [];
  const prefix = `chat-source-${encodeURIComponent(turn.id)}`;
  const references = new Map(citations.map((c, index) => [`#${prefix}-${index + 1}`, { citation: c, index }]));
  function reveal(index: number) {
    if (sources.current) sources.current.open = true;
    const source = document.getElementById(`${prefix}-${index + 1}`);
    source?.scrollIntoView({ block: "nearest", behavior: "instant" });
    source?.focus({ preventScroll: true });
  }
  return <>
    <BusinessText value={citationText(turn.response?.answer, citations, prefix)} components={{ a: ({ href, children }) => {
      const reference = references.get(href ?? "");
      return reference ? <button type="button" className="chat-citation" aria-label={`Buka sumber ${reference.index + 1}: ${reference.citation.label}`} onClick={() => reveal(reference.index)}>{children}</button> : <a href={href}>{children}</a>;
    } }} />
    {!!turn.response?.questions?.length && <div className="project-chat-questions"><strong>Yang perlu dijelaskan</strong><ul>{turn.response.questions.map((q, i) => <li key={q + i}>{q}</li>)}</ul></div>}
    {!!citations.length && <details ref={sources} className="project-chat-sources"><summary>Sumber yang dirujuk ({citations.length})</summary>{citations.map((c, index) => <blockquote key={c.id} id={`${prefix}-${index + 1}`} tabIndex={-1}><strong className="project-chat-source-title">[{index + 1}] {c.label}</strong><p>{c.text}</p><footer>{sourceLabels[c.kind] ?? "Kutipan dokumen; belum diverifikasi"}{c.locator?.page != null ? ` · halaman ${c.locator.page}` : ""}{c.analysis_id && <><br /><Link to={`/business/analyses/${c.analysis_id}`}>Buka analisis sumber</Link></>}</footer></blockquote>)}</details>}
  </>;
}
