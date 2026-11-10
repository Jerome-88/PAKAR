import { expect, it } from "vitest";
import { forgetBusinessProject, rememberBusinessProject } from "./businessWorkspace";

it("does not resurrect a deleted project when an older GET finishes late", () => {
  const id = "business_deleted_cache_race";
  rememberBusinessProject(id);
  forgetBusinessProject(id);
  rememberBusinessProject(id);
  expect(JSON.parse(localStorage.getItem("pakar:workspace-projects:v1") ?? "[]")).not.toContain(id);
});
