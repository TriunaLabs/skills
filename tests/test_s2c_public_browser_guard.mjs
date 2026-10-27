import assert from 'node:assert/strict';
import { test } from 'node:test';
import { allowedResource, makePublicGuard } from '../skills/scan-to-comprehend/scripts/s2c_public_browser_guard.mjs';

const BASE = 'https://example.com/path';

test('the public browser stays on one ordinary origin', () => {
  assert.equal(allowedResource(BASE, 'https://example.com/assets/app.css'), true);
  for (const candidate of [
    'http://example.com/', 'https://cdn.example.com/app.js', 'https://127.0.0.1/',
    'file:///etc/passwd', 'https://example.com:8443/', 'https://user@example.com/',
  ]) assert.equal(allowedResource(BASE, candidate), false, candidate);
  assert.equal(allowedResource(BASE, BASE, 'POST'), false);
  assert.throws(() => makePublicGuard('file:///tmp/page.html', 'python'));
});

test('route guard aborts cross-origin and mutating requests before fetching', async () => {
  const guard = makePublicGuard(BASE, 'python');
  const aborted = [];
  for (const [url, method] of [['https://127.0.0.1/private', 'GET'], [BASE, 'POST']]) {
    await guard.handle({ request: () => ({ url: () => url, method: () => method }),
      abort: async () => aborted.push(url) });
  }
  assert.equal(aborted.length, 2);
  assert.deepEqual(guard.stats().blocked, { origin: 1, method: 1, budget: 0, fetch: 0 });
});
