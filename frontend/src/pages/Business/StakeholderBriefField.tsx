import { useId } from "react";
import "./StakeholderBriefField.css";

export function StakeholderBriefField({ value, onChange, disabled = false }: { value: string; onChange: (value: string) => void; disabled?: boolean }) {
  const id = useId();
  return <label className="business-field-wide business-stakeholder-brief" htmlFor={id}><span id={`${id}-label`}>Brief untuk stakeholder</span>
    <textarea id={id} rows={4} minLength={20} maxLength={4000} value={value} disabled={disabled} onChange={e => onChange(e.target.value)} aria-labelledby={`${id}-label`} aria-describedby={`${id}-hint`} placeholder="Tulis konsep produk, cara pakai, klaim dan harga yang boleh diketahui calon customer atau stakeholder lain." />
    <small id={`${id}-hint`}>Hanya isi ini yang dibagikan ke persona stakeholder. Dokumen riset, ide lengkap, biaya dan strategi tetap untuk agent internal. Minimal 20 karakter; tersimpan bersama run saat analisis dimulai.</small>
  </label>;
}
