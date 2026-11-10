import type { BusinessEvent, BusinessFinding, BusinessPersona, StanceValue, SwarmStance } from "../../api/business";

export const stanceLabels: Record<StanceValue | "unrecorded", string> = {
  support: "Mendukung", oppose: "Menolak", conditional: "Bersyarat",
  undecided: "Belum memutuskan", unrecorded: "Belum tercatat",
};
export const roleLabels: Record<string, string> = {
  customer: "Calon pembeli", operator: "Fasilitator produk", supplier: "Pemasok",
  competitor: "Pesaing", regulator: "Peninjau klaim", employee: "Pelaksana",
  partner: "Mitra", investor: "Investor", community: "Masyarakat",
};
const validStance = (value: unknown): value is StanceValue => typeof value === "string" && ["support", "oppose", "conditional", "undecided"].includes(value);

/** Decode only known text envelopes. Never evaluate HTML or infer a stance. */
export function readableText(value: unknown, depth = 0): string {
  if (depth > 4 || value == null) return "";
  if (typeof value === "string") {
    const text = value.trim();
    if (text.startsWith("{") || text.startsWith("[") || text.startsWith('"')) {
      try { return readableText(JSON.parse(text), depth + 1) || text; } catch { /* Plain prose remains literal. */ }
    }
    return text;
  }
  if (Array.isArray(value)) return value.map(item => readableText(item, depth + 1)).filter(Boolean).join("\n\n");
  if (typeof value === "object") {
    const object = value as Record<string, unknown>;
    for (const key of ["content", "answer", "text", "reasoning", "stance_reason", "reason", "rationale"]) {
      if (object[key] != null) return readableText(object[key], depth + 1);
    }
  }
  return "";
}

export function friendlyText(value: unknown): string {
  const labels: Record<string, string> = {
    selling_price: "harga jual", variable_cost: "biaya per unit", fixed_cost_monthly: "biaya tetap bulanan",
    volume_monthly: "penjualan bulanan", contribution_margin: "margin per unit",
    break_even_units_monthly: "penjualan untuk balik modal", profit_monthly: "laba bulanan",
  };
  return readableText(value).replace(/\b(selling_price|variable_cost|fixed_cost_monthly|volume_monthly|contribution_margin|break_even_units_monthly|profit_monthly)\b/g, key => labels[key])
    .replace(/\bunit economics\b/gi, "biaya dan harga");
}

export function previewText(value: unknown, limit = 230): string {
  const text = friendlyText(value).replace(/[*`#]/g, "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit).replace(/\s+\S*$/, "")}…`;
}

export function formatBusinessAmount(value: unknown): string {
  if ((typeof value !== "string" && typeof value !== "number") || String(value).trim() === "" || !Number.isFinite(Number(value))) return "Belum diketahui";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(Number(value));
}

export function personaPositions(events: BusinessEvent[], personas: BusinessPersona[], saved?: Record<string, SwarmStance>) {
  const positions: Record<string, SwarmStance> = {};
  const ordered = events.map((event, index) => ({ event, index })).sort((a, b) => a.event.round - b.event.round || (a.event.sequence ?? a.index) - (b.event.sequence ?? b.index));
  for (const { event } of ordered) {
    const update = event.stance_update;
    if (!update || !validStance(update.after) || ["action_rejected", "shock", "shock_expired"].includes(event.kind)) continue;
    const history = positions[event.actor_id]?.stance_history ?? [];
    positions[event.actor_id] = { stance: update.after, stance_reason: readableText(update.reason), stance_history: update.before !== update.after ? [...history, { event_id: event.id, round: event.round, before: update.before, after: update.after, reason: readableText(update.reason), influenced_by_event_ids: update.influenced_by_event_ids ?? [], visibility: event.visibility ?? "participants" }] : history };
  }
  for (const persona of personas) {
    if (saved && Object.hasOwn(saved, persona.id)) {
      const state = saved[persona.id];
      if (state && validStance(state.stance)) positions[persona.id] = { ...state, stance_reason: readableText(state.stance_reason), stance_history: state.stance_history ?? [] };
      else delete positions[persona.id];
    }
  }
  return positions;
}

export function responseSummary(events: BusinessEvent[], personas: BusinessPersona[], saved?: Record<string, SwarmStance>) {
  const active = [...new Map(personas.filter(p => p.active !== false && typeof p.id === "string" && p.id.trim()).map(p => [p.id, p])).values()];
  const positions = personaPositions(events, active, saved);
  const counts = { support: 0, oppose: 0, conditional: 0, undecided: 0, unrecorded: 0 };
  const people: { persona: BusinessPersona; stance: StanceValue | "unrecorded"; reason: string }[] = active.map(persona => {
    const state = positions[persona.id];
    const stance = state?.stance ?? "unrecorded";
    counts[stance]++;
    return { persona, stance, reason: readableText(state?.stance_reason) };
  });
  return { people, counts, total: active.length };
}

/** Actual directed interactions/replies only; proposed profile links never become dialogue. */
export function recordedConnections(events: BusinessEvent[], people: ReturnType<typeof responseSummary>["people"]) {
  const ids = new Set(people.map(p => p.persona.id));
  const accepted = events.filter(e => !["action_rejected", "shock", "shock_expired"].includes(e.kind));
  const byId = new Map(accepted.map(e => [e.id, e]));
  const pairs = new Map<string, { source: string; target: string; eventIds: Set<string> }>();
  for (const event of accepted) {
    const targets = new Set([event.target_id, event.reply_to ? byId.get(event.reply_to)?.actor_id : undefined]);
    for (const target of targets) {
      if (!target || !ids.has(event.actor_id) || !ids.has(target) || event.actor_id === target) continue;
      const [source, other] = [event.actor_id, target].sort();
      const key = JSON.stringify([source, other]);
      const pair = pairs.get(key) ?? { source, target: other, eventIds: new Set<string>() };
      pair.eventIds.add(event.id);
      pairs.set(key, pair);
    }
  }
  return [...pairs.values()];
}

/** The short result points to discussion, rather than generic input-registry checks. */
export function discussionFindings(findings: BusinessFinding[], events: BusinessEvent[]) {
  const accepted = new Set(events.filter(event => !["action_rejected", "shock", "shock_expired", "abstain"].includes(event.kind)).map(event => event.id));
  const priority: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  return findings.filter(finding => finding.event_ids.some(id => accepted.has(id)))
    .sort((a, b) => (priority[a.severity] ?? 4) - (priority[b.severity] ?? 4))
    .filter((finding, index, all) => all.findIndex(other => other.author === finding.author && other.title.trim().toLowerCase() === finding.title.trim().toLowerCase()) === index);
}
