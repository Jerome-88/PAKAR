import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../test/server";
import { useBusinessLaunch } from "./useBusinessLaunch";

function Harness() {
  const [brief, setBrief] = useState("Konsep publik untuk calon customer, tanpa data internal.");
  const [revision, setRevision] = useState(1);
  const [done, setDone] = useState(false);
  const launch = useBusinessLaunch({ projectId: "p", revision, engine: "fixture", rounds: 4, brief, onSuccess: () => setDone(true), onRejected: () => setRevision(2) });
  return <><label>Brief<input value={brief} disabled={launch.locked} onChange={e => setBrief(e.target.value)} /></label>
    <button disabled={launch.blockedFor("quick", true)} onClick={() => launch.mutate("quick")}>Otomatis</button>
    <button disabled={launch.blockedFor("reviewed", true)} onClick={() => launch.mutate("reviewed")}>Manual</button>
    {launch.isError && <p role="alert">{launch.error.message}</p>}{done && <p>Selesai</p>}</>;
}
function mount() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}><Harness /></QueryClientProvider>);
}

describe("project launch identity", () => {
  it.each(["Otomatis", "Manual"])("freezes %s input and nonce on ambiguous failure", async label => {
    const calls: { key: string | null; body: unknown; url: string }[] = [];
    server.use(http.post(/\/backend\/api\/v1\/business\/projects\/p\/(quick-analysis|analyses)$/, async ({ request }) => {
      calls.push({ key: request.headers.get("Idempotency-Key"), body: await request.json(), url: request.url });
      return calls.length === 1 ? HttpResponse.json({ message: "Status run belum pasti" }, { status: 503 }) : HttpResponse.json({ id: "saved" }, { status: 202 });
    }));
    mount();
    await userEvent.click(screen.getByRole("button", { name: label }));
    await screen.findByText("Status run belum pasti");
    expect(screen.getByLabelText("Brief")).toBeDisabled();
    expect(screen.getByRole("button", { name: label === "Otomatis" ? "Manual" : "Otomatis" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: label }));
    await screen.findByText("Selesai");
    expect(calls).toHaveLength(2); expect(calls[0]).toEqual(calls[1]);
  });

  it("releases input only after a definite rejection and waits for an explicit new action", async () => {
    const calls: { key: string | null; body: Record<string, unknown> }[] = [];
    server.use(http.post("/backend/api/v1/business/projects/p/quick-analysis", async ({ request }) => {
      calls.push({ key: request.headers.get("Idempotency-Key"), body: await request.json() as Record<string, unknown> });
      return calls.length === 1 ? HttpResponse.json({ error: { code: "revision_conflict", message: "Input ditolak" } }, { status: 409 }) : HttpResponse.json({ id: "saved" }, { status: 202 });
    }));
    mount(); await userEvent.click(screen.getByRole("button", { name: "Otomatis" }));
    await screen.findByText("Input ditolak"); expect(calls).toHaveLength(1);
    const field = screen.getByLabelText("Brief"); expect(field).toBeEnabled();
    await userEvent.clear(field); await userEvent.type(field, "Brief publik yang direvisi setelah penolakan pasti.");
    await userEvent.click(screen.getByRole("button", { name: "Otomatis" })); await screen.findByText("Selesai");
    expect(calls[0].key).not.toBe(calls[1].key); expect(calls[1].body.expected_revision).toBe(2);
    expect(calls[1].body.public_brief).toBe("Brief publik yang direvisi setelah penolakan pasti.");
  });
});
