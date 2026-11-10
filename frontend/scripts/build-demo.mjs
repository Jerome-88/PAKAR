import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const env = { ...process.env, VITE_PUBLIC_DEMO_ONLY: "true", VITE_API_URL: "" };
for (const args of [["node_modules/typescript/bin/tsc", "-b"], ["node_modules/vite/bin/vite.js", "build", "--outDir", "dist-demo"]]) {
  const result = spawnSync(process.execPath, args, { cwd: root, env, stdio: "inherit", windowsHide: true });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
