"""Atomic conversation writes use project locks and the existing fenced queue."""
from sqlalchemy import func, insert, select, update
from ..database import jobs
from ..errors import ResourceNotFound, RevisionConflict, StageConflict
from .tables import business_ideas as ideas, business_idea_revisions as revisions, business_chat_turns as turns, business_documents
from .repository import uid, utcnow


def public_turn(row):
    return {k: row[k] for k in ("id", "project_id", "sequence", "status", "request", "response", "created_at", "updated_at")} | {"idea_context": row["input_snapshot"].get("idea")}


class ConversationRepository:
    def __init__(self, business):
        self.business, self.engine = business, business.engine

    def revision(self, project_id, revision_id, owner):
        with self.engine.connect() as db:
            self.business.require_project(db, project_id, owner)
            row = db.execute(select(revisions).where(revisions.c.id == revision_id, revisions.c.project_id == project_id)).mappings().one_or_none()
            if not row:
                raise ResourceNotFound()
            return dict(row)

    def history(self, project_id, idea_id, owner):
        with self.engine.connect() as db:
            self.business.require_project(db, project_id, owner)
            if not db.execute(select(ideas.c.id).where(ideas.c.id == idea_id, ideas.c.project_id == project_id)).scalar_one_or_none():
                raise ResourceNotFound()
            return [dict(r) for r in db.execute(select(revisions).where(revisions.c.idea_id == idea_id).order_by(revisions.c.version.desc()).limit(50)).mappings()]

    def workspace(self, project_id, owner, before=None):
        with self.engine.connect() as db:
            self.business.require_project(db, project_id, owner)
            all_ideas = []
            for row in db.execute(select(ideas).where(ideas.c.project_id == project_id).order_by(ideas.c.updated_at.desc())).mappings():
                latest = db.execute(select(revisions).where(revisions.c.idea_id == row["id"], revisions.c.version == row["version"])).mappings().one()
                all_ideas.append({"id": row["id"], "title": row["title"], "version": row["version"], "latest_revision": dict(latest)})
            statement = select(turns).where(turns.c.project_id == project_id)
            if before is not None:
                statement = statement.where(turns.c.sequence < before)
            rows = [public_turn(r) for r in db.execute(statement.order_by(turns.c.sequence.desc()).limit(41)).mappings()]
            page = list(reversed(rows[:40]))
            return {"ideas": all_ideas, "turns": page, "next_before": page[0]["sequence"] if len(rows) > 40 else None}

    def save_idea(self, project_id, owner, payload, key, idea_id=None):
        value = {k: payload[k] for k in ("title", "text", "document_ids", "source_turn_ids")}
        value["provenance"] = "user_proposed_assumption"
        with self.engine.begin() as db:
            project = self.business.require_project(db, project_id, owner, lock=True)
            previous = db.execute(select(revisions).where(revisions.c.project_id == project_id, revisions.c.idempotency_key == key)).mappings().one_or_none()
            if previous:
                if previous["content"] != value or (idea_id is not None and previous["idea_id"] != idea_id):
                    raise StageConflict("Permintaan simpan sudah digunakan untuk ide berbeda")
                return dict(previous)
            if project["revision"] != payload["expected_revision"]:
                raise RevisionConflict()
            documents = db.execute(select(business_documents).where(business_documents.c.project_id == project_id, business_documents.c.id.in_(value["document_ids"]))).mappings().all()
            if len(documents) != len(set(value["document_ids"])) or any(d["status"] != "ready" or d["content"].get("purpose") != "idea" for d in documents):
                raise StageConflict("Pilih dokumen ide yang dapat dibaca dari proyek ini")
            known_turns = set(db.execute(select(turns.c.id).where(turns.c.project_id == project_id, turns.c.id.in_(value["source_turn_ids"]))).scalars())
            if known_turns != set(value["source_turn_ids"]):
                raise ResourceNotFound()
            if idea_id:
                idea = db.execute(select(ideas).where(ideas.c.id == idea_id, ideas.c.project_id == project_id).with_for_update()).mappings().one_or_none()
                if not idea:
                    raise ResourceNotFound()
                if idea["version"] != payload["expected_version"]:
                    raise RevisionConflict()
                if idea["version"] >= 50:
                    raise StageConflict("Batas 50 versi per ide tercapai")
                version = idea["version"] + 1
                db.execute(update(ideas).where(ideas.c.id == idea_id).values(title=value["title"], version=version, updated_at=utcnow()))
            else:
                if payload["expected_version"] != 0:
                    raise RevisionConflict()
                if db.execute(select(func.count()).select_from(ideas).where(ideas.c.project_id == project_id)).scalar_one() >= 12:
                    raise StageConflict("Batas 12 ide per proyek tercapai")
                idea_id, version = uid("idea"), 1
                db.execute(insert(ideas).values(id=idea_id, project_id=project_id, title=value["title"], version=version, idempotency_key=key, created_at=utcnow(), updated_at=utcnow()))
            row = {"id": uid("idea_revision"), "idea_id": idea_id, "project_id": project_id, "version": version, "content": value, "created_at": utcnow(), "idempotency_key": key}
            db.execute(insert(revisions).values(**row))
            db.execute(update(self.business_project_table).where(self.business_project_table.c.id == project_id).values(revision=project["revision"] + 1, updated_at=utcnow()))
            return row

    @property
    def business_project_table(self):
        from .tables import business_projects
        return business_projects

    def keyed_turn(self, project_id, owner, key):
        with self.engine.connect() as db:
            self.business.require_project(db, project_id, owner)
            row = db.execute(select(turns).where(turns.c.project_id == project_id, turns.c.idempotency_key == key)).mappings().one_or_none()
            return dict(row) if row else None

    def enqueue(self, project_id, owner, request, snapshot, key):
        with self.engine.begin() as db:
            project = self.business.require_project(db, project_id, owner, lock=True)
            previous = db.execute(select(turns).where(turns.c.project_id == project_id, turns.c.idempotency_key == key)).mappings().one_or_none()
            if previous:
                if previous["request"] != request:
                    raise StageConflict("Pesan ini sudah digunakan untuk input berbeda")
                return public_turn(previous)
            if project["revision"] != request["expected_revision"]:
                raise RevisionConflict()
            if db.execute(select(turns.c.id).where(turns.c.project_id == project_id, turns.c.status.in_(["queued", "running"]))).first():
                raise StageConflict("Tunggu respons yang sedang berjalan atau batalkan terlebih dahulu")
            sequence = db.execute(select(func.coalesce(func.max(turns.c.sequence), 0)).where(turns.c.project_id == project_id)).scalar_one() + 1
            if sequence > 200:
                raise StageConflict("Batas 200 percakapan per proyek pilot tercapai")
            row = {"id": uid("chat"), "project_id": project_id, "sequence": sequence, "status": "queued", "request": request, "input_snapshot": snapshot, "response": None, "created_at": utcnow(), "updated_at": utcnow(), "idempotency_key": key}
            db.execute(insert(turns).values(**row))
            job_id = uid("job")
            db.execute(insert(jobs).values(id=job_id, simulation_id=None, analysis_id=None, business_chat_turn_id=row["id"], stage="business_chat", status="queued", config={}, input_revision=project["revision"], created_at=utcnow(), updated_at=utcnow(), available_at=utcnow(), attempts=0, max_attempts=1))
            return public_turn(row) | {"job_id": job_id}

    def turn(self, turn_id):
        with self.engine.connect() as db:
            row = db.execute(select(turns).where(turns.c.id == turn_id)).mappings().one_or_none()
            if not row:
                raise ResourceNotFound()
            return dict(row)

    def publish(self, job, worker, status, response=None):
        with self.engine.begin() as db:
            lease = db.execute(select(jobs).where(jobs.c.id == job["id"]).with_for_update()).mappings().one_or_none()
            if not lease or lease["status"] != "running" or lease["lease_owner"] != worker or lease["execution_token"] != job["execution_token"] or lease["lease_expires_at"] < utcnow():
                raise RuntimeError("Chat job lease lost")
            changed = db.execute(update(turns).where(turns.c.id == job["business_chat_turn_id"], turns.c.status.in_(["queued", "running"])).values(status=status, response=response, updated_at=utcnow()))
            if not changed.rowcount:
                raise RuntimeError("Chat request no longer active")

    def cancel(self, project_id, turn_id, owner):
        with self.engine.begin() as db:
            self.business.require_project(db, project_id, owner)
            if not db.execute(select(turns.c.id).where(turns.c.project_id == project_id, turns.c.id == turn_id)).first():
                raise ResourceNotFound()
            job = db.execute(select(jobs).where(jobs.c.business_chat_turn_id == turn_id).with_for_update()).mappings().one()
            turn = db.execute(select(turns).where(turns.c.id == turn_id)).mappings().one()
            if turn["status"] not in {"queued", "running"}:
                return
            db.execute(update(jobs).where(jobs.c.business_chat_turn_id == turn_id, jobs.c.status.in_(["queued", "running"])).values(status="cancelled", updated_at=utcnow()))
            db.execute(update(turns).where(turns.c.id == turn_id, turns.c.status.in_(["queued", "running"])).values(status="cancelled", response={"billing_status": "unknown" if job["attempts"] else "not_dispatched"}, updated_at=utcnow()))

    def cancelled_usage(self, job, worker, calls):
        """Retain usage after cancellation without publishing a discarded answer."""
        with self.engine.begin() as db:
            lease = db.execute(select(jobs).where(jobs.c.id == job["id"]).with_for_update()).mappings().one_or_none()
            if not lease or lease["status"] != "cancelled" or lease["execution_token"] != job["execution_token"] or lease["lease_owner"] != worker:
                return
            db.execute(update(turns).where(turns.c.id == job["business_chat_turn_id"], turns.c.status == "cancelled").values(response={"billing_status": "provider_reported" if calls and all(c.get("cost") is not None for c in calls) else "unknown", "usage": calls}, updated_at=utcnow()))
