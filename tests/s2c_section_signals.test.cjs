const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../skills/scan-to-comprehend/integrations/section-signals.js'), 'utf8');

function fixture() {
  let time = 0;
  let tick;
  let cleared = false;
  const listeners = new Map();
  const elementListeners = new Map();
  const rect = { left: 0, top: 0, right: 100, bottom: 100, width: 100, height: 100 };
  function on(map, type, fn) { map.set(type, fn); }
  const element = {
    getAttribute: () => 'hero',
    getBoundingClientRect: () => rect,
    addEventListener(type, fn) { on(elementListeners, type, fn); },
    removeEventListener(type) { elementListeners.delete(type); }
  };
  const doc = {
    hidden: false,
    documentElement: { clientWidth: 100, clientHeight: 100 },
    hasFocus: () => true,
    querySelectorAll: () => [element],
    addEventListener(type, fn) { on(listeners, type, fn); },
    removeEventListener(type) { listeners.delete(type); }
  };
  const win = {
    document: doc,
    innerWidth: 100,
    innerHeight: 100,
    performance: { now: () => time },
    setInterval(fn) { tick = fn; return 1; },
    clearInterval() { cleared = true; },
    addEventListener(type, fn) { on(listeners, type, fn); },
    removeEventListener(type) { listeners.delete(type); }
  };
  vm.runInNewContext(source, { window: win });
  return {
    session: win.S2CSignals.start({ pageLabel: 'page-v1' }), doc, rect, element,
    advance(ms) { time += ms; tick(); },
    moveTime(ms) { time += ms; },
    dispatch(type, event = {}) { listeners.get(type)?.(event); },
    dispatchElement(type, event = {}) { elementListeners.get(type)?.(event); },
    wasCleared: () => cleared
  };
}

test('counts foreground viewport exposure and pauses for hidden, idle, and offscreen states', () => {
  const f = fixture();
  f.advance(250);
  assert.equal(f.session.snapshot().sections[0].visibleMs, 250);
  f.moveTime(50);
  f.doc.hidden = true;
  f.dispatch('visibilitychange');
  f.advance(250);
  assert.equal(f.session.snapshot().sections[0].visibleMs, 250);
  f.doc.hidden = false;
  f.dispatch('visibilitychange');
  f.advance(250);
  assert.equal(f.session.snapshot().sections[0].visibleMs, 500);
  f.advance(31000);
  assert.equal(f.session.snapshot().sections[0].visibleMs, 500);
  f.rect.top = 200;
  f.rect.bottom = 300;
  f.dispatch('scroll');
  f.advance(250);
  assert.equal(f.session.snapshot().sections[0].visibleMs, 500);
  f.session.stop();
  assert.equal(f.wasCleared(), true);
});

test('keeps mouse hover, mouse clicks, and touch taps separate without coordinates', () => {
  const f = fixture();
  f.moveTime(100);
  f.dispatchElement('pointerenter', { pointerType: 'mouse' });
  f.advance(250);
  f.moveTime(50);
  f.dispatch('pointerup', { pointerType: 'mouse', button: 0, target: { closest: () => f.element } });
  f.dispatch('click', { target: { closest: () => f.element } });
  f.advance(200);
  f.dispatchElement('pointerleave', { pointerType: 'mouse' });
  f.dispatch('pointerup', { pointerType: 'touch', target: { closest: () => f.element } });
  f.dispatch('click', { target: { closest: () => f.element } });
  const result = f.session.stop();
  assert.equal(result.sections[0].hoverMs, 500);
  assert.equal(result.sections[0].mouseClicks, 1);
  assert.equal(result.sections[0].touchTaps, 1);
  assert.equal(result.mouseSeen, true);
  assert.equal(result.touchSeen, true);
  assert.equal(JSON.stringify(result).includes('pointerX'), false);
});
