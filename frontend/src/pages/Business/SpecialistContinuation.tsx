import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { businessKeys, continueBusinessSpecialists } from "../../api/business";
import type { BusinessAnalysis } from "../../api/business";
import { Notice } from "./BusinessPages";
import { errorText, statusLabel } from "./businessFormatting";

export function SpecialistContinuation({ analysis }: { analysis: BusinessAnalysis }) {
  const [key] = useState(() => crypto.randomUUID());
  const navigate = useNavigate();
  const client = useQueryClient();
  const entries = analysis.result.agent_runs ?? [];
  const calls = entries.filter(entry => entry.phase === "specialist" || entry.phase === "inherited_specialist");
  const notStarted = analysis.input_snapshot.config.engine === "oasis" && !!analysis.result.simulation?.events.length && calls.length === 0;
  const failedOnly = calls.length > 0 && ["Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent"].some(role =>
    !calls.some(entry => entry.role === role && entry.status === "completed") || entries.some(entry => entry.role === role && entry.status === "failed"));
  const review = useMutation({
    mutationFn: () => continueBusinessSpecialists(analysis.id, key, failedOnly),
    onSuccess: row => {
      void client.invalidateQueries({ queryKey: businessKeys.analysis(analysis.id) });
      void client.invalidateQueries({ queryKey: businessKeys.project(analysis.project_id) });
      navigate(`/business/analyses/${row.id}`);
    },
  });
  const lineage = analysis.input_snapshot.review_source ? <Notice>
    Review lanjutan dari <Link to={`/business/analyses/${analysis.input_snapshot.review_source.analysis_id}`}>diskusi run asal</Link>.
    {" "}Percakapan, persona dan evidence dipakai kembali. Penggunaan pada run ini hanya mencakup panggilan specialist baru; kelengkapan diskusi mengikuti run asal.
  </Notice> : null;
  if (analysis.review_followup) return <>{lineage}<Notice>
    Review lanjutan sudah dibuat: <Link to={`/business/analyses/${analysis.review_followup.id}`}>Buka review specialist</Link>
    {" "}({statusLabel(analysis.review_followup.status)}).
  </Notice></>;
  if ((analysis.input_snapshot.review_source && !failedOnly) || (!analysis.result.recovery && !failedOnly && !notStarted) || analysis.status !== "partial" || analysis.baseline_id) return lineage;
  return <>{lineage}<section className="business-live" aria-labelledby="specialist-continuation-title">
    <h2 id="specialist-continuation-title">{failedOnly ? "Sebagian specialist belum selesai" : "Review specialist belum berjalan"}</h2>
    <p>{failedOnly ? "Review yang sudah selesai dan lolos validator dipakai kembali. Hanya specialist yang belum selesai dipanggil lagi, dengan biaya provider. Diskusi tetap sama dan hasil disimpan sebagai run terpisah." : "Market, Finance, Legal/Compliance dan Risk dapat memeriksa diskusi yang tersimpan. Ini menjalankan panggilan AI baru dengan biaya provider, tanpa mengulang percakapan. Hasil disimpan sebagai run terpisah."}</p>
    <button className="button secondary" disabled={review.isPending} onClick={() => review.mutate()}>{review.isPending ? "Menyiapkan review…" : failedOnly ? "Lanjutkan specialist yang belum selesai" : "Jalankan empat specialist AI"}</button>
    {review.isError && <Notice error>{errorText(review.error)}</Notice>}
  </section></>;
}
