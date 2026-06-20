// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, cloudflare (build-only),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... } }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import { copyFileSync, cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

function copyOperatorLiteToClientDist() {
  const source = resolve("operator-lite");
  const clientDist = resolve("dist/client");
  if (!existsSync(source) || !existsSync(clientDist)) return;

  const destination = resolve(clientDist, "operator-lite");
  rmSync(destination, { force: true, recursive: true });
  cpSync(source, destination, { recursive: true });

  const operatorIndex = resolve(source, "agent-tasks", "index.html");
  if (!existsSync(operatorIndex)) return;

  for (const route of ["agent-tasks", "command-center", "ai-console"]) {
    const routeDir = resolve(clientDist, route);
    mkdirSync(routeDir, { recursive: true });
    copyFileSync(operatorIndex, resolve(routeDir, "index.html"));
  }
  copyFileSync(operatorIndex, resolve(clientDist, "404.html"));
}

export default defineConfig({
  vite: {
    plugins: [
      {
        name: "fathiya-copy-operator-lite",
        apply: "build",
        closeBundle() {
          copyOperatorLiteToClientDist();
        },
      },
    ],
  },
});
