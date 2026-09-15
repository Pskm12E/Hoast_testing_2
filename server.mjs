import { createServer } from "node:http";
import { readFile } from "node:fs/promises";

const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT ?? 3000);
const routes = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/index.html", ["index.html", "text/html; charset=utf-8"]],
  ["/notes", ["notes.html", "text/html; charset=utf-8"]],
  ["/notes.html", ["notes.html", "text/html; charset=utf-8"]],
  ["/styles.css", ["styles.css", "text/css; charset=utf-8"]],
  ["/app.js", ["app.js", "text/javascript; charset=utf-8"]],
  ["/favicon.svg", ["favicon.svg", "image/svg+xml"]],
]);
const headers = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "X-Frame-Options": "DENY",
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  "Cache-Control": "no-cache",
};

const server = createServer(async (request, response) => {
  if (!["GET", "HEAD"].includes(request.method)) {
    response.writeHead(405, { ...headers, Allow: "GET, HEAD" });
    response.end("Method not allowed");
    return;
  }
  let pathname;
  try {
    pathname = new URL(request.url, "http://localhost").pathname;
  } catch {
    response.writeHead(400, headers).end("Bad request");
    return;
  }
  const route = routes.get(pathname);
  if (!route) {
    response.writeHead(404, {
      ...headers,
      "Content-Type": "text/plain; charset=utf-8",
    });
    response.end(request.method === "HEAD" ? undefined : "Page not found");
    return;
  }
  try {
    const content = await readFile(
      new URL(`./public/${route[0]}`, import.meta.url),
    );
    response.writeHead(200, {
      ...headers,
      "Content-Type": route[1],
      "Content-Length": content.length,
    });
    response.end(request.method === "HEAD" ? undefined : content);
  } catch (error) {
    console.error("Unable to serve page:", error.message);
    response.writeHead(500, headers).end("Unable to load page");
  }
});

server.headersTimeout = 15000;
server.requestTimeout = 30000;
server.on("error", (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
server.listen(port, host, () =>
  console.log(
    `Little Notes is running at http://${host}:${server.address().port}`,
  ),
);
