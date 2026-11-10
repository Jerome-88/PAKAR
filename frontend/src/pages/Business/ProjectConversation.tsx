import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AgentIdentity } from "../../components/PersonaAvatar/PersonaAvatar";
import { ApiError } from "../../api/client";
import { businessKeys, cancelBusinessChat, getBusinessAnalysis, getBusinessConversation, getIdeaRevisions, saveBusinessIdea, sendBusinessChat, startQuickBusinessAnalysis, uploadBusinessDocuments } from "../../api/business";
import type { BusinessAnalysis, BusinessCapabilities, BusinessProject, ChatTarget, ChatTurn, Conversation, IdeaDraft } from "../../api/business";
import { errorText } from "./businessFormatting";
import "./ProjectConversation.css";
import { StakeholderBriefField } from "./StakeholderBriefField";
import { ConversationAnswer } from "./ConversationAnswer";
import { BusinessText } from "./BusinessText";

const targets: Record<ChatTarget, string> = { facilitator: "Fasilitator PAKAR", market: "Market Agent", finance: "Finance Agent", legal: "Legal/Compliance Agent", risk: "Risk Agent" };
const states = { queued: "Menunggu giliran", running: "Sedang menyiapkan jawaban", failed: "Jawaban belum berhasil", cancelled: "Dibatalkan", completed: "Selesai" };
type Editor = { ideaId?: string; key: string; draft: IdeaDraft };
const uniqueTurns = (turns: ChatTurn[]) => [...new Map(turns.map(t => [t.id, t])).values()].sort((a, b) => a.sequence - b.sequence);

export function SavedProjectConversation({ analysis, onSources }: { analysis: BusinessAnalysis; onSources: () => void }) {
  const findings = (analysis.result.findings ?? []).filter(finding => finding.event_ids.length > 0);
  return <section className="project-conversation analysis-conversation" aria-labelledby="conversation-title">
    <div className="business-section-heading"><div><h2 id="conversation-title">Diskusikan hasil dengan PAKAR</h2><p>Ulasan specialist dari run yang sama. Pertanyaan baru tersedia di aplikasi utama.</p></div><button type="button" className="business-text-button" onClick={onSources}>Kelola ide &amp; sumber</button></div>
    <div className="project-conversation-layout"><div className="project-chat">
      <p className="analysis-chat-context">Konteks: {analysis.input_snapshot.context.name}.</p>
      <div className="project-chat-log" tabIndex={0} role="region" aria-label="Ulasan AI tersimpan">
        {analysis.input_snapshot.idea && <article className="project-chat-turn"><div className="project-chat-message is-user"><div className="project-chat-author"><strong>Anda</strong><span>Ide yang diuji</span></div><BusinessText value={analysis.input_snapshot.idea.text} /></div></article>}
        {findings.map(finding => <article className="project-chat-turn" key={finding.id}><div className="project-chat-message is-agent"><div className="project-chat-author"><AgentIdentity name={finding.author} /><span>Review tersimpan</span></div><h3>{finding.title}</h3><BusinessText value={finding.reasoning} /><p><strong>Langkah validasi:</strong> {finding.next_validation}</p></div></article>)}
      </div>
      <div className="project-chat-composer"><label htmlFor="saved-chat-message">Pesan atau penjelasan tambahan<textarea id="saved-chat-message" disabled rows={3} placeholder="Chat baru tersedia di aplikasi utama. Demo menampilkan hasil dan ulasan yang sudah tersimpan." /></label><div className="project-chat-controls"><label>Tanyakan kepada<select disabled defaultValue="facilitator"><option value="facilitator">Fasilitator PAKAR</option></select></label><button type="button" className="button primary" disabled>Kirim ke AI</button></div><p className="project-chat-note">Membuka ulasan tersimpan tidak menjalankan AI atau memakai kredit.</p></div>
    </div></div>
  </section>;
}

export function ProjectConversation({ project, capabilities, onChanged, analysis }: { project: BusinessProject; capabilities?: BusinessCapabilities; onChanged: () => void; analysis?: BusinessAnalysis }) {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const queryKey = ["business", "conversation", project.id];
  const conversation = useQuery({ queryKey, queryFn: () => getBusinessConversation(project.id), refetchInterval: q => q.state.data?.turns.some(t => ["queued", "running"].includes(t.status)) ? 1200 : false });
  const [older, setOlder] = useState<ChatTurn[]>([]);
  const [before, setBefore] = useState<number | null | undefined>(undefined);
  const [chosenIdea, setChosenIdea] = useState<string | null>(null);
  const [chosenRevision, setChosenRevision] = useState<string | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [message, setMessage] = useState("");
  const [sentTurnId, setSentTurnId] = useState<string | null>(null);
  const [target, setTarget] = useState<ChatTarget>("facilitator");
  const [analysisId, setAnalysisId] = useState(analysis?.id ?? params.get("analysis") ?? "");
  const sourceAnalysis = useQuery({ queryKey: businessKeys.analysis(analysisId), queryFn: () => getBusinessAnalysis(analysisId), enabled: !!analysisId && !analysis, refetchInterval: q => ["queued", "running"].includes(q.state.data?.status ?? "") ? 1500 : false });
  const source = analysis ?? sourceAnalysis.data;
  const sourceReady = !analysisId || (source?.project_id === project.id && ["completed", "partial"].includes(source.status));
  const [engine, setEngine] = useState<"oasis" | "fixture">("oasis");
  const [briefs, setBriefs] = useState<Record<string, string>>({});
  const [runFrozen, setRunFrozen] = useState(false);
  const [localError, setLocalError] = useState("");
  const request = useRef<{ key: string; body: ChatTurn["request"] } | null>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const composer = useRef<HTMLTextAreaElement>(null);
  const ideas = conversation.data?.ideas ?? [];
  const idea = ideas.find(i => i.id === (chosenIdea ?? ideas[0]?.id));
  const history = useQuery({ queryKey: ["business", "idea-revisions", project.id, idea?.id], queryFn: () => getIdeaRevisions(project.id, idea!.id), enabled: !!idea && !analysis });
  const revision = (chosenRevision && history.data?.items.find(r => r.id === chosenRevision)) || idea?.latest_revision;
  const allTurns = uniqueTurns([...older, ...(conversation.data?.turns ?? [])]);
  const turns = analysis ? allTurns.filter(t => t.request.analysis_id === analysis.id) : allTurns;
  const active = allTurns.find(t => ["queued", "running"].includes(t.status));
  const last = turns.at(-1);
  const sentTurn = turns.find(t => t.id === sentTurnId);
  useEffect(() => {
    if (scroll.current && pinned.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [last?.id, last?.status]);
  const refresh = () => { void client.invalidateQueries({ queryKey }); onChanged(); };
  const editRevision = (value?: string, turn?: string) => {
    setEditor({ ideaId: idea?.id, key: crypto.randomUUID(), draft: {
      expected_revision: project.revision, expected_version: idea?.version ?? 0,
      title: revision?.content.title ?? "", text: value ?? revision?.content.text ?? "",
      document_ids: revision?.content.document_ids ?? [], source_turn_ids: [...new Set([...(revision?.content.source_turn_ids ?? []), ...(turn ? [turn] : [])])].slice(-10),
    } });
  };
  const save = useMutation({ mutationFn: () => saveBusinessIdea(project.id, { ...editor!.draft, expected_revision: project.revision }, editor!.key, editor!.ideaId), onSuccess: row => {
    setChosenIdea(row.idea_id); setChosenRevision(null); setEditor(null); resetRunIdentity(); refresh();
    void client.invalidateQueries({ queryKey: ["business", "idea-revisions", project.id, row.idea_id] });
  } });
  const send = useMutation({ mutationFn: () => {
    request.current ??= { key: crypto.randomUUID(), body: { content: message, target, expected_revision: project.revision, idea_revision_id: analysis ? analysis.input_snapshot.idea?.id ?? null : revision?.id ?? null, analysis_id: analysisId || null } };
    return sendBusinessChat(project.id, request.current.body, request.current.key);
  }, onSuccess: row => {
    client.setQueryData<Conversation>(queryKey, old => old ? { ...old, turns: uniqueTurns([...old.turns, row]) } : { ideas: [], turns: [row], next_before: null });
    setMessage(""); setSentTurnId(row.id); request.current = null; pinned.current = true; refresh(); composer.current?.focus();
  } });
  const cancel = useMutation({ mutationFn: (id: string) => cancelBusinessChat(project.id, id), onSuccess: refresh });
  const loadOlder = useMutation({ mutationFn: () => getBusinessConversation(project.id, before ?? conversation.data!.next_before!), onSuccess: page => { setOlder(old => uniqueTurns([...page.turns, ...old])); setBefore(page.next_before); pinned.current = false; } });
  const upload = useMutation({ mutationFn: ({ files, purpose }: { files: File[]; purpose: "evidence" | "idea" }) => uploadBusinessDocuments(project.id, files, purpose), onSuccess: (updated, options) => {
    setLocalError(""); refresh();
    if (options.purpose === "idea") {
      const fresh = updated.documents.filter(d => !project.documents.some(old => old.id === d.id) && d.status === "ready");
      if (fresh.length) setEditor({ key: crypto.randomUUID(), draft: { expected_revision: updated.revision, expected_version: 0, title: fresh[0].name.replace(/\.[^.]+$/, ""), text: "", document_ids: fresh.map(d => d.id), source_turn_ids: [] } });
    }
  } });
  const runKey = useRef<string | null>(null);
  const runInput = useRef<{ revision: number; idea: string; engine: "oasis" | "fixture"; brief: string } | null>(null);
  function resetRunIdentity() { runKey.current = null; runInput.current = null; setRunFrozen(false); }
  const run = useMutation({ mutationFn: () => {
    setRunFrozen(true);
    if (!runKey.current) { runKey.current = crypto.randomUUID(); runInput.current = { revision: project.revision, idea: revision!.id, engine, brief: briefs[revision!.id] ?? "" }; }
    return startQuickBusinessAnalysis(project.id, runInput.current!.revision, runInput.current!.engine, 2, runKey.current, { interaction_mode: "swarm", customer_count: 2, idea_revision_id: runInput.current!.idea, max_tokens: 60000, public_brief: runInput.current!.brief });
  }, onSuccess: row => navigate(`/business/analyses/${row.id}?tab=swarm`) });
  const staleRun = run.error instanceof ApiError && run.error.status === 409 && run.error.code === "revision_conflict";
  const recoverRun = useMutation({ mutationFn: async () => {
    if (!staleRun) return;
    await Promise.all([client.invalidateQueries({ queryKey: businessKeys.project(project.id) }), client.invalidateQueries({ queryKey })]);
    resetRunIdentity(); run.reset(); onChanged();
  } });
  const runLocked = run.isPending || (run.isError && !staleRun && runFrozen);
  const activeRun = project.analyses.find(a => ["queued", "running"].includes(a.status));
  const uploadFiles = (files: FileList | null, purpose: "evidence" | "idea") => {
    const items = Array.from(files ?? []);
    if (!items.length) return;
    if (items.length > 5 || items.some(f => f.size > (capabilities?.max_file_bytes ?? 20 * 1024 * 1024) || !/\.(pdf|docx|txt|md)$/i.test(f.name))) {
      setLocalError("Pilih maksimal 5 berkas PDF, DOCX, TXT atau MD dalam batas ukuran proyek."); return;
    }
    upload.mutate({ files: items, purpose });
  };
  const resetRequest = () => { request.current = null; send.reset(); };
  return <section className={`project-conversation${analysis ? " analysis-conversation" : ""}`} aria-labelledby="conversation-title">
    <div className="business-section-heading"><div><h2 id="conversation-title">{analysis ? "Diskusikan hasil dengan PAKAR" : "Ruang ide"}</h2><p>{analysis ? "Tanyakan alasan penilaian atau tambahkan konteks ide." : "Ajukan ide, lengkapi penjelasan, lalu uji bersama stakeholder. Dokumen dan riwayat analisis tetap bisa dirujuk."}</p></div>{analysis ? <Link to={`/business/projects/${project.id}?tab=chat&analysis=${analysis.id}`}>Kelola ide & sumber</Link> : <a href="#project-idea-panel">Kelola ide & sumber</a>}</div>
    {conversation.isPending && <p role="status">Memuat percakapan tersimpan…</p>}
    {conversation.isError && <p className="business-notice is-error" role="alert">{errorText(conversation.error)} <button type="button" onClick={() => void conversation.refetch()}>Muat ulang percakapan</button></p>}
    <div className="project-conversation-layout">
      <div className="project-chat">
        {analysis ? <p className="analysis-chat-context">Konteks: hasil analisis ini{analysis.input_snapshot.idea && <> · <strong>{analysis.input_snapshot.idea.title}, versi {analysis.input_snapshot.idea.version}</strong></>}.</p> : <div className="project-chat-context">
          <label>Bahas ide<select value={idea?.id ?? ""} disabled={send.isPending || !!active || runLocked} onChange={e => { setChosenIdea(e.target.value); setChosenRevision(null); resetRunIdentity(); resetRequest(); }}><option value="">Konteks proyek</option>{ideas.map(i => <option key={i.id} value={i.id}>{i.title}</option>)}</select></label>
          <label>Rujuk hasil analisis<select value={analysisId} disabled={send.isPending || !!active} onChange={e => { setAnalysisId(e.target.value); resetRequest(); }}><option value="">Tanpa hasil analisis</option>{analysisId && !project.analyses.some(a => a.id === analysisId && ["completed", "partial"].includes(a.status)) && <option value={analysisId}>Analisis terpilih · {sourceReady ? "tersimpan" : "memeriksa hasil"} · {analysisId.slice(-6)}</option>}{project.analyses.filter(a => ["completed", "partial"].includes(a.status)).map(a => <option key={a.id} value={a.id}>{a.review_source_id ? "Review lanjutan" : "Analisis"} · {new Date(a.created_at).toLocaleDateString("id-ID")} · {a.id.slice(-6)}</option>)}</select></label>
        </div>}
        <div className="project-chat-log" ref={scroll} tabIndex={0} role="region" aria-label="Riwayat percakapan proyek" onScroll={() => { const el = scroll.current; if (el) pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; }}>
          {(before === undefined ? conversation.data?.next_before : before) && <button type="button" className="business-text-button" disabled={loadOlder.isPending} onClick={() => loadOlder.mutate()}>Muat percakapan sebelumnya</button>}
          {!turns.length && !conversation.isPending && <div className="project-chat-empty">{analysis ? <div className="analysis-chat-prompts">{["Jelaskan alasan perbedaan sikap persona.", "Apa yang perlu saya perbaiki dari ide ini?", "Informasi apa yang masih kurang dari ide ini?"].map(prompt => <button type="button" className="business-text-button" key={prompt} onClick={() => { setMessage(prompt); resetRequest(); composer.current?.focus(); }}>{prompt}</button>)}</div> : <><h3>Mulai dari ide yang ingin diuji.</h3><p>Ceritakan ide atau tanyakan isi dokumen. Fasilitator dapat meminta penjelasan sebelum Anda menjalankan simulasi.</p><p>Misalnya: “Bagian mana dari ide ini yang perlu diperbaiki menurut data saya?”</p></>}</div>}
          {turns.map(turn => <article className="project-chat-turn" key={turn.id} id={`chat-turn-${turn.id}`}>
            <div className="project-chat-message is-user"><div className="project-chat-author"><strong>Anda</strong><time dateTime={turn.created_at}>{new Date(turn.created_at).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}</time></div><p>{turn.request.content}</p>{analysis ? <Link to={`/business/projects/${project.id}?tab=chat&analysis=${analysis.id}`}>Buat revisi ide di ruang ide</Link> : <button type="button" className="business-text-button" onClick={() => editRevision([revision?.content.text, `Penjelasan tambahan pengguna: ${turn.request.content}`].filter(Boolean).join("\n\n"), turn.id)}>Jadikan revisi ide</button>}{turn.request.idea_revision_id && <small>Ide saat dikirim: {turn.idea_context ? `${turn.idea_context.title} · versi ${turn.idea_context.version}` : "versi tersimpan"}</small>}</div>
            <div className="project-chat-message is-agent"><div className="project-chat-author"><AgentIdentity name={turn.response?.responder ?? targets[turn.request.target]} /><span>{states[turn.status]}</span></div>
              {turn.status === "completed" ? <><ConversationAnswer turn={turn} />
                {turn.response?.suggested_revision && <details><summary>Usulan revisi dari AI</summary><p>{turn.response.suggested_revision}</p>{analysis ? <Link to={`/business/projects/${project.id}?tab=chat&analysis=${analysis.id}`}>Periksa revisi di ruang ide</Link> : <button type="button" className="business-text-button" onClick={() => editRevision(turn.response!.suggested_revision!, turn.id)}>Periksa sebelum menyimpan revisi</button>}</details>}
              </> : <p role={turn.status === "failed" ? "alert" : "status"}>{turn.status === "failed" ? turn.response?.error ?? "Worker berhenti. Pesan tersimpan; tidak ada retry otomatis." : turn.status === "cancelled" ? "Permintaan dihentikan. Panggilan yang sudah dikirim dapat tetap dikenai biaya provider." : "Satu agent sedang memeriksa konteks. Percakapan akan tersimpan di proyek ini."}</p>}
              {["queued", "running"].includes(turn.status) && <button type="button" className="business-text-button" disabled={cancel.isPending} onClick={() => cancel.mutate(turn.id)}>Batalkan jawaban</button>}
            </div>
          </article>)}
        </div>
        <form className="project-chat-composer" onSubmit={e => { e.preventDefault(); send.mutate(); }}>
          <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{sentTurn?.status === "completed" ? `Jawaban baru dari ${sentTurn.response?.responder ?? targets[sentTurn.request.target]} tersedia dalam riwayat percakapan proyek.` : ""}</p>
          <label htmlFor="project-chat-message">Pesan atau penjelasan tambahan<textarea ref={composer} id="project-chat-message" rows={3} required minLength={2} maxLength={4000} value={message} disabled={send.isPending || !!active} onChange={e => { setMessage(e.target.value); resetRequest(); }} placeholder="Tanyakan alasan penilaian atau jelaskan bagian ide yang belum dipahami." /></label>
          <div className="project-chat-send"><label>Tanya kepada<select value={target} disabled={send.isPending || !!active} onChange={e => { setTarget(e.target.value as ChatTarget); resetRequest(); }}>{Object.entries(targets).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><button className="button primary" disabled={send.isPending || !!active || !message.trim() || !capabilities?.llm_available || conversation.isError || !sourceReady}>{send.isPending ? "Menyimpan pesan…" : "Kirim ke AI"}</button></div>
          {!sourceReady && <p className="business-notice">{analysis ? "Tunggu hingga hasil selesai atau parsial sebelum membahasnya di sini. Anda tetap bisa membahas proyek di ruang ide." : "Hasil analisis yang dipilih belum siap atau belum dapat dibaca. Tunggu hasilnya, atau pilih “Tanpa hasil analisis” untuk membahas proyek terlebih dahulu."}</p>}
          {analysis && active && active.request.analysis_id !== analysis.id && <p className="business-notice">Ada jawaban lain yang masih diproses di proyek ini. <Link to={`/business/projects/${project.id}?tab=chat`}>Buka percakapan proyek untuk menunggu atau membatalkannya.</Link></p>}
          {sourceAnalysis.isError && <p role="alert">{errorText(sourceAnalysis.error)}</p>}
          <p className="project-chat-note">Satu respons AI memakai kredit provider. Chat tidak menjalankan swarm atau mengubah ide tersimpan. Jawaban tetap perlu diperiksa.</p>
          {capabilities && !capabilities.llm_available && <p className="business-notice">Chat AI belum dikonfigurasi. Dokumen dan versi ide tetap dapat disimpan.</p>}
          {send.isError && <p className="business-notice is-error" role="alert">{errorText(send.error)} <button type="button" onClick={() => { resetRequest(); refresh(); }}>Muat konteks terbaru</button></p>}
          {cancel.isError && <p role="alert">{errorText(cancel.error)}</p>}{loadOlder.isError && <p role="alert">{errorText(loadOlder.error)}</p>}
        </form>
      </div>
      {!analysis && <aside id="project-idea-panel" className="project-idea-panel" aria-label="Ide dan sumber proyek" tabIndex={-1}>
        <div className="project-idea-heading"><h3>Ide yang diuji</h3><button type="button" className="business-text-button" onClick={() => { save.reset(); setEditor({ key: crypto.randomUUID(), draft: { expected_revision: project.revision, expected_version: 0, title: "", text: "", document_ids: [], source_turn_ids: [] } }); }}>Ide baru</button></div>
        {revision && <><p><strong>{revision.content.title}</strong><br />Versi {revision.version} · usulan pengguna</p><label>Versi yang dibahas<select value={revision.id} disabled={send.isPending || !!active || runLocked} onChange={e => { setChosenRevision(e.target.value); resetRunIdentity(); resetRequest(); }}>{(history.data?.items ?? [idea!.latest_revision]).map(r => <option key={r.id} value={r.id}>Versi {r.version}{r.version === idea!.version ? " · terbaru" : " · tersimpan"}</option>)}</select></label><details><summary>Baca isi ide</summary><p className="project-idea-text">{revision.content.text || "Isi ide berasal dari dokumen yang dipilih."}</p>{revision.content.document_ids.map(id => <p key={id}>{project.documents.find(d => d.id === id)?.name ?? "Dokumen ide"}</p>)}</details><button type="button" className="business-text-button" onClick={() => { save.reset(); editRevision(); }}>Edit sebagai versi baru</button></>}
        {!revision && !editor && <p>Simpan ide dari tulisan sendiri, penjelasan chat, atau dokumen ide.</p>}
        {history.isError && <p role="alert">{errorText(history.error)}</p>}
        {editor && <form className="project-idea-editor" onSubmit={e => { e.preventDefault(); save.mutate(); }}>
          <h4>{editor.ideaId ? "Periksa revisi sebelum disimpan" : "Ide baru"}</h4>
          <label>Nama ide<input required minLength={2} maxLength={160} value={editor.draft.title} disabled={save.isPending} onChange={e => setEditor({ ...editor, key: crypto.randomUUID(), draft: { ...editor.draft, title: e.target.value } })} /></label>
          <label>Isi ide<textarea rows={8} maxLength={6000} required={!editor.draft.document_ids.length} value={editor.draft.text} disabled={save.isPending} onChange={e => setEditor({ ...editor, key: crypto.randomUUID(), draft: { ...editor.draft, text: e.target.value } })} /><small>{editor.draft.text.length}/6.000 karakter{editor.draft.text.length > 6000 ? " · Ringkas teks sebelum menyimpan." : ""}</small></label>
          {project.documents.some(d => d.content.purpose === "idea" && d.status === "ready") && <fieldset><legend>Dokumen ide</legend>{project.documents.filter(d => d.content.purpose === "idea" && d.status === "ready").map(d => <label className="business-check" key={d.id}><input type="checkbox" checked={editor.draft.document_ids.includes(d.id)} disabled={save.isPending} onChange={e => setEditor({ ...editor, key: crypto.randomUUID(), draft: { ...editor.draft, document_ids: e.target.checked ? [...editor.draft.document_ids, d.id] : editor.draft.document_ids.filter(id => id !== d.id) } })} />{d.name}</label>)}</fieldset>}
          <p>Disimpan sebagai usulan/asumsi. Versi sebelumnya dan hasil analisis tetap tersimpan.</p><div className="business-actions"><button className="button primary" disabled={save.isPending || editor.draft.text.length > 6000}>{save.isPending ? "Menyimpan…" : "Simpan versi ide"}</button><button type="button" className="business-text-button" disabled={save.isPending} onClick={() => setEditor(null)}>Tutup editor</button></div>
          {save.isError && <p className="business-notice is-error" role="alert">{errorText(save.error)}</p>}
        </form>}
        {revision && <section className="project-idea-run"><h4>Uji versi {revision.version}</h4><p>Menjalankan diskusi stakeholder dan empat specialist sebagai hasil baru. Memakai versi ide yang dipilih di atas.</p>{project.context.data_classification === "synthetic" && <label>Mode simulasi<select value={engine} disabled={runLocked} onChange={e => { setEngine(e.target.value as "oasis" | "fixture"); resetRunIdentity(); }}><option value="oasis">AI live · memakai kredit</option><option value="fixture">Fixture sintetis · tanpa AI</option></select></label>}<StakeholderBriefField value={briefs[revision.id] ?? ""} disabled={runLocked} onChange={value => { setBriefs(old => ({ ...old, [revision.id]: value })); resetRunIdentity(); }} />{(briefs[revision.id] ?? "").trim().length < 20 && <p className="business-notice">Isi brief minimal 20 karakter sebelum menjalankan simulasi. Jangan masukkan data internal yang tidak ingin dibagikan.</p>}{run.isError && !staleRun && runFrozen && <p className="business-notice">Status permintaan belum pasti. Brief dibekukan agar mencoba lagi memakai permintaan yang sama.</p>}<button type="button" className="button primary" disabled={run.isPending || !!editor || !!activeRun || (briefs[revision.id] ?? "").trim().length < 20 || (engine === "oasis" && !capabilities?.oasis_available)} onClick={() => run.mutate()}>{run.isPending ? "Menyiapkan simulasi…" : `Analisis ide versi ${revision.version}`}</button>
          {editor ? <p>Simpan versi ide atau tutup editor sebelum memulai analisis.</p> : activeRun ? <p>Analisis lain masih berjalan. <Link to={`/business/analyses/${activeRun.id}`}>Buka hasil untuk menunggu atau membatalkan run tersebut.</Link></p> : engine === "oasis" && !capabilities?.oasis_available ? <p>Model atau runtime OASIS belum tersedia. {project.context.data_classification === "synthetic" ? "Pilih fixture sintetis untuk mencoba alur tanpa AI, atau periksa konfigurasi layanan." : "Periksa konfigurasi model dan runtime sebelum mencoba lagi."}</p> : null}
          <p className="project-chat-note">{engine === "oasis" ? "Aksi ini memakai kredit untuk satu run swarm baru, dua ronde. Chat sebelumnya tidak dijalankan ulang." : "Respons terprogram untuk pengujian alur; bukan penilaian AI."}</p>
          {run.isError && <div className="business-notice is-error" role="alert"><p>{errorText(run.error)}</p>{staleRun ? <><p>Input proyek sudah berubah dan permintaan ini ditolak. Muat konteks terbaru, periksa versi ide, lalu mulai lagi.</p><button type="button" disabled={recoverRun.isPending} onClick={() => recoverRun.mutate()}>Muat konteks analisis terbaru</button></> : <p>Jika koneksi terputus, coba tombol analisis kembali untuk memeriksa permintaan yang sama. Permintaan tidak dikirim dengan identitas baru.</p>}</div>}
          {recoverRun.isError && <p role="alert">{errorText(recoverRun.error)}</p>}
        </section>}
        <details className="project-source-list"><summary>Sumber proyek ({project.documents.length})</summary><ul>{project.documents.map(d => <li key={d.id}><strong>{d.name}</strong><span>{d.content.purpose === "idea" ? "Dokumen ide" : "Data / temuan"} · {d.status === "ready" ? "Teks terbaca" : d.status === "needs_ocr" ? "Perlu OCR" : d.status === "excluded" ? "Dikecualikan" : "Ekstraksi gagal"}</span></li>)}</ul><p>Grafik atau gambar belum dibaca dengan OCR. Sertakan angka penting sebagai teks.</p></details>
        <div className="project-source-upload"><label>Tambahkan data / temuan<input type="file" accept=".pdf,.docx,.txt,.md" multiple disabled={upload.isPending} onChange={e => { uploadFiles(e.target.files, "evidence"); e.target.value = ""; }} /></label><label>Unggah dokumen ide<input type="file" accept=".pdf,.docx,.txt,.md" multiple disabled={upload.isPending} onChange={e => { uploadFiles(e.target.files, "idea"); e.target.value = ""; }} /></label>{upload.isPending && <p role="status">Membaca dokumen…</p>}{localError && <p role="alert">{localError}</p>}{upload.isError && <p className="business-notice is-error" role="alert">{errorText(upload.error)}</p>}</div>
      </aside>}
    </div>
  </section>;
}
