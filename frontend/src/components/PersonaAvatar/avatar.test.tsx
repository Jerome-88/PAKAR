import { Avatar } from "@dicebear/core";
import { fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { agentAvatarId, AVATAR_CACHE_LIMIT, FALLBACK_AVATAR, findPersonaId, getAvatarSource } from "./avatar";
import { AgentIdentity, AvatarCredits, PersonaAvatar } from "./PersonaAvatar";

afterEach(() => vi.restoreAllMocks());

describe("local persona identity", () => {
  it("keeps an ID's portrait through renaming, role edits, resizing and agent/person separation", () => {
    const source = getAvatarSource({ id: "stable-person", name: "Before", role: "customer" });
    expect(getAvatarSource({ id: "stable-person", name: "After", role: "investor" })).toBe(source);
    expect(getAvatarSource({ id: "stable-person", kind: "agent" })).not.toBe(source);
    const view = render(<PersonaAvatar id="stable-person" size={24} />);
    expect(view.container.querySelector("img")).toHaveAttribute("src", source);
    view.rerender(<PersonaAvatar id="stable-person" name="Edited" size={56} />);
    expect(view.container.querySelector("img")).toHaveAttribute("src", source);
  });

  it("uses deterministic safe fallbacks for missing/invalid metadata without render-time randomness", () => {
    const random = vi.spyOn(Math, "random").mockImplementation(() => { throw new Error("No random render seeds"); });
    const source = getAvatarSource({ id: {}, name: "  Someone  ", role: "Customer" });
    expect(source).not.toBe(FALLBACK_AVATAR);
    expect(source).toBe(getAvatarSource({ name: "someone", role: "customer" }));
    expect(getAvatarSource(null)).toBe(getAvatarSource({ id: NaN, name: [], role: {} }));
    expect(getAvatarSource({ id: 42 })).toBe(getAvatarSource({ id: "42" }));
    expect(random).not.toHaveBeenCalled();
  });

  it("generates 250 distinguishable, self-contained SVGs with no untrusted markup", () => {
    const sources = Array.from({ length: 250 }, (_, n) => getAvatarSource({ id: `load-person-${n}` }));
    expect(new Set(sources).size).toBeGreaterThan(245);
    const svg = decodeURIComponent(getAvatarSource({ id: '<script>alert("x")</script>' }).split(",")[1]);
    expect(svg).toContain("<svg");
    expect(svg).toContain("CC BY 4.0");
    expect(svg).not.toMatch(/<script|<image|<foreignObject|href="https?:/);
  });

  it("reuses SVGs across consumers and bounds memory, regenerating the same portrait after eviction", () => {
    const renderSvg = vi.spyOn(Avatar.prototype, "toDataUri");
    const first = getAvatarSource({ id: "cache-eviction-subject" });
    for (let n = 0; n < 100; n++) expect(getAvatarSource({ id: "cache-eviction-subject" })).toBe(first);
    expect(renderSvg).toHaveBeenCalledTimes(1);
    for (let n = 0; n < AVATAR_CACHE_LIMIT; n++) getAvatarSource({ id: `evict-${n}` });
    expect(getAvatarSource({ id: "cache-eviction-subject" })).toBe(first);
    expect(renderSvg).toHaveBeenCalledTimes(AVATAR_CACHE_LIMIT + 2);
  });

  it("recovers from SVG generation and image decoding failures locally", () => {
    vi.spyOn(Avatar.prototype, "toDataUri").mockImplementation(() => { throw new Error("Renderer failed"); });
    expect(getAvatarSource({ id: "failure-case" })).toBe(FALLBACK_AVATAR);
    vi.restoreAllMocks();
    const view = render(<PersonaAvatar id="decode-failure" />);
    const img = view.container.querySelector("img")!;
    fireEvent.error(img);
    expect(img).toHaveAttribute("src", FALLBACK_AVATAR);
    fireEvent.error(img);
    expect(img).toHaveAttribute("src", FALLBACK_AVATAR);
  });

  it("matches older messages to real IDs only when names are unambiguous", () => {
    const list = [{ id: "p1", name: "Alex", group: "Supplier" }, { id: "p2", name: "Alex", group: "Customer" }];
    expect(findPersonaId(list, "Alex")).toBeUndefined();
    expect(findPersonaId(list, " Alex ", "supplier")).toBe("p1");
    expect(findPersonaId(list, "Other")).toBeUndefined();
    expect(agentAvatarId(" Finance  Agent ")).toBe(agentAvatarId("finance agent"));
  });

  it("provides non-duplicated labels and accessible style attribution", () => {
    const view = render(<><AgentIdentity name="Finance Agent" /><AvatarCredits /></>);
    expect(view.getByText("Finance Agent")).toBeInTheDocument();
    expect(view.container.querySelector("img")).toHaveAttribute("aria-hidden", "true");
    expect(view.getByRole("link", { name: "Personas oleh Draftbit", hidden: true })).toHaveAttribute("href", "https://personas.draftbit.com/");
    expect(view.getByRole("link", { name: "CC BY 4.0", hidden: true })).toBeInTheDocument();
  });
});
