import type { BusinessAnalysis, BusinessEvent } from "../../api/business";
import { PakarMascot } from "../../components/PakarMascot/PakarMascot";
import { BusinessText } from "./BusinessText";
import { discussionFindings, friendlyText } from "./resultSummary";

const specialists = [
  { role: "Finance Agent", label: "Keuangan", mascot: "lumi" },
  { role: "Market Agent", label: "Pasar & strategi", mascot: "peb" },
  { role: "Legal/Compliance Agent", label: "Legal & kepatuhan", mascot: "kubo" },
  { role: "Risk Agent", label: "Risiko", mascot: "noki" },
] as const;

export function SpecialistContributions({ analysis, events }: { analysis: BusinessAnalysis; events: BusinessEvent[] }) {
  const findings = discussionFindings(analysis.result.findings ?? [], events);
  const runs = analysis.result.agent_runs ?? [];
  const demoReviews = (analysis as BusinessAnalysis & { demo?: { specialists: { role: string; status: string }[] } }).demo?.specialists ?? [];
  return <section className="specialist-contributions" aria-labelledby="specialist-contributions-title">
    <div className="specialist-contributions-heading"><h2 id="specialist-contributions-title">Tinjauan spesialis</h2><p>Analisis dari hasil yang sama. Setiap temuan masih perlu divalidasi.</p></div>
    <div className="specialist-contributions-grid">{specialists.map(specialist => {
      const contributions = findings.filter(finding => finding.author === specialist.role);
      const primary = contributions[0];
      const review = [...runs.filter(run => ["specialist", "inherited_specialist"].includes(run.phase ?? "")), ...demoReviews].filter(run => run.role === specialist.role).at(-1);
      return <article className={`specialist-contribution specialist-contribution-${specialist.mascot}`} key={specialist.role}>
        <div className="specialist-contribution-identity"><PakarMascot name={specialist.mascot} /><div><h3>{specialist.label}</h3><p>{specialist.role}</p></div></div>
        <p>{review?.status === "completed" ? "Review selesai" : review?.status === "failed" ? "Review gagal; perlu diperiksa" : review?.status === "running" ? "Review berlangsung" : "Status review belum tersedia"}</p>
        {!primary ? <p>{review?.status === "completed" ? "Tidak ada temuan tambahan dari diskusi. Ini tidak berarti aspek ini bebas risiko." : "Belum ada temuan diskusi yang dapat ditampilkan."}</p> : <>
        <div className="specialist-contribution-analysis"><h4>Analisis terperinci</h4><BusinessText value={friendlyText(primary.reasoning)} /></div>
        <div className="specialist-assessment"><h4>Penilaian</h4><p>{friendlyText(primary.title)}</p></div>
        {primary.next_validation && <div className="specialist-critical-question"><h4>Langkah validasi</h4><BusinessText value={friendlyText(primary.next_validation)} /></div>}
        {contributions.length > 1 && <details><summary>{contributions.length - 1} temuan lain dari spesialis ini</summary>{contributions.slice(1).map(finding => <div className="specialist-additional-finding" key={finding.id}><h4>{friendlyText(finding.title)}</h4><BusinessText value={friendlyText(finding.reasoning)} />{finding.next_validation && <p><strong>Saran validasi:</strong> {friendlyText(finding.next_validation)}</p>}</div>)}</details>}
        </>}
      </article>;
    })}</div>
  </section>;
}
