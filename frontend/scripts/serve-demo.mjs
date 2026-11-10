import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { dirname, extname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import process from "node:process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../dist-demo");
const port = Number(process.env.DEMO_PORT ?? 4180);
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8", ".woff": "font/woff", ".woff2": "font/woff2", ".png": "image/png", ".ico": "image/x-icon" };

createServer(async (request, response) => {
  if (!["GET", "HEAD"].includes(request.method)) { response.writeHead(405, { Allow: "GET, HEAD" }); response.end(); return; }
  try {
    const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    const file = resolve(root, `.${pathname === "/" ? "/index.html" : pathname}`);
    const local = relative(root, file);
    if (local.startsWith("..") || local.split(/[\\/]/).some(part => part.startsWith("."))) throw new Error("outside-public-assets");
    if (!(await stat(file)).isFile()) throw new Error("not-a-file");
    const data = await readFile(file);
    response.writeHead(200, { "Content-Type": types[extname(file)] ?? "application/octet-stream", "X-Content-Type-Options": "nosniff", "Cache-Control": pathname.startsWith("/assets/") ? "public, max-age=31536000, immutable" : "no-cache" });
    response.end(request.method === "HEAD" ? undefined : data);
  } catch { response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }); response.end("Not found"); }
}).listen(port, "127.0.0.1", () => process.stdout.write(`Public demo preview: http://127.0.0.1:${port}\n`));
