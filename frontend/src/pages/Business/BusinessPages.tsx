import { useBusinessLaunch, definitiveLaunchRejection } from "./useBusinessLaunch";
import { ApiError } from "../../api/client";
import { StakeholderBriefField } from "./StakeholderBriefField";
import { PersonaAvatar } from "../../components/PersonaAvatar/PersonaAvatar";
import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AppShell } from "../../components/AppShell/AppShell";
import { addBusinessPersona, approveBusinessClaims, businessKeys, createBusinessProject, discoverBusinessStakeholders, excludeBusinessDocument, getBusinessCapabilities, getBusinessProject, patchBusinessClaim, patchBusinessPersona, startQuickBusinessAnalysis, uploadBusinessDocuments } from "../../api/business";
import type { BusinessClaim, BusinessContext, BusinessPersona, BusinessProject } from "../../api/business";
import "./Business.css";
import { errorText } from "./businessFormatting";
import businessExamples from "./businessExamples.json";
import { ProjectConversation } from "./ProjectConversation";
import type { BusinessAnalysis } from "../../api/business";
import { publicDemoOnly } from "../../config/publicDemo";

export function Notice({ children, error = false }: { children: React.ReactNode; error?: boolean }) {
  return <p className={`business-notice${error ? " is-error" : ""}`} role={error ? "alert" : "status"}>{children}</p>;
}

const exampleContext: BusinessContext = { ...businessExamples[0].context, data_classification: "synthetic" };

export function BusinessIntakePage({ savedDemo }: { savedDemo?: { analysis: BusinessAnalysis; publicBrief: string; onStart: () => void; onWorkspace: () => void } } = {}) {
  const [params] = useSearchParams();
  const initialExample = !!savedDemo || params.get("example") === "1";
  const [example, setExample] = useState(initialExample);
  const [exampleId, setExampleId] = useState(businessExamples[0].id);
  const [exampleSource, setExampleSource] = useState(businessExamples[0].proposal);
  const [context, setContext] = useState<BusinessContext>(savedDemo ? { ...savedDemo.analysis.input_snapshot.context, decision_question: savedDemo.analysis.input_snapshot.idea?.text ?? savedDemo.analysis.input_snapshot.context.decision_question } : initialExample ? exampleContext : { name: "", industry: "", region: "", target_customer: "", decision_question: "", data_classification: "non_confidential" });
  const [files, setFiles] = useState<File[]>([]);
  const [engine, setEngine] = useState<"fixture" | "oasis">("oasis");
  const [rounds, setRounds] = useState(savedDemo?.analysis.input_snapshot.config.rounds ?? 3);
  const [publicBrief, setPublicBrief] = useState("");
  const [demoDocumentSelected, setDemoDocumentSelected] = useState(false);
  const demoDocument = savedDemo?.analysis.input_snapshot.documents?.[0];
  const demoDocumentText = savedDemo?.analysis.input_snapshot.claims.filter(claim => !demoDocument || claim.source.document_id === demoDocument.id).map(claim => claim.quote).join("\n\n") ?? "";
  const [briefError, setBriefError] = useState("");
  const [interactionMode, setInteractionMode] = useState<"pairwise" | "swarm">("swarm");
  const [customerCount, setCustomerCount] = useState(savedDemo?.analysis.input_snapshot.config.customer_count ?? 4);
  const [phase, setPhase] = useState("");
  const [fileError, setFileError] = useState("");
  const [savedProject, setSavedProject] = useState("");
  const key = useRef(crypto.randomUUID());
  const [requestFrozen, setRequestFrozen] = useState(false);
  const [submittedIntent, setSubmittedIntent] = useState<"analysis" | "workspace">("analysis");
  const submission = useRef<{ key: string; project?: BusinessProject; uploaded: boolean; analysisKey: string; analysisStarted: boolean; intent: "analysis" | "workspace"; draft: { context: BusinessContext; files: File[]; engine: "oasis" | "fixture"; rounds: number; interactionMode: "swarm" | "pairwise"; customerCount: number; publicBrief: string } } | null>(null);
  const intent = useRef<"analysis" | "workspace">("analysis");
  const navigate = useNavigate();
  const capabilities = useQuery({ queryKey: ["business", "capabilities"], queryFn: getBusinessCapabilities, enabled: !savedDemo });
  const limit = capabilities.data?.max_file_bytes ?? 20 * 1024 * 1024;
  const reset = () => { key.current = crypto.randomUUID(); submission.current = null; setSavedProject(""); };
  const create = useMutation({ mutationFn: async () => {
    if (!submission.current || submission.current.key !== key.current) submission.current = { key: key.current, uploaded: false, analysisKey: crypto.randomUUID(), analysisStarted: false, intent: intent.current, draft: {
      context: { ...context, industry: context.industry.trim() || "Belum ditentukan", region: context.region.trim() || "Belum ditentukan", target_customer: context.target_customer.trim() || "Belum ditentukan" },
      files: example ? [new File([exampleSource], `contoh-${exampleId}.txt`, { type: "text/plain" })] : [...files], engine, rounds, interactionMode, customerCount, publicBrief,
    } };
    setRequestFrozen(true); setSubmittedIntent(submission.current.intent);
    const state = submission.current;
    if (!state.project) {
      setPhase("Menyimpan konteks...");
      state.project = await createBusinessProject(state.draft.context, state.key);
      setSavedProject(state.project.id);
    }
    if (!state.uploaded) {
      setPhase("Membaca dokumen...");
      state.project = await uploadBusinessDocuments(state.project.id, state.draft.files);
      state.uploaded = true;
    }
    if (state.intent === "workspace") return { id: state.project.id, workspace: true };
    setPhase("Menyiapkan analisis otomatis...");
    state.analysisStarted = true;
    const run = await startQuickBusinessAnalysis(state.project.id, state.project.revision, state.draft.engine, state.draft.rounds, state.analysisKey, { interaction_mode: state.draft.interactionMode, customer_count: state.draft.customerCount, public_brief: state.draft.publicBrief });
    return { id: run.id, workspace: false };
  }, onSuccess: result => navigate(result.workspace ? `/business/projects/${result.id}?tab=chat` : `/business/analyses/${result.id}`), onError: error => {
    const rejectedBeforeAnalysis = !submission.current?.analysisStarted && error instanceof ApiError && error.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);
    if (definitiveLaunchRejection(error) || rejectedBeforeAnalysis) { setRequestFrozen(false); if (submission.current) submission.current.analysisKey = crypto.randomUUID(); }
  }, onSettled: () => setPhase("") });
  const intakeLocked = !!savedDemo || create.isPending || (create.isError && requestFrozen);
  const change = (name: keyof BusinessContext, value: string) => { reset(); setContext(current => ({ ...current, [name]: value })); };
  const selectExample = (id: string) => {
    const selected = businessExamples.find(item => item.id === id) ?? businessExamples[0];
    reset(); setPublicBrief(""); setBriefError(""); setExampleId(selected.id); setExampleSource(selected.proposal);
    setContext({ ...selected.context, data_classification: "synthetic" }); setFileError("");
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (savedDemo) {
      if (!demoDocumentSelected) { setFileError("Pilih dokumen contoh Pepsodent terlebih dahulu."); return; }
      if (publicBrief.trim().length < 20) { setBriefError("Isi brief contoh sebelum memulai simulasi demo."); return; }
      if (intent.current === "workspace") savedDemo.onWorkspace(); else savedDemo.onStart();
      return;
    }
    if (!example && files.length === 0) { setFileError("Pilih minimal satu dokumen bisnis."); return; }
    if (intent.current === "analysis" && publicBrief.trim().length < 20) { setBriefError("Isi brief untuk stakeholder minimal 20 karakter sebelum analisis. Anda tetap dapat membuka ruang ide dahulu."); return; }
    create.mutate();
  };
  return <AppShell title={savedDemo ? "Siapkan demo Pepsodent" : "Analisis bisnis baru"} subtitle={savedDemo ? "Pilih dokumen dan isi brief contoh, lalu ikuti proses simulasinya." : "Unggah dokumen, jelaskan yang ingin diperiksa, lalu mulai. Persona disiapkan otomatis."} actions={<Link to={publicDemoOnly ? "/" : "/business"} className="button secondary">Kembali ke awal</Link>}>
    <form className="business-workspace business-intake" onSubmit={submit}>
      {savedDemo && <Notice>Demo ini memakai dokumen dan brief contoh Pepsodent dengan hasil yang sudah tersimpan. Pilih input contohnya dahulu; simulasi tidak memakai kredit AI.</Notice>}
      <section><h2>Dokumen bisnis</h2>
        {savedDemo ? <div className="business-upload"><p><strong>{demoDocument?.name ?? "Dokumen contoh Pepsodent"}</strong></p><p>Studi kasus sintetis yang menjadi sumber hasil demo ini.</p>{demoDocumentText && <details><summary>Lihat kutipan dokumen contoh</summary><p style={{ whiteSpace: "pre-wrap" }}>{demoDocumentText}</p><a className="business-text-button" href={`data:text/plain;charset=utf-8,${encodeURIComponent(demoDocumentText)}`} download="kutipan-contoh-pepsodent.txt">Unduh kutipan contoh (.txt)</a></details>}<button type="button" className="button secondary" disabled={demoDocumentSelected} onClick={() => { setDemoDocumentSelected(true); setFileError(""); }}>{demoDocumentSelected ? "Dokumen contoh dipilih" : "Gunakan dokumen contoh"}</button></div> : <>
        <label className="business-check"><input type="checkbox" checked={example} disabled={intakeLocked} onChange={e => { setExample(e.target.checked); reset(); setFileError(""); if (e.target.checked) selectExample(exampleId); else setEngine("oasis"); }} />Gunakan contoh proposal sintetis</label>
        {example ? <>
          <label className="business-classification">Pilih contoh bisnis<select value={exampleId} disabled={intakeLocked} onChange={e => selectExample(e.target.value)}>{businessExamples.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
          <label>Isi proposal contoh<textarea required minLength={20} maxLength={20000} rows={7} value={exampleSource} disabled={intakeLocked} onChange={e => { reset(); setExampleSource(e.target.value); }} /><small>Ubah isi atau angka untuk melihat pengaruhnya pada hasil. Semua contoh bersifat sintetis.</small></label>
          <a className="business-text-button" href={`data:text/plain;charset=utf-8,${encodeURIComponent(exampleSource)}`} download={`contoh-${exampleId}.txt`}>Unduh proposal contoh (.txt)</a>
        </> : <label className="business-upload">Pilih dokumen bisnis<input type="file" accept=".pdf,.docx,.txt,.md" multiple disabled={intakeLocked} onChange={e => {
          const selected = Array.from(e.target.files ?? []);
          const invalid = selected.length > 20 || selected.some(f => f.size > limit || !/\.(pdf|docx|txt|md)$/i.test(f.name));
          setFileError(invalid ? `Gunakan maksimal 20 berkas PDF/DOCX/TXT/MD, masing-masing maksimal ${Math.round(limit / 1024 / 1024)} MB.` : "");
          if (!invalid) { reset(); setFiles(selected); if (!context.name && selected[0]) setContext(c => ({ ...c, name: selected[0].name.replace(/\.[^.]+$/, "").slice(0, 160) })); }
        }} /><small>PDF berisi teks, DOCX, TXT atau Markdown. Maksimal {Math.round(limit / 1024 / 1024)} MB per berkas.</small>{files.map(file => <span key={`${file.name}-${file.size}`}>{file.name} ? {Math.ceil(file.size / 1024)} KB</span>)}</label>}
        </>}
      </section>
      <section><h2>Apa yang ingin Anda periksa?</h2><div className="business-fields">
        <label className="business-field-wide">Nama analisis<input required minLength={2} maxLength={160} value={context.name} onChange={e => change("name", e.target.value)} disabled={intakeLocked} placeholder="Contoh: Rencana pembukaan kedai" /></label>
        <label className="business-field-wide">Keterangan dan pertanyaan<textarea required minLength={10} maxLength={2000} rows={3} value={context.decision_question} onChange={e => change("decision_question", e.target.value)} disabled={intakeLocked} placeholder="Jelaskan rencana bisnis dan keputusan yang ingin diuji. Misalnya: apa risiko ekspansi jika harga bahan baku naik?" /></label>
      </div></section>
      <section><h2>Informasi yang boleh dibagikan</h2>{savedDemo && <><p>Gunakan brief contoh agar isi simulasi sesuai dengan konsep yang dibagikan ke persona.</p><button type="button" className="button secondary" disabled={publicBrief === savedDemo.publicBrief} onClick={() => { setPublicBrief(savedDemo.publicBrief); setBriefError(""); }}>Isi brief contoh</button></>}<StakeholderBriefField value={publicBrief} onChange={value => { reset(); setBriefError(""); setPublicBrief(value); }} disabled={intakeLocked} />{briefError && <p role="alert">{briefError}</p>}</section>
      <details><summary>Pengaturan tambahan</summary><div className="business-fields">
        <label>Industri<input maxLength={100} value={context.industry} onChange={e => change("industry", e.target.value)} disabled={intakeLocked} placeholder="Opsional, jika sudah diketahui" /></label>
        <label>Wilayah<input maxLength={120} value={context.region} onChange={e => change("region", e.target.value)} disabled={intakeLocked} placeholder="Opsional, untuk mencocokkan evidence wilayah" /></label>
        <label>Target customer<input maxLength={300} value={context.target_customer} onChange={e => change("target_customer", e.target.value)} disabled={intakeLocked} placeholder="Opsional" /></label>
        <label>Mode analisis<select value={engine} disabled={intakeLocked} onChange={e => { reset(); setEngine(e.target.value as "fixture" | "oasis"); }}><option value="oasis">{savedDemo ? "AI (run tersimpan)" : "AI live"}</option>{context.data_classification === "synthetic" && <option value="fixture">Demo tanpa AI ? respons terprogram</option>}</select></label>
        <label>Jenis interaksi<select value={interactionMode} disabled={intakeLocked} onChange={e => { reset(); setInteractionMode(e.target.value as "pairwise" | "swarm"); }}><option value="swarm">Diskusi swarm</option><option value="pairwise">Interaksi berpasangan</option></select></label>
        {interactionMode === "swarm" && <label>Jumlah perspektif customer<input type="number" min={2} max={6} required value={customerCount} disabled={intakeLocked} onChange={e => { reset(); setCustomerCount(Number(e.target.value)); }} /></label>}
        <label>Ronde interaksi<input type="number" min={2} max={12} required value={rounds} disabled={intakeLocked} onChange={e => { reset(); setRounds(Number(e.target.value)); }} /></label>
        <label>Klasifikasi data<select value={context.data_classification} disabled={example || create.isPending} onChange={e => { change("data_classification", e.target.value); if (e.target.value !== "synthetic") setEngine("oasis"); }}><option value="non_confidential">Non-rahasia</option><option value="public">Publik</option><option value="synthetic">Sintetis</option></select></label>
      </div></details>
      <p>Persona dan asumsi disiapkan dari dokumen tanpa persetujuan satu per satu. Hasilnya tetap perlu diperiksa; nilai yang belum jelas dibiarkan belum diketahui.</p>
      {!savedDemo && <label className="business-check"><input type="checkbox" required disabled={intakeLocked} />Saya berwenang memakai dokumen ini dan mengizinkan konteksnya diproses oleh model. Dokumen tidak memuat informasi rahasia atau data pribadi.</label>}
      {engine === "fixture" && <Notice>Demo tanpa AI memakai persona kontekstual dan respons terprogram. Tidak ada panggilan model.</Notice>}
      {!savedDemo && engine === "oasis" && capabilities.data && !capabilities.data.oasis_available && <Notice error>Model atau runtime belum tersedia. Periksa layanan, atau gunakan contoh sintetis dengan mode demo di pengaturan tambahan.</Notice>}
      {fileError && <Notice error>{fileError}</Notice>}{create.isError && <Notice error>{errorText(create.error)}</Notice>}
      {create.isError && requestFrozen && <Notice>Brief dan input dibekukan karena status permintaan belum pasti. Gunakan tombol yang sama untuk mencoba permintaan tersimpan; identitas run tidak berubah.</Notice>}
      <div className="business-actions"><button className="button primary" disabled={create.isPending || !!fileError || (!!savedDemo && !demoDocumentSelected) || (requestFrozen ? submittedIntent !== "analysis" : publicBrief.trim().length < 20)} onClick={() => { intent.current = "analysis"; }}>{phase || (savedDemo ? "Mulai simulasi demo" : "Mulai analisis")}</button><button className="button secondary" disabled={create.isPending || !!fileError || (!!savedDemo && (!demoDocumentSelected || publicBrief.trim().length < 20)) || (requestFrozen && submittedIntent !== "workspace")} onClick={() => { intent.current = "workspace"; }}>Buka ruang ide dahulu</button>{savedProject && create.isError && <Link to={`/business/projects/${savedProject}`}>Buka dokumen yang sudah tersimpan</Link>}</div>
    </form>
  </AppShell>;
}

function ClaimEditor({ claim, projectId, onSaved }: { claim: BusinessClaim; projectId: string; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(claim.normalized_text);
  const [value, setValue] = useState(claim.value ?? "");
  const [variable, setVariable] = useState(claim.variable ?? "");
  const [unit, setUnit] = useState(claim.unit ?? "");
  const mutation = useMutation({ mutationFn: (changes: Record<string, unknown>) => patchBusinessClaim(projectId, claim, changes), onSuccess: () => { setEditing(false); onSaved(); } });
  const units: Record<string, string> = { selling_price: "IDR/unit", variable_cost: "IDR/unit", fixed_cost_monthly: "IDR/month", volume_monthly: "units/month" };
  return <article className="business-claim">
    <div className="business-row-heading"><div><span className={`business-status ${claim.review_status}`}>{claim.review_status === "approved" ? "Disetujui" : claim.review_status === "rejected" ? "Ditolak" : "Perlu review"}</span><span className="business-muted">{claim.classification} · evidence belum tervalidasi</span></div><button className="business-text-button" onClick={() => setEditing(!editing)} aria-expanded={editing}>{editing ? "Tutup editor" : "Koreksi asumsi"}</button></div>
    <p>{claim.normalized_text}</p>
    <details className="business-source"><summary>Lihat kutipan dan lokasi sumber</summary><blockquote>{claim.quote}</blockquote><p>Dokumen {claim.source.document_id} · karakter {claim.source.locator.char_start}–{claim.source.locator.char_end}{claim.source.locator.page ? ` · halaman ${claim.source.locator.page}` : ""}{claim.source.locator.table ? ` · tabel ${claim.source.locator.table}, baris ${claim.source.locator.row}, kolom ${claim.source.locator.column}` : ""}</p></details>
    {editing && <form className="business-inline-editor" onSubmit={e => { e.preventDefault(); mutation.mutate({ normalized_text: text, variable: variable || null, value: value === "" ? null : value, unit: unit || null, review_status: "approved" }); }}>
      <label className="business-field-wide">Asumsi yang dinormalisasi<textarea rows={2} value={text} onChange={e => setText(e.target.value)} required maxLength={6000} /></label>
      <label>Variabel finansial<select value={variable} onChange={e => { setVariable(e.target.value); setUnit(units[e.target.value] ?? ""); }}><option value="">Bukan input finansial</option><option value="selling_price">Harga jual per unit</option><option value="variable_cost">Biaya variabel per unit</option><option value="fixed_cost_monthly">Biaya tetap per bulan</option><option value="volume_monthly">Volume per bulan</option></select></label>
      <label>Nilai (kosong = unknown)<input type="number" min="0" max="1000000000000000" step="any" value={value} onChange={e => setValue(e.target.value)} /></label><label>Satuan<input value={unit} maxLength={100} onChange={e => setUnit(e.target.value)} /></label>
      <button className="button primary" disabled={mutation.isPending}>Simpan dan setujui</button>
    </form>}
    <div className="business-claim-actions"><button className="business-text-button" disabled={mutation.isPending || claim.review_status === "approved"} onClick={() => mutation.mutate({ review_status: "approved" })}>Setujui asumsi</button><button className="business-text-button" disabled={mutation.isPending || claim.review_status === "rejected"} onClick={() => mutation.mutate({ review_status: "rejected" })}>Tolak dari analisis</button></div>
    {mutation.isError && <Notice error>{errorText(mutation.error)}</Notice>}
  </article>;
}

function PersonaEditor({ persona, projectId, personaNames, onSaved }: { persona: BusinessPersona; projectId: string; personaNames: Record<string, string>; onSaved: () => void }) {
  const [name, setName] = useState(persona.name);
  const [goal, setGoal] = useState(persona.goals.join("\n"));
  const [attributes, setAttributes] = useState({ motivations: persona.motivations.join("\n"), constraints: persona.constraints.join("\n"), knowledge: persona.knowledge.join("\n"), interests: persona.interests.join("\n") });
  const mutation = useMutation({ mutationFn: (changes: Record<string, unknown>) => patchBusinessPersona(projectId, persona, changes), onSuccess: onSaved });
  return <article className="business-persona"><div className="business-row-heading"><span className={`business-status ${persona.stakeholder_type}`}>{persona.stakeholder_type === "hidden" ? "Kandidat stakeholder terlewat" : persona.stakeholder_type === "indirect" ? "Tidak langsung" : "Langsung"}</span><span className="business-muted">{persona.role}</span></div><h3 className="persona-identity"><PersonaAvatar id={persona.id} /><span>{persona.name}</span></h3><p>{persona.discovery_rationale}</p><p><strong>Tujuan:</strong> {persona.goals.join("; ")}</p><p className="business-muted">Profil/tujuan bersifat hipotesis kecuali atribut yang memiliki dukungan sumber. Respons tetap sintetis.</p>
    <details><summary>Review profil, konteks dan provenance</summary><form className="business-persona-form" onSubmit={e => { e.preventDefault(); mutation.mutate({ name, goals: goal.split("\n").map(v => v.trim()).filter(Boolean), ...Object.fromEntries(Object.entries(attributes).map(([key, value]) => [key, value.split("\n").map(v => v.trim()).filter(Boolean)])), reviewed: true }); }}><label>Nama peran<input required minLength={2} maxLength={160} value={name} onChange={e => setName(e.target.value)} /></label><label>Tujuan (satu per baris)<textarea required rows={3} value={goal} onChange={e => setGoal(e.target.value)} /></label>{([['motivations', 'Motivasi'], ['constraints', 'Kendala'], ['knowledge', 'Pengetahuan yang dibagikan'], ['interests', 'Kepentingan']] as const).map(([key, label]) => <label key={key}>{label} (satu per baris)<textarea rows={2} value={attributes[key]} onChange={e => setAttributes(current => ({ ...current, [key]: e.target.value }))} /></label>)}<dl className="business-persona-attributes"><dt>Relasi yang diusulkan</dt><dd>{persona.relationships.length ? persona.relationships.map(id => personaNames[id] ?? "Stakeholder belum dikenal").join("; ") : "Belum ada relasi"}</dd></dl><pre>{JSON.stringify(persona.provenance, null, 2)}</pre><button className="button secondary" disabled={mutation.isPending}>Simpan profil dan setujui</button></form></details>
    <div className="business-persona-controls"><label className="business-check"><input type="checkbox" checked={persona.active} disabled={mutation.isPending} onChange={e => mutation.mutate({ active: e.target.checked })} />Aktif dalam simulasi</label><button className="business-text-button" disabled={mutation.isPending || persona.reviewed} onClick={() => mutation.mutate({ reviewed: true })}>{persona.reviewed ? "Profil sudah ditinjau" : "Setujui profil"}</button></div>{mutation.isError && <Notice error>{errorText(mutation.error)}</Notice>}
  </article>;
}

function AddPersona({ project, onSaved }: { project: BusinessProject; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [role, setRole] = useState("partner");
  const mutation = useMutation({ mutationFn: () => addBusinessPersona(project.id, project.revision, { id: "user-supplied", name, role, stakeholder_type: "indirect", goals: [goal], motivations: [], constraints: ["Peran dan tujuan adalah asumsi pengguna"], knowledge: [project.context.industry, project.context.region], interests: [], relationships: [], provenance: {}, discovery_rationale: "Ditambahkan pengguna untuk menguji perspektif yang belum tercakup", active: true, reviewed: true, revision: 1 }), onSuccess: () => { setName(""); setGoal(""); onSaved(); } });
  return <details className="business-add-persona"><summary>Tambahkan perspektif stakeholder</summary><form className="business-fields" onSubmit={e => { e.preventDefault(); mutation.mutate(); }}><label>Nama peran<input required minLength={2} maxLength={160} value={name} onChange={e => setName(e.target.value)} /></label><label>Jenis peran<select value={role} onChange={e => setRole(e.target.value)}>{["partner", "customer", "supplier", "competitor", "employee", "regulator", "investor", "community", "operator"].map(r => <option key={r}>{r}</option>)}</select></label><label className="business-field-wide">Tujuan utama<textarea required maxLength={1000} value={goal} onChange={e => setGoal(e.target.value)} /></label><button className="button secondary" disabled={mutation.isPending}>Tambahkan persona</button></form>{mutation.isError && <Notice error>{errorText(mutation.error)}</Notice>}</details>;
}

export function BusinessProjectPage() {
  const { projectId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "claims";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: businessKeys.project(projectId), queryFn: () => getBusinessProject(projectId), refetchInterval: q => q.state.data?.analyses.some(a => ["queued", "running"].includes(a.status)) ? 1500 : false });
  const capabilities = useQuery({ queryKey: ["business", "capabilities"], queryFn: getBusinessCapabilities });
  const [engine, setEngine] = useState<"fixture" | "oasis">("oasis");
  const [rounds, setRounds] = useState(4);
  const [publicBriefs, setPublicBriefs] = useState<Record<string, string>>({});
  const publicBrief = publicBriefs[projectId] ?? "";
  const setPublicBrief = (value: string) => setPublicBriefs(old => ({ ...old, [projectId]: value }));
  const refresh = () => { queryClient.invalidateQueries({ queryKey: businessKeys.project(projectId) }); queryClient.invalidateQueries({ queryKey: businessKeys.projects }); };
  const approve = useMutation({ mutationFn: () => approveBusinessClaims(projectId, query.data!.revision), onSuccess: refresh });
  const discovery = useMutation({ mutationFn: () => discoverBusinessStakeholders(projectId, query.data!.revision), onSuccess: () => { refresh(); setParams({ tab: "personas" }); } });
  const launch = useBusinessLaunch({ projectId, revision: query.data?.revision ?? 0, engine, rounds, brief: publicBrief, onSuccess: run => navigate(`/business/analyses/${run.id}`), onRejected: refresh });
  const start = { isPending: launch.isPending && launch.mode === "reviewed", isError: launch.isError && launch.mode === "reviewed", error: launch.error, mutate: () => launch.mutate("reviewed") };
  const quick = { isPending: launch.isPending && launch.mode === "quick", isError: launch.isError && launch.mode === "quick", error: launch.error, mutate: () => launch.mutate("quick") };
  const upload = useMutation({ mutationFn: (files: File[]) => uploadBusinessDocuments(projectId, files), onSuccess: refresh });
  const exclude = useMutation({ mutationFn: (documentId: string) => excludeBusinessDocument(projectId, documentId, query.data!.revision), onSuccess: refresh });
  const project = query.data;
  const pending = project?.claims.filter(c => c.review_status === "pending").length ?? 0;
  const active = project?.personas.filter(p => p.active) ?? [];
  const ready = !!project && project.claims.some(c => c.review_status === "approved") && pending === 0 && active.length >= 2 && active.every(p => p.reviewed) && project.documents.every(d => d.status === "ready" || d.status === "excluded");
  return <AppShell title={project?.context.name ?? "Proyek bisnis"} subtitle={project?.context.decision_question ?? "Memuat konteks keputusan…"} actions={<Link to="/business" className="button secondary">Kembali ke awal</Link>}>
    <div className="business-workspace">
      {query.isPending && <p role="status">Memuat proyek…</p>}{query.isError && <Notice error>{errorText(query.error)}</Notice>}
      {project && <>
        <div className="business-context-strip"><span>{project.context.industry} · {project.context.region}</span><span>Customer: {project.context.target_customer}</span><span>Revisi {project.revision} · {project.context.data_classification === "synthetic" ? "Data sintetis" : "Data " + project.context.data_classification}</span></div>
        {tab !== "chat" && <section className="business-section-heading"><div><h2>Langsung analisis dokumen ini.</h2><p>Persona dibuat otomatis sesuai dokumen. Pengaturan dan sumber tetap bisa diperiksa di bawah.</p></div><button className="button primary" disabled={launch.blockedFor("quick", publicBrief.trim().length >= 20 && !!project.documents.length && !project.analyses.some(run => ["queued", "running"].includes(run.status)))} onClick={() => quick.mutate()}>{quick.isPending ? "Menyiapkan..." : "Analisis otomatis"}</button></section>}
        {tab !== "chat" && <section><StakeholderBriefField value={publicBrief} onChange={setPublicBrief} disabled={launch.locked} />{publicBrief.trim().length < 20 && <p>Isi brief minimal 20 karakter untuk mengaktifkan analisis. Dokumen internal tetap terpisah.</p>}</section>}
        {launch.isError && launch.frozen && <Notice>Brief dan pengaturan run dibekukan karena status permintaan belum pasti. Coba tombol analisis yang sama untuk memeriksa permintaan tersimpan tanpa identitas baru.</Notice>}
        {quick.isError && <Notice error>{errorText(quick.error)}</Notice>}
        <nav className="business-tabs" aria-label="Tahap review proyek">{[["chat", "Chat & ide"], ["claims", "Asumsi & dokumen"], ["personas", "Stakeholder & persona"], ["runs", "Pengaturan analisis"]].map(([id, label]) => <button key={id} className={tab === id ? "active" : ""} aria-current={tab === id ? "page" : undefined} onClick={() => setParams({ tab: id })}>{label}</button>)}</nav>
        {tab === "chat" && <ProjectConversation key={projectId} project={project} capabilities={capabilities.data} onChanged={refresh} />}
        {tab === "claims" && <>
          <section className="business-section-heading"><div><h2>Periksa asumsi sebelum analisis.</h2><p>{pending} dari {project.claims.length} claim menunggu review. Persetujuan memastikan input sesuai dokumen; kebenaran eksternal tetap perlu evidence.</p></div><button className="button secondary" disabled={!pending || approve.isPending} onClick={() => approve.mutate()}>Setujui seluruh claim pending</button></section>
          <div className="business-documents">{project.documents.map(d => <div key={d.id}><strong>{d.name}</strong><span>{d.status === "ready" ? `${d.content.claim_count} kandidat claim` : d.status === "excluded" ? "Dikecualikan dari analisis berikutnya" : d.status === "needs_ocr" ? "Membutuhkan OCR" : "Ekstraksi gagal"}</span>{d.content.error && <p role="alert">{d.content.error}</p>}{d.status !== "excluded" && <button className="business-text-button" disabled={exclude.isPending} onClick={() => exclude.mutate(d.id)}>Kecualikan dokumen</button>}</div>)}<label className="business-upload-compact">{upload.isPending ? "Memproses dokumen…" : "Tambahkan dokumen"}<input type="file" accept=".pdf,.docx,.txt,.md" multiple disabled={upload.isPending} onChange={e => { const files = Array.from(e.target.files ?? []); if (files.length) upload.mutate(files); e.target.value = ""; }} /></label></div>
          {!project.claims.length && <Notice>Unggah dokumen yang dapat dibaca untuk mengekstrak asumsi. Tidak ada nilai yang akan diisi secara otomatis bila sumber tidak tersedia.</Notice>}
          {project.claims.map(claim => <ClaimEditor key={`${claim.id}-${claim.revision}`} claim={claim} projectId={projectId} onSaved={refresh} />)}
          {approve.isError && <Notice error>{errorText(approve.error)}</Notice>}{upload.isError && <Notice error>{errorText(upload.error)}</Notice>}{exclude.isError && <Notice error>{errorText(exclude.error)}</Notice>}
          <div className="business-actions"><button className="button primary" disabled={!project.claims.length || discovery.isPending} onClick={() => project.personas.length ? setParams({ tab: "personas" }) : discovery.mutate()}>{discovery.isPending ? "Mengusulkan stakeholder…" : project.personas.length ? "Lanjut review persona" : "Temukan stakeholder & persona"}</button></div>
        </>}
        {tab === "personas" && <>
          <section className="business-section-heading"><div><h2>Siapa yang perlu dipertimbangkan?</h2><p>Tinjau kandidat stakeholder, tujuan, dan batas pengetahuan. Jumlah persona tidak mewakili proporsi pasar nyata.</p></div>{!project.personas.length && <button className="button primary" disabled={discovery.isPending} onClick={() => discovery.mutate()}>{discovery.isPending ? "Menemukan kandidat…" : "Temukan stakeholder"}</button>}</section>
          {capabilities.data?.discovery_mode === "contextual_candidates" && <Notice>Provider LLM belum tersedia. Kandidat berikut berasal dari peran kontekstual untuk direview; discovery live belum dijalankan.</Notice>}
          {project.personas.map(persona => <PersonaEditor key={`${persona.id}-${persona.revision}`} persona={persona} projectId={projectId} personaNames={Object.fromEntries(project.personas.map(p => [p.id, p.name]))} onSaved={refresh} />)}
          <AddPersona project={project} onSaved={refresh} /><div className="business-actions"><button className="button primary" onClick={() => setParams({ tab: "runs" })}>Konfigurasi analisis</button><span>{active.filter(p => p.reviewed).length}/{active.length} persona aktif sudah ditinjau.</span></div>
        </>}
        {discovery.isError && <Notice error>{errorText(discovery.error)}</Notice>}
        {tab === "runs" && <>
          <section className="business-run-config"><div><h2>Jalankan pemeriksaan lintas perspektif.</h2><p>Empat specialist menilai asumsi dan hipotesis interaksi. Konfigurasi serta revisi input dibekukan pada setiap run.</p></div><div className="business-fields"><label>Engine<select value={engine} disabled={launch.locked} onChange={e => setEngine(e.target.value as "fixture" | "oasis")}><option value="oasis" disabled={!capabilities.data?.oasis_available}>OASIS + specialist live{!capabilities.data?.oasis_available ? " — belum dikonfigurasi" : ""}</option>{project.context.data_classification === "synthetic" && <option value="fixture">Fixture sintetis — tanpa model live</option>}</select></label><label>Ronde interaksi<input type="number" min={2} max={12} disabled={launch.locked} value={rounds} onChange={e => setRounds(Number(e.target.value))} /></label></div>
            {!ready && <Notice>Untuk mulai: review semua claim, setujui minimal dua persona aktif, dan pastikan seluruh dokumen dapat dibaca.</Notice>}{engine === "fixture" && <Notice>Mode fixture menghasilkan respons yang diprogram untuk demonstrasi. Hasilnya tidak membuktikan kualitas simulasi AI live.</Notice>}
            {start.isError && <Notice error>{errorText(start.error)}</Notice>}<button className="button primary" disabled={launch.blockedFor("reviewed", ready && publicBrief.trim().length >= 20 && (engine !== "oasis" || !!capabilities.data?.oasis_available))} onClick={() => start.mutate()}>{start.isPending ? "Menyiapkan run…" : "Mulai analisis"}</button>
          </section>

        </>}
      </>}
    </div>
  </AppShell>;
}
