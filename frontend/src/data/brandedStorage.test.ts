import { afterEach, describe, expect, it, vi } from "vitest";
import { readBrandedStorage, removeBrandedStorage } from "./brandedStorage";
import { setAuthStorageNamespace } from "../auth/storageNamespace";
import { createWorkflowSession, loadWorkflowSession } from "../pages/SimulationWorkflow/workflowSession";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  setAuthStorageNamespace(null);
});

describe("PAKAR browser storage compatibility", () => {
  it("restores an existing workflow only for its original account", () => {
    const session = createWorkflowSession("sim-existing", "Existing project");
    session.currentStep = 3;
    const oldKey = "rekakebijakan-workflow-v2:sim-existing:owner";
    localStorage.setItem(oldKey, JSON.stringify(session));
    setAuthStorageNamespace("someone-else");
    expect(loadWorkflowSession("sim-existing")).toBeNull();
    expect(localStorage.getItem(oldKey)).not.toBeNull();
    setAuthStorageNamespace("owner");
    expect(loadWorkflowSession("sim-existing")?.currentStep).toBe(3);
    expect(localStorage.getItem("pakar-workflow-v2:sim-existing:owner")).not.toBeNull();
    expect(localStorage.getItem(oldKey)).toBeNull();
  });

  it("prefers new data when both names exist", () => {
    localStorage.setItem("pakar-workspace-v1:owner", "new");
    localStorage.setItem("rekakebijakan-workspace-v1:owner", "old");
    expect(readBrandedStorage(localStorage, "pakar-workspace-v1:owner")).toBe("new");
  });

  it("keeps old data readable when migration cannot write", () => {
    const oldKey = "rekakebijakan-project-intake:sim:owner";
    localStorage.setItem(oldKey, "saved intake");
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
    expect(readBrandedStorage(localStorage, "pakar-project-intake:sim:owner")).toBe("saved intake");
    expect(localStorage.getItem(oldKey)).toBe("saved intake");
  });

  it("clears both names so an old presentation cannot reappear", () => {
    sessionStorage.setItem("pakar-quick-presentation:sim", "new");
    sessionStorage.setItem("rekakebijakan-quick-presentation:sim", "old");
    removeBrandedStorage(sessionStorage, "pakar-quick-presentation:sim");
    expect(readBrandedStorage(sessionStorage, "pakar-quick-presentation:sim")).toBeNull();
  });
});
