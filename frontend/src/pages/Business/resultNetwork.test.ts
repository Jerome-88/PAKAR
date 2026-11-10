import { describe, expect, it } from "vitest";
import { createResultNetwork } from "./resultNetwork";

describe("recorded result network layout", () => {
  it("is deterministic and never mutates recorded connections", () => {
    const ids = Array.from({ length: 10 }, (_, i) => `persona-${i}`);
    const edges = [{ source: ids[0], target: ids[1] }, { source: ids[1], target: ids[2] }];
    const original = structuredClone(edges);
    const first = createResultNetwork(ids, edges, 900);
    const second = createResultNetwork(ids, edges, 900);
    expect(first.nodes.map(({ id, x, y }) => ({ id, x, y }))).toEqual(second.nodes.map(({ id, x, y }) => ({ id, x, y })));
    expect(edges).toEqual(original);
    expect(first.byId.size).toBe(10);
  });

  it("keeps finite unique positions for large and disconnected cohorts", () => {
    const ids = Array.from({ length: 120 }, (_, i) => `persona-${i}`);
    const network = createResultNetwork(ids, [], 360);
    expect(network.nodes).toHaveLength(120);
    expect(network.nodes.every(node => Number.isFinite(node.x) && Number.isFinite(node.y))).toBe(true);
    expect(new Set(network.nodes.map(node => `${node.x}:${node.y}`)).size).toBe(120);
  });
});
