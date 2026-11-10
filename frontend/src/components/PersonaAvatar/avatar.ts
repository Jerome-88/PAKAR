import { Avatar, Style } from "@dicebear/core";
import personas from "@dicebear/styles/personas.json" with { type: "json" };
import funEmoji from "@dicebear/styles/fun-emoji.json" with { type: "json" };

export type AvatarIdentity = {
  id?: unknown;
  name?: unknown;
  role?: unknown;
  kind?: "person" | "agent";
};

// Keep package versions and these options pinned: both are part of visual identity.
const personStyle = new Style(personas);
const agentStyle = new Style(funEmoji);
export const AVATAR_CACHE_LIMIT = 2048;
const cache = new Map<string, string>();
const text = (value: unknown) => typeof value === "string" ? value.trim() : typeof value === "number" && Number.isFinite(value) ? String(value) : "";
const normalize = (value: unknown) => text(value).toLowerCase().replace(/\s+/g, " ");

// Analytical runs expose a stable role, not a persona entity ID. Namespace it so
// a human with the same name can never acquire that system agent's identity.
export const agentAvatarId = (role: unknown) => `pakar:agent:${normalize(role) || "unknown"}`;

// Older message DTOs contain names only. Reuse a real ID only when unambiguous;
// do not assign a message/event ID or another person's ID to the portrait.
export function findPersonaId(list: readonly { id: string; name: string; group?: string }[], name: string, group?: string) {
  const matches = list.filter(p => normalize(p.name) === normalize(name) && (!group || normalize(p.group) === normalize(group)));
  return matches.length === 1 ? matches[0].id : undefined;
}

export const FALLBACK_AVATAR = `data:image/svg+xml;charset=utf-8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="32" fill="#e8eff9"/><circle cx="32" cy="25" r="10" fill="#526981"/><path d="M13 56c0-22 38-22 38 0" fill="#526981"/></svg>')}`;

export function getAvatarSource(identity: AvatarIdentity | null = {}): string {
  const kind = identity?.kind === "agent" ? "agent" : "person";
  // An ID always wins over editable metadata. JSON encoding prevents ambiguous
  // fallback combinations, and an anonymous persona has a safe, stable default.
  const seed = text(identity?.id) || `pakar:missing:${JSON.stringify([normalize(identity?.name), normalize(identity?.role)])}`;
  const key = JSON.stringify([kind, seed]);
  const existing = cache.get(key);
  if (existing) {
    cache.delete(key);
    cache.set(key, existing);
    return existing;
  }
  let source: string;
  try {
    const common = { seed, size: 64, borderRadius: 50, idRandomization: false };
    source = kind === "agent"
      ? new Avatar(agentStyle, { ...common, backgroundColor: ["#c8e6de", "#dce7fb", "#e8dcf6", "#f4e5c7"], eyesVariant: ["plain", "cute", "glasses", "wink", "stars"], mouthVariant: ["cute", "lilSmile", "plain", "smileTeeth", "wideSmile"] }).toDataUri()
      : new Avatar(personStyle, {
          ...common,
          backgroundColor: ["#e8eff9", "#e5f0eb", "#eee8f5", "#f4eddf"],
          // Deliberately illustrative colors; no gender, age, or ethnicity is
          // inferred from a stakeholder's name, occupation, or business role.
          skinColor: ["#a8c9e8", "#b9b2da", "#a4d2c7"],
          facialHairProbability: 0,
          noseVariant: ["smallRound", "mediumRound"],
          mouthVariant: ["smile", "bigSmile", "smirk"],
          eyesVariant: ["open", "happy", "glasses", "wink"],
          hairVariant: ["beanie", "cap", "buzzcut", "bobCut", "curly", "mohawk", "shortCombover", "sideShave"],
        }).toDataUri();
  } catch {
    source = FALLBACK_AVATAR;
  }
  if (cache.size >= AVATAR_CACHE_LIMIT) cache.delete(cache.keys().next().value!);
  cache.set(key, source);
  return source;
}
