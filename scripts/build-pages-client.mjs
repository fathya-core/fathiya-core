import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { existsSync, mkdirSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import { build } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

const repoRoot = process.cwd();
const clientDist = resolve(repoRoot, "dist/client");
const assetsDir = resolve(clientDist, "assets");
const entryPath = resolve(repoRoot, "src/pages-client.tsx");

function removePreviousPagesAssets() {
  if (!existsSync(assetsDir)) return;

  for (const name of readdirSync(assetsDir)) {
    if (!name.startsWith("fathiya-pages-")) continue;
    rmSync(resolve(assetsDir, name), { force: true, recursive: true });
  }
}

function findLargestAsset(prefix, suffix) {
  if (!existsSync(assetsDir)) return null;

  return readdirSync(assetsDir)
    .filter((name) => name.startsWith(prefix) && name.endsWith(suffix))
    .map((name) => ({ name, size: statSync(resolve(assetsDir, name)).size }))
    .sort((a, b) => b.size - a.size)[0]?.name ?? null;
}

function createStaticAppHtml(assetPrefix, entryAsset, stylesAsset) {
  const stylesheet = stylesAsset
    ? `    <link rel="stylesheet" crossorigin href="${assetPrefix}/${stylesAsset}" />\n`
    : "";

  return `<!doctype html>
<html lang="ar" dir="rtl" class="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>FATHIYA - Smart Sovereign Platform</title>
    <meta
      name="description"
      content="FATHIYA private agent console for trading operations, bug bounty research, reporting, and local tool orchestration."
    />
    <meta name="author" content="FATHIYA" />
    <link
      rel="icon"
      href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23050d10'/%3E%3Cpath d='M32 9 50 16v14c0 12-7.5 21-18 25-10.5-4-18-13-18-25V16l18-7Z' fill='none' stroke='%2310f2a0' stroke-width='5'/%3E%3Cpath d='m24 32 5 5 12-13' fill='none' stroke='%23eafff6' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E"
    />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
    />
${stylesheet}    <script type="module" crossorigin src="${assetPrefix}/${entryAsset}"></script>
  </head>
  <body>
    <div id="root"></div>
    <noscript>FATHIYA requires JavaScript to run.</noscript>
  </body>
</html>
`;
}

function writeStaticAppShells() {
  const entryAsset = findLargestAsset("fathiya-pages-app-", ".js");
  if (!entryAsset) {
    throw new Error("FATHIYA Pages build could not find the static client entry asset.");
  }

  const stylesAsset = findLargestAsset("fathiya-pages-", ".css");
  const rootHtml = createStaticAppHtml("assets", entryAsset, stylesAsset);

  writeFileSync(resolve(clientDist, "index.html"), rootHtml);
  writeFileSync(resolve(clientDist, "404.html"), rootHtml);

  for (const route of ["agent-tasks", "command-center", "ai-console"]) {
    const routeDir = resolve(clientDist, route);
    mkdirSync(routeDir, { recursive: true });
    writeFileSync(resolve(routeDir, "index.html"), createStaticAppHtml("../assets", entryAsset, stylesAsset));
  }
}

removePreviousPagesAssets();

await build({
  appType: "custom",
  base: "./",
  configFile: false,
  envFile: false,
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  publicDir: false,
  root: repoRoot,
  build: {
    cssCodeSplit: true,
    emptyOutDir: false,
    outDir: clientDist,
    rollupOptions: {
      input: {
        "fathiya-pages-app": entryPath,
      },
      output: {
        assetFileNames: "assets/fathiya-pages-[name]-[hash][extname]",
        chunkFileNames: "assets/fathiya-pages-[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
      },
    },
  },
  resolve: {
    alias: {
      "@": resolve(repoRoot, "src"),
    },
    dedupe: ["react", "react-dom", "@tanstack/react-router"],
  },
});

writeStaticAppShells();
