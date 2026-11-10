from __future__ import annotations

import hashlib
import io
import json
import logging
import random
import tempfile
import threading
import time
from urllib.parse import urlsplit
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from sqlalchemy import insert, select, update
from werkzeug.utils import secure_filename

from ..documents import chunk_text, extract_document
from ..errors import ApiError, RevisionConflict, StageConflict, UnsupportedDocument, UploadQuotaExceeded
from .agents import BusinessLLM, structured_findings, validate_finding_references
from .contracts import AnalysisInput, QuickAnalysisInput, SpecialistReviewInput, BusinessContext, Finding, Persona, Shock, DialogueAction
from .evidence import BPSEvidence
from .intake import discover, extract_claims, financial_inputs
from .repository import BusinessRepository, uid, utcnow
from .simulation import BusinessSimulation, fixture_action
from .structured import review_schema
from .reporting import build_report, render_html
from .tables import business_analyses, business_claims, business_personas
from .budget import BudgetExceeded, RunCancelled, RunDeadline
from .usage import summarize_calls
from .spending import SpendLedger, SpendingLimit
from .reviews import PAIRED_POLICY, ROLES, run_paired_reviews
from .finding_checks import project_valid_findings
from .preparation import automatic_inputs, contextual_personas
from .swarm import SwarmSimulation, expand_customer_cohort, swarm_fixture_action, is_quiet_round
from .recovery import replay_committed
from .discussion import DialogueSimulation, ReactiveAgenda, reactive
from .information import freeze as freeze_information, scoped as information_scoped, bind_personas
from ..provider_errors import ProviderResponseError, ProviderTransportError

logger = logging.getLogger("pakar.business")


class BusinessService:
    def __init__(self, repository, storage, settings, oasis_runtime=None):
        self.shared = repository
        self.repository = BusinessRepository(repository)
        self.storage = storage
        self.settings = settings
        self.oasis = oasis_runtime
        self.evidence = BPSEvidence()
        self.spawn = None
        from .conversation import ConversationService
        self.conversation = ConversationService(self)

    def capabilities(self):
        return {"product": "PAKAR", "llm_available": bool(self.settings.llm_api_key), "oasis_available": self.oasis is not None and bool(self.settings.llm_api_key), "discovery_mode": "llm" if self.settings.llm_api_key else "contextual_candidates", "max_file_bytes": self.settings.max_file_upload_bytes, "max_request_bytes": self.settings.max_upload_bytes, "max_personas": 24, "supported_data_classifications": ["public", "synthetic", "non_confidential"]}

    def create(self, owner, payload, key=None):
        context = BusinessContext.model_validate(payload).model_dump(mode="json")
        return self.repository.create(owner, context, key, self.settings.max_active_projects_per_user)

    def delete_project(self, project_id, owner):
        keys, results = self.repository.delete_project(project_id, owner)
        pending = False
        for key in keys:
            try:
                self.storage.delete(key)
            except Exception:
                pending = True
                logger.warning("business_delete_storage_cleanup_failed project=%s", project_id)
        runtime_ids = [call.get("runtime_id") for result in results
                       for call in [*(result.get("runtime_calls") or []), *((result.get("simulation") or {}).get("usage") or {}).get("calls", [])]
                       if isinstance(call, dict)]
        import re
        import shutil
        root = self.settings.oasis_data_dir.resolve()
        for runtime_id in runtime_ids:
            if not isinstance(runtime_id, str) or not re.fullmatch(r"business-[0-9a-f]{32}", runtime_id):
                continue
            target = root / runtime_id
            if target.is_symlink() or target.resolve().parent != root:
                continue
            try:
                if target.is_dir():
                    shutil.rmtree(target)
            except OSError:
                pending = True
                logger.warning("business_delete_runtime_cleanup_failed project=%s", project_id)
        return {"status": "deleted", "cleanup_pending": pending}

    def upload(self, project_id, owner, files, purpose="evidence"):
        if purpose not in {"evidence", "idea"}:
            raise ValueError("Invalid document purpose")
        project = self.repository.project(project_id, owner)
        if not files or len(files) + len(project["documents"]) > self.settings.max_files_per_project:
            raise UploadQuotaExceeded("Pilih berkas dalam batas jumlah yang diizinkan")
        documents, claims, saved_keys = [], [], []
        try:
            for upload in files:
                name = secure_filename(upload.filename or "")
                suffix = Path(name).suffix.casefold()
                if suffix not in {".pdf", ".docx", ".txt", ".md"}:
                    raise UnsupportedDocument("Gunakan PDF, DOCX, TXT atau Markdown")
                content = upload.file.read(self.settings.max_file_upload_bytes + 1)
                if not content or len(content) > self.settings.max_file_upload_bytes:
                    raise UploadQuotaExceeded("Berkas kosong atau melebihi batas ukuran")
                document_id = uid("business_doc")
                storage_key = f"business/{project_id}/{document_id}{suffix}"
                self.storage.save(storage_key, content)
                saved_keys.append(storage_key)
                document = {"id": document_id, "name": name, "storage_key": storage_key, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "status": "ready", "content": {}, "created_at": utcnow()}
                with tempfile.TemporaryDirectory(prefix="pakar-parse-") as directory:
                    path = Path(directory) / f"source{suffix}"
                    path.write_bytes(content)
                    try:
                        extracted = extract_document(path, self.settings.max_pdf_pages, self.settings.max_extracted_chars)
                        chunks = chunk_text(document_id, extracted, self.settings.chunk_size, self.settings.chunk_overlap)
                        if len(chunks) > self.settings.max_chunks_per_document:
                            raise ValueError("Jumlah chunk melebihi batas ekstraksi")
                        parsed_claims = extract_claims(document_id, extracted)
                        if len(parsed_claims) > 400:
                            raise ValueError("Dokumen melebihi 400 segmen claim; pecah dokumen agar review dapat dilakukan")
                        claims.extend(parsed_claims)
                        document["content"] = {"chunks": chunks, "extraction_version": "pakar-source-v1", "claim_count": len(parsed_claims), "notice": "Nilai dan kategori adalah kandidat ekstraksi; review diperlukan. PDF scan memerlukan OCR terpisah."}
                    except (ValueError, RuntimeError) as error:
                        document["status"] = "needs_ocr" if suffix == ".pdf" and "tidak menghasilkan teks" in str(error) else "parse_failed"
                        document["content"] = {"error": str(error)[:500], "chunks": [], "claim_count": 0}
                document["content"]["purpose"] = purpose
                documents.append(document)
            self.repository.store_documents(project_id, owner, documents, claims, self.settings.max_files_per_project, self.settings.max_total_upload_bytes)
        except Exception:
            for key in saved_keys:
                self.storage.delete(key)
            raise
        return self.repository.project(project_id, owner)

    def discover(self, project_id, owner, expected_revision):
        project = self.repository.project(project_id, owner)
        if project["revision"] != expected_revision:
            raise RevisionConflict()
        if not project["claims"]:
            raise StageConflict("Unggah dokumen yang dapat dibaca sebelum discovery")
        if self.settings.llm_api_key:
            ledger = SpendLedger.open(self.settings, self.shared.engine, uid("discovery"))
            try:
                personas = BusinessLLM(self.settings, spending=ledger.budget if ledger else None).discover(project["context"], project["claims"], project["personas"])
            finally:
                if ledger:
                    ledger.close()
        else:
            personas = discover(project["context"], project["claims"], project["personas"])
            # Role-based fixture IDs are local to the pure simulator. Persisted
            # identities must be unique across projects and users.
            identities = {p["id"]: f"{project_id}:{p['id']}" for p in personas}
            for persona in personas:
                persona["id"] = identities[persona["id"]]
                persona["relationships"] = [identities.get(target, target) for target in persona["relationships"]]
        if not personas:
            raise StageConflict("Tidak ada kandidat baru; tambah persona manual bila diperlukan")
        self.repository.add_personas(project_id, owner, expected_revision, personas)
        return self.repository.project(project_id, owner)

    def add_persona(self, project_id, owner, payload, expected_revision):
        value = Persona.model_validate(payload).model_dump(mode="json")
        value.update(id=uid("persona"), revision=1, provenance={"profile": "user_supplied_assumption"}, relationships=[])
        self.repository.add_personas(project_id, owner, expected_revision, [value])
        return value

    def analysis_options(self, payload, schema):
        options = dict(payload)
        if options.get("engine", "oasis") == "oasis" and urlsplit(self.settings.llm_base_url or "").hostname in {"openrouter.ai", "api.openai.com"}:
            options.setdefault("max_seconds", 900)
            options.setdefault("max_tokens", 300000)
        if options.get("engine", "oasis") == "oasis" and urlsplit(self.settings.llm_base_url or "").hostname == "api.groq.com":
            # Free-tier throttling needs time to wait. Explicit smaller user
            # limits remain authoritative; fixture/other-provider defaults stay.
            options.setdefault("max_seconds", 900)
            options.setdefault("max_tokens", 180000)
        return schema.model_validate(options).model_dump(mode="json")

    def start(self, project_id, owner, payload, key=None):
        config = self.analysis_options(payload, AnalysisInput)
        project = self.repository.project(project_id, owner)
        if project["revision"] != config["expected_revision"]:
            raise RevisionConflict()
        if not project["claims"] or any(c["review_status"] == "pending" for c in project["claims"]):
            raise StageConflict("Review seluruh claim: setujui atau tolak sebelum analisis")
        included_documents = {d["id"] for d in project["documents"] if d["status"] == "ready"}
        claims = [c for c in project["claims"] if c["review_status"] == "approved" and c["source"]["document_id"] in included_documents]
        if not claims:
            raise StageConflict("Analisis membutuhkan minimal satu claim yang disetujui")
        if any(d["status"] not in {"ready", "excluded"} for d in project["documents"]):
            raise StageConflict("Ada dokumen yang belum dapat dibaca; perbaiki sumber sebelum analisis")
        personas = [p for p in project["personas"] if p["active"]]
        if not 2 <= len(personas) <= config["max_personas"] or any(not p["reviewed"] for p in personas):
            raise StageConflict("Review minimal dua persona aktif; jumlahnya harus sesuai batas konfigurasi")
        values, references = financial_inputs(claims)
        if config["engine"] == "oasis" and not self.capabilities()["oasis_available"]:
            raise StageConflict("Runtime OASIS/LLM belum tersedia; konfigurasi layanan atau pilih fixture berlabel")
        if config["engine"] == "fixture" and project["context"]["data_classification"] != "synthetic":
            raise StageConflict("Engine fixture hanya untuk proyek berklasifikasi data sintetis")
        snapshot = {"context": project["context"], "revision": project["revision"], "claims": claims, "personas": personas, "values": values, "value_claim_ids": references, "config": config, "documents": [{"id": d["id"], "name": d["name"]} for d in project["documents"] if d["status"] == "ready"], "prompt_version": "pakar-1.2", "review_policy": PAIRED_POLICY, "model": self.settings.llm_model if config["engine"] == "oasis" else None, "limitations": ["Persona adalah perspektif sintetis, bukan sampel opini pasar.", "Provenance persona tidak memverifikasi perilaku yang dihasilkan.", "Sumber eksternal dapat tidak tersedia atau belum cocok dengan klaim."]}
        snapshot["response_mode"] = "json_schema" if self.settings.llm_structured_outputs else "json_object"
        snapshot["interaction_policy"] = "swarm-v1" if config.get("interaction_mode") == "swarm" else "pairwise-v1"
        if reactive(config):
            snapshot.update(interaction_policy="reactive-v2", prompt_version="pakar-1.7" if config.get("document_grounding") and config.get("compact_dialogue") else "pakar-1.6" if config.get("choice_dialogue") and config.get("compact_dialogue") else "pakar-1.5" if config.get("compact_dialogue") else "pakar-1.4" if config.get("business_system_prompt") else "pakar-1.3")
        if config["engine"] == "oasis" and len(config["public_brief"].strip()) < 20:
            raise ApiError(422, "public_brief_required", "Isi brief untuk stakeholder minimal 20 karakter. Dokumen dan ide lengkap hanya digunakan agent internal.")
        freeze_information(snapshot, config["public_brief"])
        row = self.repository.enqueue(project_id, owner, snapshot, key)
        self._spawn(row)
        return row

    def quick_start(self, project_id, owner, payload, key=None):
        config = self.analysis_options(payload, QuickAnalysisInput)
        previous = self.repository.keyed_analysis(project_id, owner, key)
        if previous:
            if previous["input_snapshot"].get("input_mode") != "automatic-v1" or previous["input_snapshot"]["config"] != config:
                raise StageConflict("Permintaan ini sudah digunakan untuk konfigurasi berbeda")
            return previous
        project = self.repository.project(project_id, owner)
        if project["revision"] != config["expected_revision"]:
            raise RevisionConflict()
        selected_idea = self.conversation.repository.revision(project_id, config["idea_revision_id"], owner) if config["idea_revision_id"] else None
        selected_documents = [d for d in project["documents"] if d["content"].get("purpose", "evidence") != "idea" or (selected_idea and d["id"] in selected_idea["content"]["document_ids"])]
        if any(d["status"] not in {"ready", "excluded"} for d in selected_documents) or (not selected_documents and not selected_idea):
            raise StageConflict("Dokumen belum dapat dibaca. Gunakan PDF berisi teks, DOCX, TXT atau Markdown; PDF scan memerlukan OCR.")
        documents = [d for d in selected_documents if d["status"] == "ready"]
        if selected_idea and not set(selected_idea["content"]["document_ids"]) <= {d["id"] for d in documents}:
            raise StageConflict("Dokumen ide terpilih tidak lagi tersedia; simpan revisi baru tanpa dokumen tersebut")
        from .idea_inputs import idea_claims, public_idea
        proposed_claims = idea_claims(selected_idea) if selected_idea else []
        claims, values, references, issues = automatic_inputs([*proposed_claims, *[c for c in project["claims"] if c["source"]["document_id"] in {d["id"] for d in documents}]])
        if not claims:
            raise StageConflict("Dokumen belum menghasilkan teks untuk dianalisis")
        if config["engine"] == "oasis" and not self.capabilities()["oasis_available"]:
            raise ApiError(503, "analysis_unavailable", "Model atau runtime belum tersedia. Periksa konfigurasi layanan, atau gunakan contoh sintetis dengan mode demo.")
        if config["engine"] == "fixture" and project["context"]["data_classification"] != "synthetic":
            raise StageConflict("Demo tanpa model hanya tersedia untuk data sintetis")
        snapshot = {"context": project["context"], "revision": project["revision"], "claims": claims, "personas": [], "values": values, "value_claim_ids": references, "config": config,
                    "documents": [{"id": d["id"], "name": d["name"]} for d in documents], "prompt_version": "pakar-1.2", "review_policy": PAIRED_POLICY,
                    "model": self.settings.llm_model if config["engine"] == "oasis" else None, "response_mode": "json_schema" if self.settings.llm_structured_outputs else "json_object",
                    "input_mode": "automatic-v1", "preparation": {"status": "pending"},
                    "limitations": ["Input diterima otomatis sebagai asumsi dari dokumen, bukan hasil review manusia atau verifikasi fakta.", "Persona dibuat otomatis sebagai perspektif sintetis; profil dan perilakunya belum dikonfirmasi oleh stakeholder nyata.", *issues]}
        snapshot["interaction_policy"] = "swarm-v1" if config.get("interaction_mode") == "swarm" else "pairwise-v1"
        if selected_idea:
            snapshot["idea"] = public_idea(selected_idea)
            snapshot["documents"].append({"id": selected_idea["id"], "name": f"Usulan pengguna: {selected_idea['content']['title']} · versi {selected_idea['version']}"})
            snapshot["limitations"].append("Ide dan penjelasan chat yang dipilih adalah usulan/asumsi pengguna, bukan fakta terverifikasi. Run ini memakai versi ide yang dibekukan; perubahan berikutnya memerlukan run terpisah.")
        if reactive(config):
            snapshot.update(interaction_policy="reactive-v2", prompt_version="pakar-1.7" if config.get("document_grounding") and config.get("compact_dialogue") else "pakar-1.6" if config.get("choice_dialogue") and config.get("compact_dialogue") else "pakar-1.5" if config.get("compact_dialogue") else "pakar-1.4" if config.get("business_system_prompt") else "pakar-1.3")
        if config["engine"] == "oasis" and len(config["public_brief"].strip()) < 20:
            raise ApiError(422, "public_brief_required", "Isi brief untuk stakeholder minimal 20 karakter. Dokumen dan ide lengkap hanya digunakan agent internal.")
        freeze_information(snapshot, config["public_brief"])
        row = self.repository.enqueue(project_id, owner, snapshot, key)
        self._spawn(row)
        return row

    def scenario(self, baseline_id, owner, shock, key=None):
        baseline = self.analysis_view(baseline_id, owner)
        if baseline["input_snapshot"]["config"]["engine"] == "oasis" and not information_scoped(baseline["input_snapshot"]):
            raise StageConflict("Run lama belum memisahkan pengetahuan stakeholder. Buat baseline baru dengan brief stakeholder sebelum menjalankan scenario AI.")
        if baseline["status"] not in {"completed", "partial"} or not baseline["result"].get("simulation"):
            raise StageConflict("Selesaikan baseline sebelum membuat scenario")
        if baseline["baseline_id"]:
            raise StageConflict("Pilih baseline awal untuk membuat perbandingan scenario")
        snapshot = deepcopy(baseline["input_snapshot"])
        if snapshot["config"]["engine"] == "oasis":
            if snapshot.get("model") != self.settings.llm_model:
                snapshot["limitations"] = [*snapshot.get("limitations", []), "Model scenario berbeda dari baseline; perbedaan hasil juga dapat dipengaruhi pergantian model."]
            snapshot["model"] = self.settings.llm_model
            snapshot["response_mode"] = "json_schema" if self.settings.llm_structured_outputs else "json_object"
        # A scenario must run its changed conditions, never reuse a review seed.
        snapshot.pop("review_source", None)
        snapshot.pop("review_roles", None)
        if shock["effective_round"] > snapshot["config"]["rounds"]:
            raise StageConflict("Ronde shock harus berada dalam batas simulasi")
        if shock["region"].casefold() != snapshot["context"]["region"].casefold():
            raise StageConflict("Wilayah shock harus sesuai wilayah baseline MVP")
        snapshot["shock"] = shock
        row = self.repository.enqueue(baseline["project_id"], owner, snapshot, key, baseline_id)
        self._spawn(row)
        return row

    def continue_specialists(self, source_id, owner, payload, key):
        options = SpecialistReviewInput.model_validate(payload).model_dump(mode="json")
        retry_failed = options.pop("retry_failed")
        recover_cancelled = options.pop("recover_cancelled")
        if recover_cancelled and retry_failed:
            raise StageConflict("Pilih pemulihan diskusi atau retry reviewer, bukan keduanya")
        source = self.analysis_view(source_id, owner)
        interrupted_review = bool(retry_failed and source["status"] == "failed" and source["input_snapshot"].get("review_source") and not source["result"].get("simulation"))
        if interrupted_review:
            frozen = source["input_snapshot"]["review_source"]
            original = self.repository.analysis(frozen["analysis_id"], owner)
            digest = hashlib.sha256(json.dumps(original["result"], sort_keys=True).encode()).hexdigest()
            if digest != frozen["result_sha256"] or not frozen.get("simulation", {}).get("events"):
                raise StageConflict("Diskusi sumber berubah atau tidak tersedia; review tidak dijalankan")
            # Explicit retry of an interrupted review recovers only its frozen
            # discussion. Never mark the failed run complete or replay personas.
            source = dict(source, status="partial", result={"simulation": deepcopy(frozen["simulation"]), "evidence": deepcopy(frozen.get("evidence", [])), "agent_runs": deepcopy(frozen.get("retained_runs", [])), "findings": deepcopy(frozen.get("retained_findings", []))})
        previous = self.repository.keyed_analysis(source["project_id"], owner, key)
        if previous:
            frozen = previous["input_snapshot"]
            if frozen.get("review_source", {}).get("analysis_id") != source_id or frozen.get("review_source", {}).get("retry_failed", False) != retry_failed or frozen.get("review_source", {}).get("recovered_cancelled", False) != recover_cancelled or any(frozen["config"].get(k, "0.01" if k == "max_cost_usd" else None) != v for k, v in options.items()):
                raise StageConflict("Permintaan review sudah dipakai untuk input berbeda")
            return previous
        recovered_events_hash = None
        if recover_cancelled:
            if source["status"] != "cancelled" or source["result"].get("simulation") or source["input_snapshot"].get("config", {}).get("engine") != "oasis":
                raise StageConflict("Pemulihan eksplisit memerlukan diskusi AI dibatalkan yang belum memiliki hasil simulasi")
            events, calls = self.repository.cancelled_discussion_records(source_id)
            if not events:
                raise StageConflict("Tidak ada diskusi tersimpan untuk dipulihkan")
            simulation = replay_committed(source["input_snapshot"], events, calls, stop_reason="cancelled_source")
            recovered_events_hash = hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest()
            source = dict(source, status="partial", result={"simulation": simulation, "evidence": [], "agent_runs": []})
        if source["status"] != "partial" or source["input_snapshot"]["config"]["engine"] != "oasis" or not source["result"].get("simulation", {}).get("events"):
            raise StageConflict("Review lanjutan membutuhkan run AI parsial dengan interaksi tersimpan")
        if source["baseline_id"] or (source["input_snapshot"].get("review_source") and not retry_failed):
            raise StageConflict("Pilih run awal untuk review lanjutan")
        if not retry_failed and any(c.get("phase") in {"specialist", "inherited_specialist"} for c in source["result"].get("agent_runs", [])):
            raise StageConflict("Review specialist sudah pernah dimulai; review lanjutan ini hanya untuk run yang belum direview AI")
        if not self.settings.llm_api_key or source["input_snapshot"].get("model") != self.settings.llm_model:
            raise StageConflict("Provider/model harus tersedia dan sama dengan run asal")
        snapshot = deepcopy(source["input_snapshot"])
        snapshot["config"].update(options)
        snapshot["review_policy"] = PAIRED_POLICY
        snapshot["review_source"] = {"analysis_id": source_id, "result_sha256": hashlib.sha256(json.dumps(self.repository.analysis(source_id, owner)["result"], sort_keys=True).encode()).hexdigest(),
                                   "simulation": deepcopy(source["result"]["simulation"]), "evidence": deepcopy(source["result"].get("evidence", []))}
        if interrupted_review:
            snapshot["review_source"].update(interrupted_review=True, original_execution_status="failed")
            snapshot["limitations"].append("Review asal terputus. Kelanjutan memakai diskusi yang dibekukan tanpa giliran persona baru; biaya panggilan review yang tidak sempat tercatat tetap unknown.")
        if recover_cancelled:
            snapshot["review_source"].update(recovered_cancelled=True, committed_events_sha256=recovered_events_hash,
                original_execution_status="cancelled", evidence_recovery="unavailable_from_cancelled_result")
            snapshot["limitations"].append("Run asal tetap dibatalkan. Diskusi dipulihkan secara eksplisit dari event tervalidasi tanpa giliran stakeholder baru; review specialist pada run baru berbayar. Evidence eksternal yang tidak tersimpan saat pembatalan tidak dipulihkan atau diambil ulang. Usage sumber yang belum lengkap tetap unknown.")
        if retry_failed:
            entries = source["result"].get("agent_runs", [])
            failed_roles = {entry["role"] for entry in entries if entry.get("status") == "failed"}
            retained = [deepcopy(entry) for entry in entries if entry.get("phase") in {"specialist", "inherited_specialist"} and entry.get("status") == "completed" and entry["role"] not in failed_roles]
            retained_roles = {entry["role"] for entry in retained}
            snapshot["review_roles"] = [role for role in ROLES if role not in retained_roles]
            if not snapshot["review_roles"]:
                raise StageConflict("Semua specialist sudah menyelesaikan review; tidak ada panggilan yang perlu dilanjutkan")
            template_ids = {finding["id"] for finding in structured_findings(snapshot, source["result"]["simulation"], source["result"].get("evidence", []))}
            for entry in retained:
                entry.update(phase="inherited_specialist", source_analysis_id=source_id, execution_kind="inherited_specialist_review")
            snapshot["review_source"].update(retry_failed=True, retained_runs=retained,
                retained_findings=[deepcopy(f) for f in source["result"].get("findings", []) if f["id"] not in template_ids and f["author"] in retained_roles],
                retained_disagreements=[deepcopy(d) for d in source["result"].get("disagreements", []) if d["author"] in retained_roles])
        snapshot["limitations"] = [*snapshot.get("limitations", []), "Review lanjutan memakai diskusi dan evidence yang dibekukan dari run asal, tanpa mengulang simulasi atau mengambil evidence baru."]
        if source["result"]["simulation"]["stop_reason"] not in {"round_limit", "discussion_quiet"}:
            snapshot["limitations"].append("Diskusi asal tetap tidak lengkap.")
        row = self.repository.enqueue(source["project_id"], owner, snapshot, key, frozen_source_id=source_id)
        self._spawn(row)
        return row

    def _spawn(self, row):
        if self.settings.embedded_worker and self.spawn and row.get("job_id"):
            self.spawn(row["job_id"])

    def execute(self, job, worker_id):
        stop = threading.Event()
        lease_lost = threading.Event()

        def heartbeat():
            while not stop.wait(max(1, min(10, self.settings.worker_lease_seconds / 3))):
                if not self.shared.renew_job_lease(job["id"], worker_id, job["execution_token"], self.settings.worker_lease_seconds):
                    lease_lost.set()
                    break

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        result = {"findings": [], "agent_runs": [], "evidence": [], "disagreements": [], "limitations": []}
        llm = None
        spend_ledger = None
        try:
            row = self.repository.analysis(job["analysis_id"])
            if row["status"] in {"completed", "partial"} and row["result"].get("report"):
                self.shared.finish_job(job["id"], worker_id, job["execution_token"], {"analysis_id": row["id"]})
                return True
            snapshot = row["input_snapshot"]
            run_identity = f"{row['id']}:attempt:{job['lease_generation']}"
            started = time.monotonic()
            last_cancel_check = 0.0
            def cancelled():
                nonlocal last_cancel_check
                if lease_lost.is_set():
                    return True
                now = time.monotonic()
                if now - last_cancel_check >= 0.5:
                    last_cancel_check = now
                    if self.repository.analysis(row["id"])["status"] == "cancelled":
                        lease_lost.set()
                return lease_lost.is_set()

            deadline = RunDeadline(snapshot["config"]["max_seconds"], cancelled=cancelled)
            if snapshot["config"]["engine"] == "oasis":
                spend_ledger = SpendLedger.open(self.settings, self.shared.engine, f"analysis:{row['id']}", snapshot["config"].get("max_cost_usd", ".10"), timeout=min(10, deadline.remaining()), cancelled=cancelled)
            spending = spend_ledger.budget if spend_ledger else None
            attempt_token_budget = snapshot["config"]["max_tokens"] // job["max_attempts"]
            attempt_total_cap = attempt_token_budget

            def publish(stage, payload):
                self.repository.publish(job, worker_id, stage, payload)

            if snapshot.get("preparation", {}).get("status") == "pending":
                publish("preparing", {"message": "Membaca konteks dokumen dan membuat persona otomatis"})
                generated = None
                discovery_failure = None
                if snapshot["config"]["engine"] == "oasis":
                    discovery = BusinessLLM(self.settings, min(18000, attempt_token_budget // 4), min(25, deadline.remaining()), response_mode=snapshot["response_mode"], cancelled=cancelled, attempt=job["attempts"], prompt_version=snapshot["prompt_version"], provider_sort="latency", spending=spending)
                    try:
                        role_limit = min(6, snapshot["config"]["max_personas"] - snapshot["config"]["customer_count"] + 1) if snapshot["config"].get("interaction_mode") == "swarm" else snapshot["config"]["max_personas"]
                        generated = discovery.discover(snapshot["context"], snapshot["claims"], [], limit=role_limit, call_seconds=min(25, deadline.remaining()))
                    except RunCancelled:
                        raise
                    except Exception as error:
                        discovery_failure = type(error).__name__
                        logger.warning("business_discovery_fallback analysis=%s type=%s", row["id"], discovery_failure)
                    finally:
                        result["preparation_calls"] = discovery.calls
                deadline.remaining()
                generator = "llm-contextual-v3" if generated else "document-context-v1"
                if not generated:
                    role_limit = snapshot["config"]["max_personas"] - snapshot["config"]["customer_count"] + 1 if snapshot["config"].get("interaction_mode") == "swarm" else snapshot["config"]["max_personas"]
                    generated = contextual_personas(snapshot["context"], snapshot["claims"], role_limit)
                if snapshot["config"].get("interaction_mode") == "swarm":
                    generated = expand_customer_cohort(generated, snapshot["config"]["customer_count"], snapshot["config"]["max_personas"])
                snapshot = deepcopy(snapshot)
                snapshot["personas"] = generated
                bind_personas(snapshot)
                generated = snapshot["personas"]
                snapshot["preparation"] = {"status": "completed", "generator": generator, "human_reviewed": False, "discovery_failure_type": discovery_failure}
                if discovery_failure:
                    snapshot["limitations"].append("Discovery AI tidak selesai/valid; persona memakai peran yang diturunkan dari konteks dokumen. Ini bukan hasil discovery LLM dan belum direview manusia.")
                self.repository.publish(job, worker_id, "personas_ready", {"message": f"{len(generated)} persona otomatis siap; analisis dilanjutkan", "generator": generator}, prepared_snapshot=snapshot)
                # Discovery and simulation/review share the original token cap.
                attempt_token_budget = max(0, attempt_token_budget - sum(c["reserved_tokens_upper_bound"] if c.get("tokens") is None else c["tokens"] for c in result.get("preparation_calls", [])))

            source = snapshot.get("review_source")
            publish("evidence", {"message": "Memakai evidence yang dibekukan dari run asal" if source else "Mengambil evidence resmi sesuai wilayah; ketidaktersediaan ditampilkan eksplisit"})
            if source:
                evidence = deepcopy(source["evidence"])
            elif snapshot["config"]["engine"] == "oasis":
                evidence = self.evidence.retrieve(snapshot["context"]["region"], deadline=deadline, cancelled=cancelled)
            else:
                evidence = [{"id": "fixture-evidence-unavailable", "origin": "fixture", "status": "UNAVAILABLE", "url": None, "value": None, "reason": "Fixture tidak mengambil data resmi live"}]
            result["evidence"] = evidence
            publish("simulation", {"message": "Memakai diskusi tersimpan tanpa giliran persona baru" if source else "Menjalankan persona dengan state dan informasi yang dibatasi", "engine": snapshot["config"]["engine"]})
            if source:
                simulation = deepcopy(source["simulation"])
                result["continuation"] = {"source_analysis_id": source["analysis_id"], "source_result_sha256": source["result_sha256"], "simulation_reused": True, "usage_scope": "new_specialist_calls_only"}
                result["agent_runs"].extend(deepcopy(source.get("retained_runs", [])))
                result["disagreements"].extend(deepcopy(source.get("retained_disagreements", [])))
                publish("validation", {"message": "Memakai diskusi tersimpan; menjalankan empat specialist tanpa mengulang percakapan"})
            elif snapshot["config"]["engine"] == "oasis":
                if self.oasis is None:
                    raise ValueError("Runtime OASIS tidak tersedia pada worker")

                def receive(message):
                    if message["kind"] == "novelty":
                        result.setdefault("novelty_checks", []).append(deepcopy(message["check"]))
                    if message["kind"] == "interaction":
                        committed_events.append(deepcopy(message["event"]))
                    if message["kind"] == "usage":
                        calls = result.setdefault("runtime_calls", [])
                        previous = next((i for i, call in enumerate(calls) if call["call_id"] == message["call"]["call_id"]), None)
                        if previous is None:
                            calls.append(message["call"])
                        else:
                            calls[previous] = message["call"]
                    publish("interaction" if message["kind"] == "interaction" else "simulation", message)

                runtime_snapshot = deepcopy(snapshot)
                committed_events = []
                runtime_snapshot["config"]["max_seconds"] = deadline.remaining()
                if snapshot.get("review_policy") == PAIRED_POLICY:
                    review_reserve = min(120.0, runtime_snapshot["config"]["max_seconds"] * 0.4)
                    runtime_snapshot["config"]["max_seconds"] -= review_reserve
                    result["review_budget_reserved_seconds"] = round(review_reserve, 3)
                # Keep a separate share for the specialist review phase.
                runtime_snapshot["config"]["max_tokens"] = int(attempt_token_budget * 0.65)
                runtime_snapshot["config"]["attempt"] = job["attempts"]
                phase_reservation = None
                if spending:
                    phase_limit = spending.remaining * Decimal('.65')
                    phase_reservation = spending.reserve_amount(phase_limit)
                    runtime_snapshot["config"]["spending"] = {"limit_usd": str(phase_limit), "prices": {k: str(v) for k, v in spending.prices.items()}}
                try:
                    simulation = self.oasis.run_business_simulation(run_identity, runtime_snapshot, receive, cancelled=cancelled)
                    if phase_reservation:
                        charged = simulation.get("usage", {}).get("spending", {}).get("charged_or_reserved_usd")
                        spending.settle(phase_reservation, charged)
                except (BudgetExceeded, ProviderResponseError, ProviderTransportError) as error:
                    if not committed_events or cancelled():
                        raise
                    reason = "runtime_time_budget" if isinstance(error, BudgetExceeded) else "runtime_provider_failure"
                    simulation = replay_committed(snapshot, committed_events, result.get("runtime_calls", []), stop_reason=reason, reserved_token_cap=runtime_snapshot["config"]["max_tokens"])
                    result["runtime_recovery"] = simulation["recovery"]
                    publish("simulation", {"message": "Diskusi berhenti sebelum seluruh giliran selesai; interaksi tersimpan dipulihkan untuk laporan parsial"})
            else:
                simulation = self._fixture_simulation(run_identity, snapshot, publish)
            result["simulation"] = simulation
            publish("validation", {"message": "Memeriksa hipotesis interaksi, unit economics dan evidence gaps"})
            findings = structured_findings(snapshot, simulation, evidence)
            if source:
                findings.extend(deepcopy(source.get("retained_findings", [])))
            for finding in findings:
                validate_finding_references(finding, snapshot, simulation, evidence)
            for role in ("Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent"):
                result["agent_runs"].append({"role": role, "status": "completed", "execution_kind": "deterministic_checks", "finding_ids": [f["id"] for f in findings if f["author"] == role], "tools": ["typed_decimal_calculator"] if role == "Finance Agent" else ["scoped_registry_read"], "tokens": 0, "cost": None})
            failures = []
            if snapshot["config"]["engine"] == "oasis":
                budget_remaining = attempt_token_budget if source else max(0, attempt_token_budget - simulation.get("usage", {}).get("reserved_tokens_upper_bound", 0))
                llm = BusinessLLM(self.settings, budget_remaining, max(0, deadline.expires - deadline.finalization_reserve - time.monotonic()), response_mode=snapshot.get("response_mode"), cancelled=cancelled, attempt=job["attempts"], prompt_version=snapshot["prompt_version"], provider_sort="latency" if snapshot.get("review_policy") == PAIRED_POLICY else None, spending=spending)
                if snapshot.get("review_policy") == PAIRED_POLICY:
                    review = run_paired_reviews(llm, snapshot, simulation, evidence, findings, deadline.remaining, cancelled)
                    failures.extend(review["failures"])
                    result["disagreements"].extend(review["disagreements"])
                    result["review_execution"] = {"policy": PAIRED_POLICY, "concurrency": snapshot["config"].get("review_concurrency", 2), "provider_sort": "latency", "waves": review["waves"]}
                else:
                    for role in ("Market Agent", "Finance Agent", "Legal/Compliance Agent", "Risk Agent"):
                        try:
                            deadline.remaining()
                            schema = review_schema(role, snapshot, simulation, evidence)
                            output = llm.generate(role, "Review your domain. Return {findings: [...], disagreements: [strings]}, with at most TWO concise findings (or none if you have no additional finding). Findings must match finding_schema, copy your role exactly as author, use existing IDs only, status NEEDS_VALIDATION, and explicitly retain uncertainty. For an unsupported reference leave its array empty and describe an evidence gap; never invent IDs. Do not reproduce template findings. For any peer disagreement, preserve both conclusions. Legal output is questions for qualified review.", {"role": role, "context": snapshot["context"], "claims": snapshot["claims"][:35], "evidence": evidence, "events": simulation["events"][-12:], "personas": [{"id": p["id"], "role": p["role"]} for p in snapshot["personas"]], "calculation": simulation["calculation"], "peer_findings": findings[-12:], "finding_schema": schema["properties"]["findings"]["items"]}, response_schema=schema)
                            proposed = output.get("findings")
                            if not isinstance(proposed, list) or len(proposed) > 8:
                                raise ValueError("Specialist harus menghasilkan maksimal delapan finding")
                            validated = []
                            for raw in proposed:
                                finding = Finding.model_validate(raw).model_dump(mode="json")
                                if finding["author"] != role:
                                    raise ValueError("Author finding tidak sesuai role")
                                finding["id"] = f"finding-{len(findings) + len(validated) + 1}"
                                validated.append(validate_finding_references(finding, snapshot, simulation, evidence))
                            findings.extend(validated)
                            disagreements = output.get("disagreements", [])
                            if not isinstance(disagreements, list) or any(not isinstance(d, str) or len(d) > 2000 for d in disagreements):
                                raise ValueError("Kontrak disagreement tidak valid")
                            result["disagreements"].extend({"author": role, "summary": d} for d in disagreements[:8])
                        except RunCancelled:
                            raise
                        except Exception as error:
                            failures.append({"role": role, "status": "failed", "message": "Review specialist gagal atau budget tercapai; pemeriksaan deterministik tetap tersedia"})
                            logger.warning("business_specialist_failed analysis=%s role=%s type=%s", row["id"], role, type(error).__name__)
                result["agent_runs"].extend(llm.calls)
                result["agent_runs"].extend(failures)
                costs = [call["cost"] for call in llm.calls]
                result["specialist_usage"] = {"accounted_tokens": llm.tokens, "cost": sum(costs) if costs and all(isinstance(cost, (int, float)) for cost in costs) else None}
                result["usage"] = summarize_calls([*result.get("preparation_calls", []), *result.get("runtime_calls", []), *llm.calls])
                if spending:
                    result["usage"]["spending"] = spending.summary()
            # Exact duplicates merge only when source/category/next action agree.
            seen = set()
            result["findings"] = []
            for finding in findings:
                signature = (finding["title"].casefold(), finding["category"], tuple(sorted(finding["event_ids"])), finding["status"])
                if signature not in seen:
                    result["findings"].append(finding)
                    seen.add(signature)
            result["limitations"] = snapshot["limitations"] + (["Mode fixture: respons persona dan pemeriksaan adalah demonstrasi deterministik, bukan simulasi LLM live."] if snapshot["config"]["engine"] == "fixture" else [])
            if spending:
                result["limitations"].append(f"Plafon AI run USD {spending.limit}; biaya terlapor atau reservasi konservatif USD {spending.charged}. Biaya yang belum dilaporkan bukan nol.")
            if simulation["stop_reason"] not in {"round_limit", "discussion_quiet"}:
                result["limitations"].append("Diskusi berhenti sebelum seluruh giliran selesai karena batas runtime/provider. Laporan parsial hanya memakai interaksi yang benar-benar diterima; tidak ada retry live otomatis.")
            if simulation.get("recovery"):
                result["limitations"].append("Diskusi tidak menyelesaikan seluruh giliran. State dipulihkan dari event tervalidasi; tidak ada respons AI baru yang dibuat saat pemulihan.")
            discussion_quality = simulation.get("discussion_quality", {})
            if discussion_quality.get("warnings"):
                result["limitations"].extend(discussion_quality["warnings"])
                result["limitations"].append(discussion_quality["notice"])
            if failures:
                result["limitations"].append("Sebagian specialist tidak menyelesaikan review; hasil berstatus partial.")
            rejected_actions = sum(e["kind"] == "action_rejected" for e in simulation["events"])
            result["action_validation"] = {"rejected": rejected_actions, "accepted": sum(e["kind"] not in {"action_rejected", "shock", "shock_expired"} for e in simulation["events"])}
            if rejected_actions:
                result["limitations"].append("Sebagian aksi persona ditolak validator tanpa mengubah state; hasil berstatus partial.")
            if all(e["status"] == "UNAVAILABLE" for e in evidence):
                result["limitations"].append("Tidak ada evidence eksternal yang berhasil divalidasi pada run ini.")
            if any(e["status"] == "CONFLICTING" for e in evidence):
                result["limitations"].append("Angka sumber resmi belum selaras dengan publikasi pembanding; konflik disimpan dan nilai tidak digunakan sebagai angka tervalidasi.")
            result["elapsed_seconds"] = round(time.monotonic() - started, 3)
            result["budget"] = {"analysis_token_cap": snapshot["config"]["max_tokens"], "attempt_token_cap": attempt_total_cap, "after_preparation_token_cap": attempt_token_budget, "attempt": job["attempts"], "max_attempts": job["max_attempts"]}
            result["budget"].update(max_seconds=deadline.seconds, finalization_reserve_seconds=deadline.finalization_reserve,
                                   work_deadline_reached=time.monotonic() >= deadline.expires - deadline.finalization_reserve,
                                   deadline_exceeded=time.monotonic() > deadline.expires)
            result["provenance"] = {"engine": snapshot["config"]["engine"], "prompt_version": snapshot["prompt_version"], "input_revision": snapshot["revision"], "model": snapshot["model"], "seed": snapshot["config"]["seed"], "execution_kind": "fixture" if snapshot["config"]["engine"] == "fixture" else "oasis_business_adapter", "scenario_semantics": "separate_run_scheduled_shock"}
            result["provenance"]["review_policy"] = snapshot.get("review_policy", "sequential-v1")
            result["provenance"]["interaction_policy"] = snapshot.get("interaction_policy", "pairwise-v1")
            if source:
                result["provenance"].update(execution_kind="specialist_review_continuation", source_analysis_id=source["analysis_id"], source_result_sha256=source["result_sha256"], usage_scope="new_specialist_calls_only")
                result["provenance"]["inherited_specialist_roles"] = [entry["role"] for entry in source.get("retained_runs", [])]
            if snapshot.get("input_mode"):
                result["provenance"].update(input_mode=snapshot["input_mode"], persona_generator=snapshot["preparation"]["generator"], human_reviewed=False)
            result["provenance"]["response_mode"] = simulation.get("response_mode", snapshot.get("response_mode", "json_object"))
            partial = bool(failures) or simulation["stop_reason"] not in {"round_limit", "discussion_quiet"} or bool(rejected_actions) or not result["action_validation"]["accepted"]
            partial = partial or (snapshot["config"]["engine"] == "oasis" and discussion_quality.get("limited_exchange", False))
            baseline = self.repository.analysis(row["baseline_id"]) if row["baseline_id"] else None
            report = self.report(snapshot, result, analysis_id=row["id"], baseline=baseline, status="partial" if partial else "completed", created_at=row["created_at"])
            # Keep the polling response small. The authenticated report endpoint
            # expands the immutable registry into its full readable projection.
            result["report"] = {key: report[key] for key in ("version", "title", "analysis_id", "status", "created_at", "sections", "summary")}
            publish("report", {"message": "Laporan disusun dari finding registry tervalidasi"})
            self.repository.publish(job, worker_id, "completed", {"message": "Analisis selesai dengan batas ketidakpastian yang tercatat"}, result=result, status="partial" if partial else "completed")
            if not self.shared.finish_job(job["id"], worker_id, job["execution_token"], {"analysis_id": row["id"]}):
                raise RuntimeError("Lease lost before job completion")
        except Exception as error:
            retry = job["attempts"] < job["max_attempts"] and not isinstance(error, (ValueError, ApiError)) and locals().get("snapshot", {}).get("config", {}).get("engine") != "oasis"
            try:
                result["usage"] = summarize_calls([*result.get("preparation_calls", []), *result.get("runtime_calls", []), *(llm.calls if llm else [])])
                if spend_ledger:
                    result["usage"]["spending"] = spend_ledger.budget.summary()
                result["stop_reason"] = "dollar_budget" if isinstance(error, SpendingLimit) else "time_budget" if isinstance(error, BudgetExceeded) else "cancelled" if isinstance(error, RunCancelled) else "external_failure"
                if "started" in locals():
                    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
                result["error"] = "Analisis gagal. Konfigurasi runtime, sumber data atau provider perlu diperiksa; tidak ada hasil yang dianggap terverifikasi."
                if isinstance(error, SpendingLimit):
                    result["error"] = str(error)
                elif isinstance(error, BudgetExceeded):
                    result["error"] = "Analisis dihentikan karena batas waktu tercapai. Event yang sudah tercatat tetap dapat diperiksa; tidak ada retry live otomatis."
                self.repository.publish(job, worker_id, "failed", {"message": result["error"]}, result=result, status="queued" if retry else "failed")
            except RuntimeError:
                pass
            self.shared.fail_job(job["id"], worker_id, job["execution_token"], "Business analysis failed: " + type(error).__name__, retry_delay=2 if retry else None)
            logger.error("business_analysis_failed analysis=%s type=%s", job["analysis_id"], type(error).__name__, exc_info=True)
        finally:
            if spend_ledger:
                try:
                    spend_ledger.close()
                except Exception:
                    logger.error("spend_reservation_retained analysis=%s", job["analysis_id"])
            stop.set()
            thread.join(timeout=1)
        return True

    @staticmethod
    def _fixture_simulation(run_id, snapshot, publish):
        config = snapshot["config"]
        swarm = config.get("interaction_mode") == "swarm"
        active_dialogue = reactive(config)
        extra = {"strict_trigger_reply": config.get("strict_trigger_reply", False)} if active_dialogue else {}
        sim = (DialogueSimulation if active_dialogue else SwarmSimulation if swarm else BusinessSimulation)(run_id, snapshot["personas"], snapshot["values"], config["max_events"], **extra)
        if swarm:
            order = sim.turn_order()
        else:
            order = list(sim.personas)
            random.Random(config["seed"]).shuffle(order)
            order.sort(key=lambda key: {"supplier": 0, "operator": 1}.get(sim.personas[key].role, 2))
        stop_reason = "round_limit"
        for round_number in range(1, config["rounds"] + 1):
            round_start = len(sim.events)
            if len(sim.events) >= sim.max_events:
                stop_reason = "event_budget"
                break
            expired = sim.expire_shock(round_number)
            if expired:
                publish("interaction", {"event": expired})
            if snapshot.get("shock") and snapshot["shock"]["effective_round"] == round_number:
                publish("interaction", {"event": sim.inject(Shock.model_validate(snapshot["shock"]), round_number)})
            turns = ReactiveAgenda(sim, config.get("followups_per_round", 2)).turns(round_number) if active_dialogue else ({"actor_id": key} for key in order)
            for turn in turns:
                persona_id = turn["actor_id"]
                if len(sim.events) >= sim.max_events:
                    stop_reason = "event_budget"
                    break
                if active_dialogue:
                    sim.current_dispatch = turn
                action = swarm_fixture_action(sim, persona_id, round_number) if swarm else fixture_action(sim, persona_id)
                if active_dialogue:
                    action = DialogueAction(**action.model_dump(), dialogue_act="answer" if action.kind == "reply_message" else "abstain" if action.kind == "abstain" else "statement")
                if action:
                    publish("interaction", {"event": sim.apply(action, round_number)})
            if swarm and stop_reason == "round_limit" and is_quiet_round(sim, round_start, round_number, config["rounds"], snapshot.get("shock")):
                stop_reason = "discussion_quiet"
                break
        return sim.snapshot() | {"engine": "fixture", "stop_reason": stop_reason, "usage": {"actual_tokens": 0, "cost": "0", "cost_status": "fixture_no_model_calls"}}

    @staticmethod
    def report(snapshot, result, **metadata):
        return build_report(snapshot, result, **metadata)

    def comparison(self, analysis_id, owner):
        scenario = self.analysis_view(analysis_id, owner)
        if not scenario["baseline_id"]:
            raise StageConflict("Analisis ini belum merupakan scenario")
        baseline = self.analysis_view(scenario["baseline_id"], owner)
        if not scenario["result"].get("simulation") or not baseline["result"].get("simulation"):
            raise StageConflict("Tunggu kedua run selesai sebelum membandingkan")
        from decimal import Decimal
        before, after = (r["result"]["simulation"]["calculation"] for r in (baseline, scenario))
        metrics = []
        for key in ("contribution_margin", "break_even_units_monthly", "profit_monthly"):
            left, right = before[key], after[key]
            metrics.append({"metric": key, "before": left, "after": right, "delta": format(Decimal(right) - Decimal(left), "f") if left is not None and right is not None else None, "status": "COMPUTED_CONDITIONAL_ON_INPUTS" if left is not None and right is not None else "UNKNOWN"})
        def signature(f):
            return f["title"], f["category"]
        old = {signature(f): f for f in project_valid_findings(baseline["result"])["findings"]}
        new = {signature(f): f for f in project_valid_findings(scenario["result"])["findings"]}
        return {"baseline_id": baseline["id"], "scenario_id": scenario["id"], "metrics": metrics, "states_before": baseline["result"]["simulation"]["states"], "states_after": scenario["result"]["simulation"]["states"], "relationships_before": baseline["result"]["simulation"].get("relationships", []), "relationships_after": scenario["result"]["simulation"].get("relationships", []), "new_findings": [f for k, f in new.items() if k not in old], "shared_findings": [{"before": old[k], "after": new[k]} for k in sorted(old.keys() & new.keys())], "notice": "Perbandingan dua run sintetis; delta finansial mengikuti input dan strategi. Kesamaan judul finding tidak membuktikan risiko tetap sama."}

    def report_view(self, analysis_id, owner):
        row = self.analysis_view(analysis_id, owner)
        if not row["result"].get("report") or not row["result"].get("simulation"):
            raise StageConflict("Laporan belum tersedia")
        baseline = self.analysis_view(row["baseline_id"], owner) if row["baseline_id"] else None
        return build_report(row["input_snapshot"], row["result"], analysis_id=row["id"], baseline=baseline, status=row["status"], created_at=row["created_at"])

    def analysis_view(self, analysis_id, owner):
        row = self.repository.analysis(analysis_id, owner)
        row["review_followup"] = self.repository.review_followup(analysis_id)
        if row["status"] == "failed" and row["input_snapshot"].get("config", {}).get("engine") == "oasis" and row["result"].get("stop_reason") == "time_budget" and not row["result"].get("simulation"):
            events = self.repository.committed_interactions(row["id"])
            if events:
                try:
                    simulation = replay_committed(row["input_snapshot"], events, row["result"].get("runtime_calls", []))
                    result = deepcopy(row["result"])
                    result.pop("error", None)
                    result["simulation"] = simulation
                    result["recovery"] = {**simulation["recovery"], "original_execution_status": "failed", "specialist_review": "not_run", "raw_result_sha256": hashlib.sha256(json.dumps(row["result"], sort_keys=True).encode()).hexdigest()}
                    result["findings"] = structured_findings(row["input_snapshot"], simulation, result.get("evidence", []))
                    for finding in result["findings"]:
                        validate_finding_references(finding, row["input_snapshot"], simulation, result.get("evidence", []))
                    result["limitations"] = [*row["input_snapshot"].get("limitations", []), *result.get("limitations", []), "Run live berhenti karena batas waktu. Laporan parsial dipulihkan hanya dari event yang sudah tersimpan; tidak ada panggilan AI baru. Review specialist AI belum dijalankan; temuan memakai pemeriksaan deterministik atas input dan jejak aktual."]
                    snapshot = row["input_snapshot"]
                    result["provenance"] = {"execution_kind": "oasis_business_adapter", "engine": snapshot["config"]["engine"], "model": snapshot.get("model"), "prompt_version": snapshot.get("prompt_version"), "input_revision": snapshot["revision"], "seed": snapshot["config"]["seed"], "recovery": "validated_event_replay_v1", "specialist_review": "not_run"}
                    baseline = self.analysis_view(row["baseline_id"], owner) if row["baseline_id"] else None
                    report = build_report(snapshot, result, analysis_id=row["id"], baseline=baseline, status="partial", created_at=row["created_at"])
                    result["report"] = {k: report[k] for k in ("version", "title", "analysis_id", "status", "created_at", "sections", "summary")}
                    row = dict(row, result=result, status="partial", stage="completed")
                except (ValueError, KeyError, TypeError):
                    logger.warning("business_saved_recovery_invalid analysis=%s", row["id"])
        result = project_valid_findings(row["result"])
        if result is row["result"]:
            return row
        # The raw registry remains immutable. Counts/sections for publication
        # are derived by the report endpoint with the current validation policy.
        if result.get("report"):
            baseline = self.repository.analysis(row["baseline_id"], owner) if row["baseline_id"] else None
            report = build_report(row["input_snapshot"], result, analysis_id=row["id"], baseline=baseline, status=row["status"], created_at=row["created_at"])
            result["report"]["summary"] = report["summary"]
        return dict(row, result=result)

    def export(self, analysis_id, owner):
        return render_html(self.report_view(analysis_id, owner))
