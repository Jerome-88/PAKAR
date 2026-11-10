import type { BusinessAnalysis } from "../../api/business";

const roles = ["Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent"];

export function SpecialistReviewStatus({ analysis }: { analysis: BusinessAnalysis }) {
  const entries = analysis.result.agent_runs ?? [];
  const calls = entries.filter(entry => entry.phase === "specialist" || entry.phase === "inherited_specialist");
  if (!calls.length) return null;
  const failed = roles.some(role => entries.some(entry => entry.role === role && entry.status === "failed"));
  return <section className="business-specialist-status" aria-labelledby="specialist-review-status-title">
    <h2 id="specialist-review-status-title">Review specialist AI</h2>
    <div className="business-table-wrap"><table className="business-table">
      <caption>Hasil review specialist</caption>
      <thead><tr><th>Specialist</th><th>Status</th><th>Keterangan</th></tr></thead>
      <tbody>{roles.map(role => {
        const call = calls.find(entry => entry.role === role);
        const failure = entries.find(entry => entry.role === role && entry.status === "failed");
        const rateLimited = call?.status_code === 429 || call?.failure_kind === "rate_limit";
        const completed = call?.status === "completed" && !failure;
        const errorType = failure?.error_type ?? call?.error_type;
        let detail = "Tidak ada panggilan AI yang selesai untuk specialist ini.";
        if (completed) detail = "Respons diterima dan diperiksa; temuan tetap perlu validasi.";
        else if (call?.status === "completed" && failure) detail = "Respons AI diterima, tetapi keluarannya ditolak validator; temuan tidak dipakai.";
        else if (rateLimited) detail = "HTTP 429: provider membatasi request (rate limit).";
        else if (call?.status_code) detail = `HTTP ${call.status_code}: permintaan ke provider gagal.`;
        else if (call?.failure_kind === "timeout") detail = "Provider tidak merespons dalam batas waktu.";
        else if (errorType === "BudgetExceeded") detail = "Batas waktu atau token review tercapai; jenis batas tidak dirinci pada catatan ini.";
        else if (errorType === "ValueError" || errorType === "JSONDecodeError") detail = "Respons AI tidak memenuhi kontrak output; temuan tidak dipakai.";
        else if (failure) detail = "Review gagal; rincian penyebab tidak tersedia pada catatan ini.";
        if (completed && call?.phase === "inherited_specialist") detail = "Review selesai pada run asal; hasil dipakai kembali tanpa panggilan AI baru untuk specialist ini.";
        return <tr key={role}><th scope="row">{role}</th><td>{completed ? "Selesai" : failure ? "Belum selesai" : "Belum ada hasil"}</td>
          <td>{detail}</td></tr>;
      })}</tbody>
    </table></div>
    {failed && <p>Review belum lengkap. Tidak ada retry AI otomatis. Periksa batas provider dan keterbatasan laporan sebelum memakai hasil.</p>}
  </section>;
}
