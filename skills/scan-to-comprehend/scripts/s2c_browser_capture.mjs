#!/usr/bin/env node
/** Capture a rendered page and Chromium's accessibility and keyboard paths. */
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';

const args = process.argv.slice(2);
const value = (flag, fallback) => {
  const index = args.indexOf(flag);
  return index < 0 ? fallback : args[index + 1];
};
const url = value('--url');
const htmlStdin = args.includes('--html-stdin');
const out = value('--out');
const auditDate = value('--audit-date', new Date().toISOString().slice(0, 10));
if (!out || (htmlStdin === Boolean(url)) || (url && !/^(https?:\/\/|file:\/\/)/.test(url))) {
  console.error('Usage: node s2c_browser_capture.mjs (--url https://example.com/ | --html-stdin) --out capture-dir');
  process.exit(2);
}
if (!/^\d{4}-\d{2}-\d{2}$/.test(auditDate) || Number.isNaN(Date.parse(`${auditDate}T00:00:00Z`))) {
  throw new Error('--audit-date must be YYYY-MM-DD');
}
const target = resolve(out);
let prototype = null;
if (htmlStdin) {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of process.stdin) {
    bytes += chunk.length;
    if (bytes > 2_000_000) throw new Error('HTML prototype exceeds 2 MB');
    chunks.push(chunk);
  }
  prototype = Buffer.concat(chunks).toString('utf8');
}
const viewports = [
  { id: 'desktop', width: 1265, height: 712 },
  { id: 'mobile', width: 375, height: 812 },
  { id: 'reflow-320', width: 320, height: 800 },
];
await mkdir(target, { recursive: true });
let browser;
try {
  browser = await chromium.launch({ channel: 'chrome', headless: true });
} catch {
  browser = await chromium.launch({ headless: true });
}
const frames = [];
try {
  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport, deviceScaleFactor: 1, reducedMotion: 'reduce',
      javaScriptEnabled: !htmlStdin, serviceWorkers: 'block' });
    const page = await context.newPage();
    if (htmlStdin) {
      await page.route('**/*', route => route.abort());
      await page.setContent(prototype, { waitUntil: 'domcontentloaded', timeout: 15000 });
    } else {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    }
    await page.locator('body').waitFor();
    await page.evaluate(() => document.fonts?.ready);
    await page.waitForTimeout(800);
    const capturedAt = new Date().toISOString();
    const image = `${viewport.id}.png`;
    await page.screenshot({ path: join(target, image), animations: 'disabled' });
    const dom = await page.evaluate(() => {
      const selector = 'h1,h2,h3,h4,h5,h6,p,a,button,input,select,textarea,img,[role],[tabindex],summary,[contenteditable],svg[role="img"]';
      const candidates = [...document.querySelectorAll(selector)];
      const backdrop = element => {
        for (let item = element; item; item = item.parentElement) {
          const style = getComputedStyle(item);
          if (style.backgroundImage !== 'none') return 'image';
          if (style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.backgroundColor !== 'transparent') return style.backgroundColor;
        }
        return 'unknown';
      };
      const nodes = candidates.map((element, index) => {
        const id = `n${String(index + 1).padStart(5, '0')}`;
        element.setAttribute('data-s2c-id', id);
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        const landmark = element.closest('main,nav,header,footer,aside,[role="main"],[role="navigation"],[role="banner"],[role="contentinfo"],[role="complementary"]');
        const visible = style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0 && box.width > 0 && box.height > 0;
        return {
          id, tag: element.tagName.toLowerCase(), role: element.getAttribute('role') || null,
          text: (element.innerText || '').trim().slice(0, 500), href: element.getAttribute('href'),
          alt: element.getAttribute('alt'), title: element.getAttribute('title'),
          aria_label: element.getAttribute('aria-label'), aria_hidden: element.closest('[aria-hidden="true"]') !== null,
          tabindex_attribute: element.getAttribute('tabindex'), dom_index: index + 1,
          box: { x: box.x, y: box.y, width: box.width, height: box.height },
          in_viewport: visible && box.bottom > 0 && box.right > 0 && box.top < innerHeight && box.left < innerWidth,
          visible, landmark: landmark?.getAttribute('role') || landmark?.tagName.toLowerCase() || null,
          heading_level: /^H[1-6]$/.test(element.tagName) ? Number(element.tagName[1]) : null,
          clipped_text: element.scrollWidth > element.clientWidth + 1 && style.overflowX !== 'visible' && Boolean(element.innerText?.trim()),
          style: { font_size: parseFloat(style.fontSize), font_weight: style.fontWeight, color: style.color,
            background: backdrop(element), line_height: style.lineHeight, text_transform: style.textTransform },
        };
      });
      return {
        nodes,
        anchor_ids: [...document.querySelectorAll('[id]')].map(item => item.id).filter(Boolean).slice(0, 5000),
        anchor_names: [...document.querySelectorAll('a[name]')].map(item => item.getAttribute('name')).filter(Boolean).slice(0, 5000),
        performance: (() => {
          const nav = performance.getEntriesByType('navigation')[0];
          const resources = performance.getEntriesByType('resource');
          return {
            basis: 'Single Chromium navigation in this audit environment; not field Core Web Vitals',
            ttfb_ms: nav && nav.responseStart > 0 ? Math.round(nav.responseStart - nav.requestStart) : null,
            dom_content_loaded_ms: nav?.domContentLoadedEventEnd ? Math.round(nav.domContentLoadedEventEnd) : null,
            load_event_ms: nav?.loadEventEnd ? Math.round(nav.loadEventEnd) : null,
            resource_count: resources.length,
            measured_transfer_bytes: resources.reduce((sum, item) => sum + (item.transferSize || 0), 0),
            measured_transfer_count: resources.filter(item => item.transferSize > 0).length,
          };
        })(),
        document_width: document.documentElement.scrollWidth,
        client_width: document.documentElement.clientWidth,
        head: { title: document.title, lang: document.documentElement.lang,
          meta_description: document.querySelector('meta[name="description"]')?.content || '',
          canonical: document.querySelector('link[rel="canonical"]')?.href || '',
          robots_meta: document.querySelector('meta[name="robots"]')?.content || '' },
      };
    });
    const cdp = await context.newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('Accessibility.enable');
    const root = (await cdp.send('DOM.getDocument', { depth: -1 })).root.nodeId;
    const { nodeIds } = await cdp.send('DOM.querySelectorAll', { nodeId: root, selector: '[data-s2c-id]' });
    const backendToId = new Map();
    for (const nodeId of nodeIds) {
      const described = await cdp.send('DOM.describeNode', { nodeId });
      const attributes = described.node.attributes || [];
      const at = attributes.indexOf('data-s2c-id');
      if (at >= 0) backendToId.set(described.node.backendNodeId, attributes[at + 1]);
    }
    const axNodes = (await cdp.send('Accessibility.getFullAXTree')).nodes;
    const byAxId = new Map(axNodes.map(node => [node.nodeId, node]));
    const visited = new Set();
    const axPath = [];
    const walk = node => {
      if (!node || visited.has(node.nodeId)) return;
      visited.add(node.nodeId);
      if (!node.ignored) {
        const role = node.role?.value || '';
        const name = node.name?.value || '';
        const id = backendToId.get(node.backendDOMNodeId) || null;
        if (name && role !== 'generic' && role !== 'InlineTextBox') {
          axPath.push({ index: axPath.length + 1, id, role, name: name.slice(0, 300) });
        }
      }
      for (const child of node.childIds || []) walk(byAxId.get(child));
    };
    walk(axNodes.find(node => node.role?.value === 'RootWebArea') || axNodes[0]);
    const nodeById = new Map(dom.nodes.map(node => [node.id, node]));
    for (const step of axPath) {
      const match = nodeById.get(step.id);
      if (match && match.a11y_index == null) {
        match.a11y_index = step.index;
        match.name = step.name;
        match.ax_role = step.role;
      }
    }
    // Keyboard traversal is observed in Chromium, including script-defined focus behavior.
    await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
    const focusPath = [];
    const seen = new Set();
    let focusStop = 'limit';
    for (let index = 1; index <= 250; index++) {
      await page.keyboard.press('Tab');
      const step = await page.evaluate(() => {
        const element = document.activeElement;
        if (!element || element === document.body) return null;
        const box = element.getBoundingClientRect();
        return { id: element.getAttribute('data-s2c-id'), tag: element.tagName.toLowerCase(),
          label: (element.getAttribute('aria-label') || element.innerText || element.getAttribute('title') || '').trim().slice(0, 200),
          box: { x: box.x, y: box.y, width: box.width, height: box.height } };
      });
      if (!step) { focusStop = 'body'; break; }
      const key = step.id || `${step.tag}:${step.label}:${Math.round(step.box.x)}:${Math.round(step.box.y)}`;
      if (seen.has(key)) { focusStop = 'cycle'; break; }
      seen.add(key);
      focusPath.push({ index, ...step });
      const match = nodeById.get(step.id);
      if (match) match.tab_index = index;
    }
    frames.push({ id: viewport.id, url: htmlStdin ? 'uploaded:prototype' : page.url(), captured_at: capturedAt,
      viewport: { width: viewport.width, height: viewport.height }, dpr: 1, image,
      ...dom, ax_path: axPath, focus_path: focusPath, focus_stop: focusStop,
      capture_basis: htmlStdin ? 'Inline HTML in Chromium with JavaScript disabled and external requests blocked' :
        'Chromium rendered DOM, CDP accessibility tree, observed Tab traversal',
      limitations: ['AX order is browser-reported, not a screen reader speech trace.',
        'Tab traversal may omit elements in shadow roots or cross-origin frames.',
        'A single viewport and state do not establish WCAG conformance.'] });
    await context.close();
  }
} finally {
  await browser.close();
}
const result = { schema: 's2c-browser-capture/v1', url: htmlStdin ? 'uploaded:prototype' : url,
  source_kind: htmlStdin ? 'html' : 'url', audited_on: auditDate, frames };
await writeFile(join(target, 'snapshot.json'), JSON.stringify(result, null, 2) + '\n');
console.log(join(target, 'snapshot.json'));
