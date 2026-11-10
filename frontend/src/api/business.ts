import { request } from "./client";
import { rememberBusinessProject } from "../data/businessWorkspace";

const root = "/api/v1/business";
const encoded = encodeURIComponent;
const json = (method: string, body: unknown): RequestInit => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export type BusinessContext = {
  name: string;
  industry: string;
  region: string;
  target_customer: string;
  decision_question: string;
  business_model?: string;
  value_proposition?: string;
  data_classification: "public" | "synthetic" | "non_confidential";
};
export type BusinessClaim = {
  id: string; quote: string; normalized_text: string; classification: string;
  variable: string | null; value: string | null; unit: string | null; period: string | null;
  region?: string | null;
  review_status: "pending" | "approved" | "rejected"; evidence_status: string; revision: number;
  source: { document_id: string; locator: { char_start: number; char_end: number; page?: number | null; paragraph?: number | null; table?: number | null; row?: number | null; column?: number | null } };
};
export type BusinessPersona = {
  id: string; name: string; role: string; stakeholder_type: "direct" | "indirect" | "hidden";
  goals: string[]; motivations: string[]; constraints: string[]; knowledge: string[];
  interests: string[]; relationships: string[]; provenance: Record<string, unknown>;
  discovery_rationale: string; active: boolean; reviewed: boolean; revision: number;
};
export type BusinessFinding = {
  id: string; title: string; category: string; severity: string; status: string; origin: string;
  author: string; claim_ids: string[]; persona_ids: string[]; event_ids: string[];
  evidence_ids: string[]; calculation_ids: string[]; reasoning: string; confidence: string;
  evidence_gaps: string[]; next_validation: string; owner_suggestion: string;
};
export type BusinessEvent = {
  id: string; sequence?: number; kind: string; round: number; actor_id: string; target_id: string;
  rationale: string; amount?: string | null; parent_event_ids: string[];
  state_before?: { version: number; position: string }; state_after?: { version: number; position: string };
  visibility?: "public" | "participants";
  content?: string; thread_id?: string | null; reply_to?: string | null;
  dialogue_act?: "statement" | "question" | "answer" | "challenge" | "clarification" | "proposal" | "abstain";
  dispatch?: { reason: string; trigger_event_id: string | null; followup: boolean };
  stance_update?: { before: StanceValue; after: StanceValue; reason: string; influenced_by_event_ids: string[] };
};
export type StanceValue = "support" | "oppose" | "conditional" | "undecided";
export type DialogueQuality = { version: string; messages: number; reply_pairs: number; reciprocal_pairs: number; customer_peer_replies: number; near_duplicate_event_ids: string[]; questions: number; questions_without_recipient_reply: string[]; warnings: string[]; limited_exchange: boolean; notice: string };
export type SwarmStance = { stance: StanceValue; stance_reason: string; stance_history: { event_id: string; round: number; before: StanceValue; after: StanceValue; reason: string; influenced_by_event_ids: string[]; visibility: "public" | "participants" }[] };
export type Calculation = {
  contribution_margin: string | null; break_even_units_monthly: string | null; profit_monthly: string | null;
  missing_inputs: string[]; inputs: Record<string, string | null>; status: string; formulas: Record<string, string>;
};
export type BusinessEvidence = { id: string; status: string; url?: string | null; reason?: string; provider?: string; region?: string; observed_period?: string | null; unit?: string | null; retrieved_at?: string; value?: string | null };
export type BusinessAnalysis = {
  id: string; project_id: string; baseline_id: string | null; status: string; stage: string; created_at: string;
  review_followup?: { id: string; status: string } | null;
  input_snapshot: { information_policy?: { version: string; public_brief: string }; revision: number; context: BusinessContext; personas: BusinessPersona[]; claims: BusinessClaim[]; documents?: { id: string; name: string }[]; config: { engine: "fixture" | "oasis"; rounds: number; interaction_mode?: "pairwise" | "swarm"; customer_count?: number }; idea?: { id: string; idea_id: string; title: string; version: number; text: string }; shock?: Shock; input_mode?: string; preparation?: { status: string; generator?: string; human_reviewed?: boolean }; review_source?: { analysis_id: string } };
  result: {
    usage?: Record<string, unknown>;
    stop_reason?: string;
    simulation?: { events: BusinessEvent[]; states: Record<string, { version: number; position: string }>; relationships?: { source: string; target: string; status: string; event_ids: string[] }[]; calculation: Calculation; stop_reason: string; usage: Record<string, unknown>; interaction_mode?: string; stances?: Record<string, SwarmStance>; discussion_quality?: DialogueQuality };
    findings?: BusinessFinding[]; evidence?: BusinessEvidence[];
    agent_runs?: { role: string; status?: string; phase?: string; execution_kind?: string; message?: string; tokens?: number | null; status_code?: number; failure_kind?: string; error_type?: string }[];
    disagreements?: { author: string; summary: string }[]; limitations?: string[];
    report?: { title: string }; error?: string; elapsed_seconds?: number;
    recovery?: { original_execution_status: string; specialist_review: string; new_model_calls: number };
    provenance?: { execution_kind: string; model: string | null; input_revision: number; seed: number; prompt_version: string };
  };
};
export type Shock = { kind: "supplier_cost_increase" | "competitor_price_cut" | "regulation_change"; magnitude_percent: string; region: string; effective_round: number; duration_rounds: number; response_strategy: "observe" | "match_price"; description: string; announce_to_personas?: boolean };
export type BusinessProject = {
  id: string; context: BusinessContext; revision: number; created_at: string; updated_at: string;
  documents: { id: string; name: string; status: string; size_bytes: number; content: { error?: string; claim_count: number; notice?: string; purpose?: "evidence" | "idea" } }[];
  claims: BusinessClaim[]; personas: BusinessPersona[];
  analyses: { id: string; status: string; stage: string; engine: string; baseline_id: string | null; review_source_id?: string | null; input_revision: number; created_at: string }[];
};
export type BusinessCapabilities = { llm_available: boolean; oasis_available: boolean; discovery_mode: string; max_file_bytes: number; max_personas: number };
export type BusinessComparison = {
  baseline_id: string; scenario_id: string; notice: string;
  metrics: { metric: string; before: string | null; after: string | null; delta: string | null; status: string }[];
  new_findings: BusinessFinding[]; shared_findings: { before: BusinessFinding; after: BusinessFinding }[];
  states_before: Record<string, { position: string; version: number }>; states_after: Record<string, { position: string; version: number }>;
};

export type ReportAssumption = Omit<BusinessClaim, "source"> & { source_label: string; document_id: string | null; locator: Record<string, unknown> };
export type ReportEvent = BusinessEvent & { actor_name: string; target_name: string };
export type ReportFinding = BusinessFinding & {
  affected_assumptions: ReportAssumption[]; supporting_evidence: BusinessEvidence[]; interaction_chain: ReportEvent[];
  estimated_impact: { status: string; explanation: string }; has_related_calculation: boolean;
};
export type BusinessReport = {
  version: string; title: string; analysis_id: string; status: string; created_at: string | null; context: BusinessContext;
  sections: { id: string; title: string }[];
  summary: { decision_question: string; text: string; finding_count: number; high_priority_count: number; disagreement_count: number; unavailable_evidence_count: number; top_finding_ids: string[]; validation_status: string; next_action: string };
  assumptions: ReportAssumption[]; findings: ReportFinding[]; evidence: (BusinessEvidence & { related_claim_ids: string[] })[];
  contradictions: { author: string; summary: string }[];
  scenario: { is_scenario: boolean; baseline_id: string | null; shock: Shock | null; comparison_available: boolean; notice: string;
    metrics: (BusinessComparison["metrics"][number] & { label: string })[]; new_finding_ids: string[];
    state_changes: { id: string; name: string; before: { position: string; version: number } | null; after: { position: string; version: number } }[] };
  validation_tasks: { id: string; finding_id: string; title: string; priority: string; action: string; owner: string; evidence_gaps: string[]; status: string }[];
  limitations: string[];
  appendix: { personas: BusinessPersona[]; events: ReportEvent[]; relationships: { source: string; target: string; status: string; event_ids: string[] }[];
    calculation: Calculation; provenance: Record<string, unknown>; agent_runs: NonNullable<BusinessAnalysis["result"]["agent_runs"]>; action_validation: { accepted?: number; rejected?: number }; stances?: Record<string, SwarmStance>; discussion_quality?: DialogueQuality | null };
};

export const businessKeys = { all: ["business"] as const, projects: ["business", "projects"] as const, project: (id: string) => ["business", "project", id] as const, analysis: (id: string) => ["business", "analysis", id] as const };
export const getBusinessCapabilities = () => request<BusinessCapabilities>(`${root}/capabilities`);
export type BusinessProjectSummary = Pick<BusinessProject, "id" | "context" | "revision" | "created_at" | "updated_at"> & {
  analysis_count: number; completed_analysis_count: number; ongoing_analysis_count: number; activity_at: string;
  latest_analysis: { id: string; project_id: string; status: string; stage: string; created_at: string; findings: BusinessFinding[] } | null;
};
export const listBusinessProjects = () => request<{ items: BusinessProjectSummary[] }>(`${root}/projects`);
export const getBusinessProject = async (id: string) => {
  const project = await request<BusinessProject>(`${root}/projects/${encoded(id)}`);
  rememberBusinessProject(project.id);
  return project;
};
export const excludeBusinessDocument = (id: string, documentId: string, revision: number) => request<BusinessProject>(`${root}/projects/${encoded(id)}/documents/${encoded(documentId)}/exclude`, json("POST", { expected_revision: revision }));
export const createBusinessProject = async (context: BusinessContext, key: string) => {
  const project = await request<BusinessProject>(`${root}/projects`, { ...json("POST", context), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
  rememberBusinessProject(project.id);
  return project;
};
export const uploadBusinessDocuments = (id: string, files: File[], purpose: "evidence" | "idea" = "evidence") => { const form = new FormData(); files.forEach(file => form.append("files", file)); form.append("purpose", purpose); return request<BusinessProject>(`${root}/projects/${encoded(id)}/documents`, { method: "POST", body: form }); };
export const patchBusinessClaim = (id: string, claim: BusinessClaim, changes: Record<string, unknown>) => request<BusinessClaim>(`${root}/projects/${encoded(id)}/claims/${encoded(claim.id)}`, json("PATCH", { expected_revision: claim.revision, ...changes }));
export const approveBusinessClaims = (id: string, revision: number) => request<BusinessProject>(`${root}/projects/${encoded(id)}/claims/approve`, json("POST", { expected_revision: revision }));
export const discoverBusinessStakeholders = (id: string, revision: number) => request<BusinessProject>(`${root}/projects/${encoded(id)}/stakeholder-discovery`, json("POST", { expected_revision: revision }));
export const patchBusinessPersona = (id: string, persona: BusinessPersona, changes: Record<string, unknown>) => request<BusinessPersona>(`${root}/projects/${encoded(id)}/personas/${encoded(persona.id)}`, json("PATCH", { expected_revision: persona.revision, ...changes }));
export const addBusinessPersona = (id: string, revision: number, persona: Record<string, unknown>) => request<BusinessPersona>(`${root}/projects/${encoded(id)}/personas?expected_revision=${revision}`, json("POST", persona));
export const startBusinessAnalysis = (id: string, revision: number, engine: "fixture" | "oasis", rounds: number, key: string, publicBrief = "") => request<BusinessAnalysis>(`${root}/projects/${encoded(id)}/analyses`, { ...json("POST", { expected_revision: revision, engine, rounds, max_personas: 24, public_brief: publicBrief }), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
export const startQuickBusinessAnalysis = (id: string, revision: number, engine: "fixture" | "oasis", rounds: number, key: string, options?: { interaction_mode?: "pairwise" | "swarm"; customer_count?: number; idea_revision_id?: string; max_tokens?: number; public_brief?: string }) => request<BusinessAnalysis>(`${root}/projects/${encoded(id)}/quick-analysis`, { ...json("POST", { expected_revision: revision, engine, rounds, ...options }), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
export const getBusinessAnalysis = (id: string) => request<BusinessAnalysis>(`${root}/analyses/${encoded(id)}`);
export const continueBusinessSpecialists = (id: string, key: string, retryFailed = false) => request<BusinessAnalysis>(`${root}/analyses/${encoded(id)}/specialist-review`, { ...json("POST", retryFailed ? { retry_failed: true } : {}), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
export const getBusinessReport = (id: string) => request<BusinessReport>(`${root}/analyses/${encoded(id)}/report`);
export const cancelBusinessAnalysis = (id: string) => request<BusinessAnalysis>(`${root}/analyses/${encoded(id)}/cancel`, { method: "POST" });
export const getBusinessEvents = (id: string) => request<{ items: { sequence: number; type: string; payload: { event?: BusinessEvent; message?: string; kind?: string } }[] }>(`${root}/analyses/${encoded(id)}/events`);
export const startBusinessScenario = (id: string, shock: Shock, key: string) => request<BusinessAnalysis>(`${root}/analyses/${encoded(id)}/scenarios`, { ...json("POST", { shock }), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
export const getBusinessComparison = (id: string) => request<BusinessComparison>(`${root}/analyses/${encoded(id)}/comparison`);
export const businessExportUrl = (id: string) => `${(import.meta.env.VITE_API_URL || "/backend").replace(/\/$/, "")}${root}/analyses/${encoded(id)}/export`;

export type ChatTarget = "facilitator" | "market" | "finance" | "legal" | "risk";
export type IdeaContent = { title: string; text: string; document_ids: string[]; source_turn_ids: string[]; provenance: string };
export type IdeaRevision = { id: string; idea_id: string; project_id: string; version: number; content: IdeaContent; created_at: string };
export type ProjectIdea = { id: string; title: string; version: number; latest_revision: IdeaRevision };
export type ChatCitation = { id: string; kind: string; label: string; text: string; document_id?: string; idea_revision_id?: string; analysis_id?: string; locator?: Record<string, unknown> };
export type ChatTurn = {
  id: string; project_id: string; sequence: number; status: "queued" | "running" | "completed" | "failed" | "cancelled";
  request: { content: string; target: ChatTarget; idea_revision_id: string | null; analysis_id: string | null; expected_revision: number };
  response: { answer?: string; responder?: string; questions?: string[]; suggested_revision?: string | null; citations?: ChatCitation[]; error?: string; error_type?: string; notice?: string; usage?: Record<string, unknown>[] } | null;
  created_at: string; updated_at: string;
  idea_context?: { id: string; title: string; version: number } | null;
};
export type Conversation = { ideas: ProjectIdea[]; turns: ChatTurn[]; next_before: number | null };
export type IdeaDraft = { expected_revision: number; expected_version: number; title: string; text: string; document_ids: string[]; source_turn_ids: string[] };
const keyedJson = (body: unknown, key: string): RequestInit => ({ ...json("POST", body), headers: { "Content-Type": "application/json", "Idempotency-Key": key } });
export const getBusinessConversation = (id: string, before?: number) => request<Conversation>(`${root}/projects/${encoded(id)}/conversation${before ? `?before=${before}` : ""}`);
export const getIdeaRevisions = (id: string, idea: string) => request<{ items: IdeaRevision[] }>(`${root}/projects/${encoded(id)}/ideas/${encoded(idea)}/revisions`);
export const saveBusinessIdea = (id: string, draft: IdeaDraft, key: string, idea?: string) => request<IdeaRevision>(`${root}/projects/${encoded(id)}/ideas${idea ? `/${encoded(idea)}/revisions` : ""}`, keyedJson(draft, key));
export const sendBusinessChat = (id: string, body: ChatTurn["request"], key: string) => request<ChatTurn>(`${root}/projects/${encoded(id)}/conversation`, keyedJson(body, key));
export const cancelBusinessChat = (id: string, turn: string) => request<{ status: string }>(`${root}/projects/${encoded(id)}/conversation/${encoded(turn)}/cancel`, { method: "POST" });
