import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ApiError } from "../../api/client";
import { startBusinessAnalysis, startQuickBusinessAnalysis } from "../../api/business";
import type { BusinessAnalysis } from "../../api/business";

export function definitiveLaunchRejection(error: unknown) {
  return error instanceof ApiError && ["revision_conflict", "public_brief_required", "invalid_analysis", "analysis_unavailable", "validation_error"].includes(error.code ?? "");
}

type Mode = "quick" | "reviewed";
type Launch = { mode: Mode; key: string; projectId: string; revision: number; engine: "oasis" | "fixture"; rounds: number; brief: string };

export function useBusinessLaunch(input: Omit<Launch, "mode" | "key"> & { onSuccess: (row: BusinessAnalysis) => void; onRejected: () => void }) {
  const request = useRef<Launch | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [frozen, setFrozen] = useState(false);
  const mutation = useMutation({ mutationFn: (selected: Mode) => {
    request.current ??= { mode: selected, key: crypto.randomUUID(), projectId: input.projectId, revision: input.revision, engine: input.engine, rounds: selected === "quick" ? 3 : input.rounds, brief: input.brief };
    const saved = request.current;
    setMode(saved.mode); setFrozen(true);
    return saved.mode === "quick"
      ? startQuickBusinessAnalysis(saved.projectId, saved.revision, saved.engine, saved.rounds, saved.key, { public_brief: saved.brief })
      : startBusinessAnalysis(saved.projectId, saved.revision, saved.engine, saved.rounds, saved.key, saved.brief);
  }, onSuccess: input.onSuccess, onError: error => {
    if (definitiveLaunchRejection(error)) { request.current = null; setFrozen(false); input.onRejected(); }
  } });
  return { ...mutation, mode, frozen, locked: mutation.isPending || frozen,
    blockedFor: (selected: Mode, ready: boolean) => mutation.isPending || (frozen ? mode !== selected : !ready) };
}
