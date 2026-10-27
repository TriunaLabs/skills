/** Constrain a public URL render to pinned, same-origin GET responses. */
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const FETCHER = join(dirname(fileURLToPath(import.meta.url)), 's2c_safe_browser_fetch.py');
const MAX_REQUESTS = 50;
const MAX_TOTAL_BYTES = 12_000_000;

export function allowedResource(base, candidate, method = 'GET') {
  try {
    const start = new URL(base);
    const request = new URL(candidate);
    return ['http:', 'https:'].includes(start.protocol) && request.origin === start.origin &&
      !start.username && !start.password && !request.username && !request.password &&
      [80, 443].includes(Number(request.port || (request.protocol === 'https:' ? 443 : 80))) &&
      method === 'GET';
  } catch {
    return false;
  }
}

export function makePublicGuard(base, python) {
  if (!allowedResource(base, base)) throw new Error('Public capture needs an HTTP(S) URL on port 80 or 443');
  let requests = 0;
  let totalBytes = 0;
  const blocked = { origin: 0, method: 0, budget: 0, fetch: 0 };
  return {
    blocked,
    async handle(route) {
      const request = route.request();
      const url = request.url();
      const method = request.method();
      if (!allowedResource(base, url, method)) {
        blocked[method === 'GET' ? 'origin' : 'method']++;
        await route.abort();
        return;
      }
      if (++requests > MAX_REQUESTS || totalBytes >= MAX_TOTAL_BYTES) {
        blocked.budget++;
        await route.abort();
        return;
      }
      try {
        const { stdout } = await execute(python, [FETCHER, url], {
          timeout: 12_000, maxBuffer: 3_500_000, windowsHide: true,
        });
        const response = JSON.parse(stdout);
        if (!Number.isInteger(response.status) || response.status < 100 || response.status > 599) {
          throw new Error('Invalid upstream status');
        }
        const body = Buffer.from(response.body_base64, 'base64');
        if (totalBytes + body.length > MAX_TOTAL_BYTES) {
          blocked.budget++;
          await route.abort();
          return;
        }
        totalBytes += body.length;
        await route.fulfill({ status: response.status, headers: response.headers, body });
      } catch {
        blocked.fetch++;
        await route.abort();
      }
    },
    stats() { return { requests, fetched_bytes: totalBytes, blocked: { ...blocked } }; },
  };
}
