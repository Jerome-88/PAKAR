from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, insert, select, update

from ..database import jobs, users
from ..errors import ResourceNotFound, RevisionConflict, StageConflict, UploadQuotaExceeded
from .tables import business_analyses, business_claims, business_documents, business_events, business_personas, business_projects


def utcnow():
    return datetime.now(timezone.utc)


def uid(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class BusinessRepository:
    def __init__(self, repository):
        self.shared = repository
        self.engine = repository.engine

    @staticmethod
    def require_project(db, project_id, owner, lock=False):
        statement = select(business_projects).where(business_projects.c.id == project_id, business_projects.c.owner_user_id == owner)
        if lock:
            statement = statement.with_for_update()
        row = db.execute(statement).mappings().one_or_none()
        if not row:
            raise ResourceNotFound()
        return dict(row)

    def create(self, owner, context, key=None, max_projects=100):
        with self.engine.begin() as db:
            db.execute(select(users.c.id).where(users.c.id == owner).with_for_update()).scalar_one()
            if key:
                existing = db.execute(select(business_projects).where(business_projects.c.owner_user_id == owner, business_projects.c.idempotency_key == key)).mappings().one_or_none()
                if existing:
                    if existing["context"] != context:
                        raise StageConflict("Idempotency key sudah dipakai untuk input berbeda")
                    return dict(existing)
            count = db.execute(select(func.count()).select_from(business_projects).where(business_projects.c.owner_user_id == owner)).scalar_one()
            if count >= max_projects:
                raise UploadQuotaExceeded("Batas proyek bisnis telah tercapai")
            row = {"id": uid("business"), "owner_user_id": owner, "context": context, "revision": 1, "created_at": utcnow(), "updated_at": utcnow(), "idempotency_key": key}
            db.execute(insert(business_projects).values(**row))
            return row

    def list_projects(self, owner, *, shared=False):
        with self.engine.connect() as db:
            statement = select(business_projects)
            if not shared:
                statement = statement.where(business_projects.c.owner_user_id == owner)
            projects = [dict(r) for r in db.execute(statement.order_by(business_projects.c.updated_at.desc())).mappings()]
            if not projects:
                return []
            project_ids = [row["id"] for row in projects]
            counts = {row["project_id"]: dict(row) for row in db.execute(select(
                business_analyses.c.project_id,
                func.count().label("analysis_count"),
                func.count().filter(business_analyses.c.status == "completed").label("completed_analysis_count"),
                func.count().filter(business_analyses.c.status.in_(["queued", "running"])).label("ongoing_analysis_count"),
            ).where(business_analyses.c.project_id.in_(project_ids)).group_by(business_analyses.c.project_id)).mappings()}
            latest = {row["project_id"]: dict(row) for row in db.execute(select(
                business_analyses.c.id, business_analyses.c.project_id, business_analyses.c.status,
                business_analyses.c.stage, business_analyses.c.created_at,
                business_analyses.c.result["findings"].label("findings"),
            ).where(business_analyses.c.project_id.in_(project_ids))
                .distinct(business_analyses.c.project_id)
                .order_by(business_analyses.c.project_id, business_analyses.c.created_at.desc(), business_analyses.c.id.desc())).mappings()}
            for project in projects:
                stats = counts.get(project["id"], {})
                for key in ("analysis_count", "completed_analysis_count", "ongoing_analysis_count"):
                    project[key] = stats.get(key, 0)
                run = latest.get(project["id"])
                if run is not None:
                    run["findings"] = run.get("findings") or []
                project["latest_analysis"] = run
                project["activity_at"] = max(project["updated_at"], run["created_at"]) if run else project["updated_at"]
            return sorted(projects, key=lambda row: row["activity_at"], reverse=True)

    def resource_owner(self, *, project_id=None, analysis_id=None):
        """Resolve persisted ownership in shared mode without rewriting old data."""
        statement = select(business_projects.c.owner_user_id)
        if project_id:
            statement = statement.where(business_projects.c.id == project_id)
        elif analysis_id:
            statement = statement.join(business_analyses).where(business_analyses.c.id == analysis_id)
        else:
            raise ValueError("A project or analysis is required")
        with self.engine.connect() as db:
            owner = db.execute(statement).scalar_one_or_none()
        if owner is None:
            raise ResourceNotFound()
        return owner

    def project(self, project_id, owner):
        with self.engine.connect() as db:
            row = self.require_project(db, project_id, owner)
            row["documents"] = [dict(r) for r in db.execute(select(business_documents.c.id, business_documents.c.name, business_documents.c.status, business_documents.c.size_bytes, business_documents.c.content).where(business_documents.c.project_id == project_id).order_by(business_documents.c.created_at)).mappings()]
            row["claims"] = [r[0] for r in db.execute(select(business_claims.c.content).where(business_claims.c.project_id == project_id).order_by(business_claims.c.id))]
            row["personas"] = [r[0] for r in db.execute(select(business_personas.c.content).where(business_personas.c.project_id == project_id).order_by(business_personas.c.id))]
            row["analyses"] = [dict(r) for r in db.execute(select(business_analyses.c.id, business_analyses.c.status, business_analyses.c.stage, business_analyses.c.baseline_id, business_analyses.c.created_at, business_analyses.c.input_snapshot).where(business_analyses.c.project_id == project_id).order_by(business_analyses.c.created_at.desc()).limit(50)).mappings()]
            for run in row["analyses"]:
                snapshot = run.pop("input_snapshot")
                run["engine"] = snapshot["config"]["engine"]
                run["input_revision"] = snapshot["revision"]
                run["shock"] = snapshot.get("shock")
                run["review_source_id"] = snapshot.get("review_source", {}).get("analysis_id")
            return row

    def store_documents(self, project_id, owner, documents, claims, max_files, max_total):
        with self.engine.begin() as db:
            self.require_project(db, project_id, owner, lock=True)
            # Serialize per-user quota checks across uploads in different projects.
            db.execute(select(users.c.id).where(users.c.id == owner).with_for_update()).scalar_one()
            count = db.execute(select(func.count()).select_from(business_documents).where(business_documents.c.project_id == project_id)).scalar_one()
            used = db.execute(select(func.coalesce(func.sum(business_documents.c.size_bytes), 0)).select_from(business_documents.join(business_projects)).where(business_projects.c.owner_user_id == owner)).scalar_one()
            if count + len(documents) > max_files or used + sum(d["size_bytes"] for d in documents) > max_total:
                raise UploadQuotaExceeded("Batas berkas atau kuota penyimpanan bisnis terlampaui")
            for row in documents:
                db.execute(insert(business_documents).values(project_id=project_id, **row))
            for claim in claims:
                db.execute(insert(business_claims).values(id=claim["id"], project_id=project_id, document_id=claim["source"]["document_id"], content=claim))
            db.execute(update(business_projects).where(business_projects.c.id == project_id).values(revision=business_projects.c.revision + 1, updated_at=utcnow()))

    def patch_item(self, table, project_id, item_id, owner, expected, changes):
        with self.engine.begin() as db:
            self.require_project(db, project_id, owner, lock=True)
            row = db.execute(select(table.c.content).where(table.c.id == item_id, table.c.project_id == project_id).with_for_update()).scalar_one_or_none()
            if row is None:
                raise ResourceNotFound()
            if row["revision"] != expected:
                raise RevisionConflict()
            value = dict(row) | changes | {"revision": expected + 1}
            if table is business_claims:
                from .contracts import Claim
                value = Claim.model_validate(value).model_dump(mode="json")
            else:
                from .contracts import Persona
                updated_fields = set(changes) & {"name", "goals", "constraints", "motivations", "knowledge", "interests"}
                if updated_fields:
                    value["provenance"] = dict(value.get("provenance", {})) | {field: "user_supplied_assumption" for field in updated_fields}
                    value["reviewed"] = changes.get("reviewed", False)
                value = Persona.model_validate(value).model_dump(mode="json")
            db.execute(update(table).where(table.c.id == item_id).values(content=value))
            db.execute(update(business_projects).where(business_projects.c.id == project_id).values(revision=business_projects.c.revision + 1, updated_at=utcnow()))
            return value

    def exclude_document(self, project_id, document_id, owner, expected):
        with self.engine.begin() as db:
            project = self.require_project(db, project_id, owner, lock=True)
            if project["revision"] != expected:
                raise RevisionConflict()
            changed = db.execute(update(business_documents).where(business_documents.c.id == document_id, business_documents.c.project_id == project_id).values(status="excluded"))
            if changed.rowcount != 1:
                raise ResourceNotFound()
            for row in db.execute(select(business_claims).where(business_claims.c.document_id == document_id)).mappings():
                content = row["content"]
                db.execute(update(business_claims).where(business_claims.c.id == row["id"]).values(content=content | {"review_status": "rejected", "revision": content["revision"] + 1}))
            db.execute(update(business_projects).where(business_projects.c.id == project_id).values(revision=expected + 1, updated_at=utcnow()))

    def approve_claims(self, project_id, owner, expected):
        with self.engine.begin() as db:
            project = self.require_project(db, project_id, owner, lock=True)
            if project["revision"] != expected:
                raise RevisionConflict()
            for row in db.execute(select(business_claims).where(business_claims.c.project_id == project_id)).mappings():
                claim = row["content"]
                if claim["review_status"] == "pending":
                    db.execute(update(business_claims).where(business_claims.c.id == row["id"]).values(content=claim | {"review_status": "approved", "revision": claim["revision"] + 1}))
            db.execute(update(business_projects).where(business_projects.c.id == project_id).values(revision=expected + 1, updated_at=utcnow()))

    def add_personas(self, project_id, owner, expected, personas):
        with self.engine.begin() as db:
            project = self.require_project(db, project_id, owner, lock=True)
            if project["revision"] != expected:
                raise RevisionConflict()
            existing = db.execute(select(func.count()).select_from(business_personas).where(business_personas.c.project_id == project_id)).scalar_one()
            if existing + len(personas) > 24:
                raise StageConflict("Maksimum 24 persona per proyek pilot")
            for persona in personas:
                db.execute(insert(business_personas).values(id=persona["id"], project_id=project_id, content=persona))
            db.execute(update(business_projects).where(business_projects.c.id == project_id).values(revision=expected + 1, updated_at=utcnow()))

    def enqueue(self, project_id, owner, snapshot, key=None, baseline_id=None, frozen_source_id=None):
        with self.engine.begin() as db:
            project = self.require_project(db, project_id, owner, lock=True)
            if key:
                previous = db.execute(select(business_analyses).where(business_analyses.c.project_id == project_id, business_analyses.c.idempotency_key == key)).mappings().one_or_none()
                if previous:
                    same_quick_request = snapshot.get("input_mode") == "automatic-v1" and previous["input_snapshot"].get("input_mode") == "automatic-v1" and previous["input_snapshot"]["config"] == snapshot["config"] and previous["input_snapshot"].get("review_source") == snapshot.get("review_source")
                    if (previous["input_snapshot"] != snapshot and not same_quick_request) or previous["baseline_id"] != baseline_id:
                        raise StageConflict("Idempotency key analisis sudah dipakai untuk input berbeda")
                    return dict(previous)
            if frozen_source_id:
                source = db.execute(select(business_analyses).where(business_analyses.c.id == frozen_source_id, business_analyses.c.project_id == project_id)).mappings().one_or_none()
                if not source or snapshot.get("review_source", {}).get("analysis_id") != frozen_source_id:
                    raise StageConflict("Sumber review tidak sesuai proyek")
                # The project lock serializes even submissions with different
                # keys. A refresh/double click must not buy the review twice.
                previous = db.execute(select(business_analyses).where(business_analyses.c.project_id == project_id, business_analyses.c.input_snapshot["review_source"]["analysis_id"].astext == frozen_source_id)).mappings().first()
                if previous:
                    if previous["input_snapshot"].get("review_source", {}).get("retry_failed", False) != snapshot.get("review_source", {}).get("retry_failed", False) or any(previous["input_snapshot"]["config"][k] != snapshot["config"][k] for k in ("max_tokens", "max_seconds", "review_concurrency")):
                        raise StageConflict("Review lanjutan run ini sudah dibuat dengan batas berbeda")
                    return dict(previous)
            if not baseline_id and not frozen_source_id and project["revision"] != snapshot["revision"]:
                raise RevisionConflict()
            analysis_id, job_id = uid("analysis"), uid("job")
            row = {"id": analysis_id, "project_id": project_id, "baseline_id": baseline_id, "status": "queued", "stage": "queued", "input_snapshot": snapshot, "result": {}, "created_at": utcnow(), "updated_at": utcnow(), "idempotency_key": key}
            db.execute(insert(business_analyses).values(**row))
            # A paid request may already have been billed when a worker dies.
            # Require an explicit new live analysis rather than spend twice.
            attempts = 1 if snapshot["config"]["engine"] == "oasis" else 2
            db.execute(insert(jobs).values(id=job_id, simulation_id=None, analysis_id=analysis_id, stage="business", status="queued", config={}, input_revision=snapshot["revision"], created_at=utcnow(), updated_at=utcnow(), available_at=utcnow(), attempts=0, max_attempts=attempts))
            return row | {"job_id": job_id}

    def analysis(self, analysis_id, owner=None):
        with self.engine.connect() as db:
            statement = select(business_analyses).join(business_projects).where(business_analyses.c.id == analysis_id)
            if owner:
                statement = statement.where(business_projects.c.owner_user_id == owner)
            row = db.execute(statement).mappings().one_or_none()
            if row is None:
                raise ResourceNotFound()
            return dict(row)

    def keyed_analysis(self, project_id, owner, key):
        if not key:
            return None
        with self.engine.connect() as db:
            self.require_project(db, project_id, owner)
            row = db.execute(select(business_analyses).where(business_analyses.c.project_id == project_id, business_analyses.c.idempotency_key == key)).mappings().one_or_none()
            return dict(row) if row else None

    def publish(self, job, worker_id, stage, payload, result=None, status="running", prepared_snapshot=None):
        """Fence publication against an expired/reassigned lease in one transaction."""
        with self.engine.begin() as db:
            lease = db.execute(select(jobs).where(jobs.c.id == job["id"]).with_for_update()).mappings().one_or_none()
            if not lease or lease["execution_token"] != job["execution_token"] or lease["lease_owner"] != worker_id or lease["status"] != "running" or lease["lease_expires_at"] < utcnow():
                raise RuntimeError("Business job lease lost")
            analysis = db.execute(select(business_analyses).where(business_analyses.c.id == job["analysis_id"]).with_for_update()).mappings().one()
            if analysis["status"] == "cancelled":
                raise RuntimeError("Business analysis cancelled")
            values = {"stage": stage, "status": status, "updated_at": utcnow()}
            if prepared_snapshot is not None:
                if analysis["input_snapshot"].get("preparation", {}).get("status") != "pending":
                    raise RuntimeError("Business input already frozen")
                values["input_snapshot"] = prepared_snapshot
                # Save generated profiles for inspection; do not overwrite any
                # existing manually edited profile or mark human review done.
                db.execute(select(business_projects.c.id).where(business_projects.c.id == analysis["project_id"]).with_for_update()).scalar_one()
                count = db.execute(select(func.count()).select_from(business_personas).where(business_personas.c.project_id == analysis["project_id"])).scalar_one()
                if count + len(prepared_snapshot["personas"]) <= 24:
                    for persona in prepared_snapshot["personas"]:
                        db.execute(insert(business_personas).values(id=persona["id"], project_id=analysis["project_id"], content=persona))
                    db.execute(update(business_projects).where(business_projects.c.id == analysis["project_id"]).values(revision=business_projects.c.revision + 1, updated_at=utcnow()))
            if result is not None:
                values["result"] = result
            db.execute(update(business_analyses).where(business_analyses.c.id == job["analysis_id"]).values(**values))
            sequence = db.execute(select(func.coalesce(func.max(business_events.c.sequence), 0)).where(business_events.c.analysis_id == job["analysis_id"])).scalar_one() + 1
            db.execute(insert(business_events).values(analysis_id=job["analysis_id"], sequence=sequence, type=stage, payload=payload, created_at=utcnow()))

    def events(self, analysis_id, after=0):
        with self.engine.connect() as db:
            return [dict(r) for r in db.execute(select(business_events).where(business_events.c.analysis_id == analysis_id, business_events.c.sequence > after).order_by(business_events.c.sequence).limit(200)).mappings()]

    def cancel(self, analysis_id, owner):
        self.analysis(analysis_id, owner)
        with self.engine.begin() as db:
            db.execute(update(jobs).where(jobs.c.analysis_id == analysis_id, jobs.c.status.in_(["queued", "running"])).values(status="cancelled", updated_at=utcnow()))
            db.execute(update(business_analyses).where(business_analyses.c.id == analysis_id, business_analyses.c.status.in_(["queued", "running"])).values(status="cancelled", stage="cancelled", updated_at=utcnow()))

    def cancelled_discussion_records(self, analysis_id):
        """Audit records for an explicitly requested recovery, never a paid retry."""
        with self.engine.connect() as db:
            rows = [dict(row) for row in db.execute(select(business_events.c.type, business_events.c.payload)
                    .where(business_events.c.analysis_id == analysis_id).order_by(business_events.c.sequence)).mappings()]
        if any(row["type"] == "validation" for row in rows):
            raise StageConflict("Review mungkin sudah dimulai sebelum pembatalan; pemulihan ini hanya untuk diskusi yang belum masuk validasi")
        events, calls = [], {}
        for row in rows:
            if row["type"] == "interaction" and isinstance(row["payload"].get("event"), dict):
                events.append(row["payload"]["event"])
            call = row["payload"].get("call")
            if isinstance(call, dict) and call.get("call_id"):
                calls[call["call_id"]] = call
        return events, list(calls.values())

    def committed_interactions(self, analysis_id):
        # Recovery needs the whole committed stream, not a UI page of logs.
        with self.engine.connect() as db:
            payloads = db.execute(select(business_events.c.payload).where(business_events.c.analysis_id == analysis_id, business_events.c.type == "interaction").order_by(business_events.c.sequence)).scalars()
            return [payload["event"] for payload in payloads if isinstance(payload.get("event"), dict)]

    def review_followup(self, analysis_id):
        with self.engine.connect() as db:
            row = db.execute(select(business_analyses.c.id, business_analyses.c.status).where(business_analyses.c.input_snapshot["review_source"]["analysis_id"].astext == analysis_id).order_by(business_analyses.c.created_at).limit(1)).mappings().one_or_none()
            return dict(row) if row else None
