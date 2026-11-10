from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ..auth import current_user
from ..errors import ApiError
from .contracts import AnalysisInput, QuickAnalysisInput, SpecialistReviewInput, BusinessContext, ClaimPatch, Persona, PersonaPatch, ScenarioInput
from .budget import BudgetExceeded, ExternalCallError
from .tables import business_claims, business_personas
from .conversation_contracts import ChatInput, IdeaInput

router = APIRouter(prefix="/api/v1/business", dependencies=[Depends(current_user)])


def service(request):
    return request.app.state.business


def owner(request):
    if not request.app.state.settings.auth_required:
        project_id = request.path_params.get("project_id")
        analysis_id = request.path_params.get("analysis_id")
        if project_id or analysis_id:
            return service(request).repository.resource_owner(project_id=project_id, analysis_id=analysis_id)
    return current_user(request)["id"]


class RevisionInput(BaseModel):
    expected_revision: int = Field(ge=1)


@router.get("/capabilities")
def capabilities(request: Request):
    return service(request).capabilities()


@router.get("/projects")
def projects(request: Request):
    return {"items": service(request).repository.list_projects(owner(request), shared=not request.app.state.settings.auth_required)}


@router.post("/projects", status_code=201)
def create(request: Request, payload: BusinessContext, idempotency_key: str | None = Header(default=None, min_length=1, max_length=128)):
    return service(request).create(owner(request), payload.model_dump(mode="json"), idempotency_key)


@router.get("/projects/{project_id}")
def project(request: Request, project_id: str):
    return service(request).repository.project(project_id, owner(request))


@router.delete("/projects/{project_id}")
def delete_project(request: Request, project_id: str):
    return service(request).delete_project(project_id, owner(request))


@router.post("/projects/{project_id}/documents", status_code=201)
async def upload(request: Request, project_id: str):
    # Check access before receiving/extracting document contents.
    await run_in_threadpool(service(request).repository.project, project_id, owner(request))
    form = await request.form(max_files=request.app.state.settings.max_files_per_project)
    try:
        files = [item for item in form.getlist("files") if hasattr(item, "file")]
        purpose = form.get("purpose", "evidence")
        if purpose not in {"evidence", "idea"}:
            raise ApiError(422, "invalid_document_purpose", "Pilih dokumen data atau dokumen ide")
        return await run_in_threadpool(service(request).upload, project_id, owner(request), files, purpose=purpose)
    finally:
        await form.close()


@router.get("/projects/{project_id}/conversation")
def conversation(request: Request, project_id: str, before: int | None = Query(default=None, ge=1)):
    return service(request).conversation.repository.workspace(project_id, owner(request), before)


@router.post("/projects/{project_id}/conversation", status_code=202)
def send_chat(request: Request, project_id: str, payload: ChatInput, idempotency_key: str = Header(min_length=1, max_length=128)):
    return service(request).conversation.send(project_id, owner(request), payload.model_dump(mode="json"), idempotency_key)


@router.post("/projects/{project_id}/conversation/{turn_id}/cancel")
def cancel_chat(request: Request, project_id: str, turn_id: str):
    service(request).conversation.repository.cancel(project_id, turn_id, owner(request))
    return {"status": "ok"}


@router.post("/projects/{project_id}/ideas", status_code=201)
def create_idea(request: Request, project_id: str, payload: IdeaInput, idempotency_key: str = Header(min_length=1, max_length=128)):
    return service(request).conversation.save_idea(project_id, owner(request), payload.model_dump(mode="json"), idempotency_key)


@router.post("/projects/{project_id}/ideas/{idea_id}/revisions", status_code=201)
def revise_idea(request: Request, project_id: str, idea_id: str, payload: IdeaInput, idempotency_key: str = Header(min_length=1, max_length=128)):
    return service(request).conversation.save_idea(project_id, owner(request), payload.model_dump(mode="json"), idempotency_key, idea_id)


@router.get("/projects/{project_id}/ideas/{idea_id}/revisions")
def idea_history(request: Request, project_id: str, idea_id: str):
    return {"items": service(request).conversation.repository.history(project_id, idea_id, owner(request))}


@router.get("/projects/{project_id}/claims")
def claims(request: Request, project_id: str):
    row = service(request).repository.project(project_id, owner(request))
    return {"items": row["claims"], "revision": row["revision"]}


@router.post("/projects/{project_id}/documents/{document_id}/exclude")
def exclude_document(request: Request, project_id: str, document_id: str, payload: RevisionInput):
    service(request).repository.exclude_document(project_id, document_id, owner(request), payload.expected_revision)
    return service(request).repository.project(project_id, owner(request))


@router.patch("/projects/{project_id}/claims/{claim_id}")
def patch_claim(request: Request, project_id: str, claim_id: str, payload: ClaimPatch):
    changes = payload.model_dump(mode="json", exclude_unset=True, exclude={"expected_revision"})
    # Nullable numeric fields may be cleared; non-null domain fields may not.
    for key in ("normalized_text", "classification", "review_status"):
        if key in changes and changes[key] is None:
            raise ApiError(422, "invalid_claim", f"{key} tidak boleh null")
    return service(request).repository.patch_item(business_claims, project_id, claim_id, owner(request), payload.expected_revision, changes)


@router.post("/projects/{project_id}/claims/approve")
def approve_claims(request: Request, project_id: str, payload: RevisionInput):
    service(request).repository.approve_claims(project_id, owner(request), payload.expected_revision)
    return service(request).repository.project(project_id, owner(request))


@router.post("/projects/{project_id}/stakeholder-discovery")
def discovery(request: Request, project_id: str, payload: RevisionInput):
    try:
        return service(request).discover(project_id, owner(request), payload.expected_revision)
    except BudgetExceeded as error:
        raise ApiError(504, "discovery_timeout", "Provider melewati batas waktu pembuatan persona. Gunakan Analisis otomatis untuk melanjutkan dengan penanganan fallback.") from error
    except (ExternalCallError, ValueError, KeyError, TypeError) as error:
        raise ApiError(502, "discovery_unavailable", "Provider belum menghasilkan persona yang valid. Gunakan Analisis otomatis atau coba lagi setelah memeriksa layanan model.") from error


@router.post("/projects/{project_id}/personas", status_code=201)
def add_persona(request: Request, project_id: str, payload: Persona, expected_revision: int = Query(ge=1)):
    return service(request).add_persona(project_id, owner(request), payload.model_dump(mode="json"), expected_revision)


@router.patch("/projects/{project_id}/personas/{persona_id}")
def patch_persona(request: Request, project_id: str, persona_id: str, payload: PersonaPatch):
    changes = payload.model_dump(mode="json", exclude_unset=True, exclude={"expected_revision"})
    if any(value is None for value in changes.values()):
        raise ApiError(422, "invalid_persona", "Atribut persona tidak boleh null")
    return service(request).repository.patch_item(business_personas, project_id, persona_id, owner(request), payload.expected_revision, changes)


@router.post("/projects/{project_id}/analyses", status_code=202)
def start(request: Request, project_id: str, payload: AnalysisInput, idempotency_key: str | None = Header(default=None, min_length=1, max_length=128)):
    try:
        return service(request).start(project_id, owner(request), payload.model_dump(mode="json", exclude_unset=True), idempotency_key)
    except ValueError as error:
        raise ApiError(422, "invalid_analysis", str(error)) from error


@router.post("/projects/{project_id}/quick-analysis", status_code=202)
def quick_start(request: Request, project_id: str, payload: QuickAnalysisInput, idempotency_key: str | None = Header(default=None, min_length=1, max_length=128)):
    try:
        return service(request).quick_start(project_id, owner(request), payload.model_dump(mode="json", exclude_unset=True), idempotency_key)
    except ValueError as error:
        raise ApiError(422, "invalid_analysis", "Input analisis otomatis tidak valid; periksa konfigurasi dan dokumen.") from error


@router.get("/analyses/{analysis_id}")
def analysis(request: Request, analysis_id: str):
    return service(request).analysis_view(analysis_id, owner(request))


@router.get("/analyses/{analysis_id}/findings")
def findings(request: Request, analysis_id: str):
    row = service(request).analysis_view(analysis_id, owner(request))
    return {"items": row["result"].get("findings", []), "status": row["status"]}


@router.post("/analyses/{analysis_id}/specialist-review", status_code=202)
def continue_specialists(request: Request, analysis_id: str, payload: SpecialistReviewInput, idempotency_key: str = Header(min_length=1, max_length=128)):
    return service(request).continue_specialists(analysis_id, owner(request), payload.model_dump(mode="json"), idempotency_key)


@router.get("/analyses/{analysis_id}/report")
def report(request: Request, analysis_id: str):
    return service(request).report_view(analysis_id, owner(request))


@router.get("/analyses/{analysis_id}/evidence")
def evidence(request: Request, analysis_id: str):
    row = service(request).repository.analysis(analysis_id, owner(request))
    return {"items": row["result"].get("evidence", []), "status": row["status"]}


@router.get("/analyses/{analysis_id}/events")
def events(request: Request, analysis_id: str, after: int = Query(default=0, ge=0)):
    service(request).repository.analysis(analysis_id, owner(request))
    return {"items": service(request).repository.events(analysis_id, after)}


@router.get("/analyses/{analysis_id}/stream")
async def stream(request: Request, analysis_id: str, after: int = Query(default=0, ge=0)):
    user = owner(request)
    await run_in_threadpool(service(request).repository.analysis, analysis_id, user)
    try:
        cursor = max(after, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        cursor = after

    async def generate():
        nonlocal cursor
        yield "retry: 2000\n: connected\n\n"
        while not await request.is_disconnected():
            rows = await run_in_threadpool(service(request).repository.events, analysis_id, cursor)
            for row in rows:
                cursor = row["sequence"]
                yield f"id: {cursor}\nevent: {row['type']}\ndata: {json.dumps(jsonable_encoder(row['payload']), ensure_ascii=False)}\n\n"
            row = await run_in_threadpool(service(request).repository.analysis, analysis_id, user)
            if row["status"] in {"completed", "partial", "failed", "cancelled"} and not rows:
                break
            if not rows:
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


@router.post("/analyses/{analysis_id}/cancel")
def cancel(request: Request, analysis_id: str):
    service(request).repository.cancel(analysis_id, owner(request))
    return service(request).repository.analysis(analysis_id, owner(request))


@router.post("/analyses/{analysis_id}/scenarios", status_code=202)
def scenario(request: Request, analysis_id: str, payload: ScenarioInput, idempotency_key: str | None = Header(default=None, min_length=1, max_length=128)):
    return service(request).scenario(analysis_id, owner(request), payload.shock.model_dump(mode="json"), idempotency_key)


@router.get("/analyses/{analysis_id}/comparison")
def comparison(request: Request, analysis_id: str):
    return service(request).comparison(analysis_id, owner(request))


@router.get("/analyses/{analysis_id}/export")
def export(request: Request, analysis_id: str):
    return HTMLResponse(service(request).export(analysis_id, owner(request)), headers={"Content-Disposition": f'attachment; filename="pakar-{analysis_id}.html"'})
