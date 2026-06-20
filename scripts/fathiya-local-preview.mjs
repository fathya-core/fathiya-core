import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize, relative, resolve } from "node:path";
import serverBuild from "../dist/server/index.js";

const port = Number(process.env.PORT || process.env.FATHIYA_WEB_PORT || 5180);
const host = process.env.HOST || process.env.FATHIYA_WEB_HOST || "127.0.0.1";
const apiTarget = process.env.FATHIYA_API_URL || "http://127.0.0.1:8765";
const clientRoot = resolve("dist/client");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function isInside(base, candidate) {
  const rel = relative(base, candidate);
  return rel === "" || (!rel.startsWith("..") && !rel.startsWith("/"));
}

function sendResponse(res, response) {
  res.statusCode = response.status;
  res.statusMessage = response.statusText;
  response.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "content-encoding") {
      res.setHeader(key, value);
    }
  });
  return response.arrayBuffer().then((buffer) => {
    res.end(Buffer.from(buffer));
  });
}

async function proxyApi(req, res, pathname) {
  const upstream = new URL(pathname + (new URL(req.url, `http://${host}:${port}`).search || ""), apiTarget);
  const headers = new Headers(req.headers);
  headers.delete("host");
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : req;
  const response = await fetch(upstream, {
    method: req.method,
    headers,
    body,
    duplex: body ? "half" : undefined,
  });
  await sendResponse(res, response);
}

function serveStatic(req, res, pathname) {
  const decoded = decodeURIComponent(pathname);
  const target = normalize(join(clientRoot, decoded));
  if (!isInside(clientRoot, target) || !existsSync(target) || !statSync(target).isFile()) {
    return false;
  }
  res.statusCode = 200;
  res.setHeader("content-type", contentTypes[extname(target)] || "application/octet-stream");
  createReadStream(target).pipe(res);
  return true;
}

createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${host}:${port}`);
    if (url.pathname.startsWith("/api/")) {
      await proxyApi(req, res, url.pathname);
      return;
    }
    if (serveStatic(req, res, url.pathname)) {
      return;
    }
    const request = new Request(url, {
      method: req.method,
      headers: req.headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : req,
      duplex: req.method === "GET" || req.method === "HEAD" ? undefined : "half",
    });
    await sendResponse(res, await serverBuild.fetch(request));
  } catch (error) {
    res.statusCode = 500;
    res.setHeader("content-type", "text/plain; charset=utf-8");
    res.end(error instanceof Error ? error.stack || error.message : String(error));
  }
}).listen(port, host, () => {
  console.log(`FATHIYA local preview ready at http://${host}:${port}`);
  console.log(`Proxying /api to ${apiTarget}`);
});
