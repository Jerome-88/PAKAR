export const errorText = (error: unknown) => error instanceof Error ? error.message : "Permintaan gagal. Coba lagi.";
const statusLabels: Record<string, string> = { queued: "Dalam antrean", running: "Berjalan", completed: "Selesai", partial: "Selesai sebagian", failed: "Gagal", cancelled: "Dibatalkan" };
export const statusLabel = (status: string) => statusLabels[status] ?? status;
export function projectDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Belum tercatat" : new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta" }).format(date);
}
export function analysisDateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Hasil analisis tersimpan" : `Dibuat ${new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(date)}`;
}
