#!/usr/bin/env node
// Static file server for a scene folder (ES modules do not load from file://).
//   node serve.mjs <dir> [port]      → http://localhost:<port>/
// Also importable: const { url, close } = await serve(dir).
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };
export function serve(dir, port = 0) {
  const root = path.resolve(dir);
  const server = http.createServer((req, res) => {
    const p = path.join(root, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!p.startsWith(root)) { res.writeHead(403).end(); return; }
    const f = fs.existsSync(p) && fs.statSync(p).isDirectory() ? path.join(p, 'demo.html') : p;
    fs.readFile(f, (err, buf) => {
      if (err) { res.writeHead(404).end('not found'); return; }
      res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }).end(buf);
    });
  });
  return new Promise(ok => server.listen(port, '127.0.0.1', () => ok({ url: `http://127.0.0.1:${server.address().port}/`, close: () => server.close() })));
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { url } = await serve(process.argv[2] || '.', +(process.argv[3] || 8765));
  console.log(`serving ${path.resolve(process.argv[2] || '.')} at ${url}`);
}
