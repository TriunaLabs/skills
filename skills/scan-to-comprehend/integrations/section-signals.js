/* S2C section signals: opt-in, in-memory, first-party observation. No network calls. */
(function (root) {
  "use strict";

  function start(options = {}) {
    const doc = root.document;
    if (!doc || !root.performance || typeof root.setInterval !== "function") {
      throw new Error("S2C section signals requires a browser document.");
    }

    const sampleMs = options.sampleMs ?? 250;
    const idleMs = options.idleMs ?? 30000;
    const minVisibleFraction = options.minVisibleFraction ?? 0.25;
    if (!Number.isFinite(sampleMs) || sampleMs < 100 || !Number.isFinite(idleMs) || idleMs < 1000 ||
        !Number.isFinite(minVisibleFraction) || minVisibleFraction <= 0 || minVisibleFraction > 1) {
      throw new Error("Invalid S2C section signals timing or visibility option.");
    }

    const elements = Array.from(doc.querySelectorAll("[data-s2c-section]"));
    if (!elements.length) throw new Error("Mark at least one section with data-s2c-section.");
    const records = new Map();
    const ids = new Set();
    for (const element of elements) {
      const id = (element.getAttribute("data-s2c-section") || "").trim();
      if (!id || ids.has(id)) throw new Error("Each data-s2c-section needs a unique, nonempty ID.");
      ids.add(id);
      records.set(element, { id, visibleMs: 0, hoverMs: 0, mouseClicks: 0, touchTaps: 0, hovered: false });
    }

    const now = () => root.performance.now();
    let lastSample = now();
    let lastActivity = lastSample;
    let lastMouseMove = -Infinity;
    let activeMs = 0;
    let mouseSeen = false;
    let touchSeen = false;
    let lastPointerUp = null;
    let stopped = false;

    function viewport() {
      return {
        width: doc.documentElement.clientWidth || root.innerWidth,
        height: doc.documentElement.clientHeight || root.innerHeight
      };
    }

    function visibleEnough(element, size) {
      const box = element.getBoundingClientRect();
      const width = Math.max(0, Math.min(box.right, size.width) - Math.max(box.left, 0));
      const height = Math.max(0, Math.min(box.bottom, size.height) - Math.max(box.top, 0));
      const reference = Math.min(Math.max(0, box.width * box.height), size.width * size.height);
      return reference > 0 && (width * height) / reference >= minVisibleFraction;
    }

    function sample() {
      if (stopped) return;
      const at = now();
      const elapsed = Math.min(1000, Math.max(0, at - lastSample));
      lastSample = at;
      if (doc.hidden || (typeof doc.hasFocus === "function" && !doc.hasFocus()) || at - lastActivity > idleMs) return;
      activeMs += elapsed;
      const size = viewport();
      for (const [element, record] of records) {
        if (!visibleEnough(element, size)) continue;
        record.visibleMs += elapsed;
        if (record.hovered && at - lastMouseMove <= 5000) record.hoverMs += elapsed;
      }
    }

    function activity() { lastActivity = now(); }
    function pointerMove(event) {
      activity();
      if (event.pointerType === "mouse") {
        mouseSeen = true;
        lastMouseMove = now();
      } else if (event.pointerType === "touch") touchSeen = true;
    }
    function pointerUp(event) {
      sample();
      activity();
      lastPointerUp = null;
      if (event.pointerType === "mouse") mouseSeen = true;
      if (event.pointerType === "touch") touchSeen = true;
      if (event.pointerType !== "mouse" && event.pointerType !== "touch") return;
      if (event.pointerType === "mouse" && event.button !== 0) return;
      const element = event.target && typeof event.target.closest === "function"
        ? event.target.closest("[data-s2c-section]") : null;
      lastPointerUp = { element, type: event.pointerType, at: now() };
    }
    function click(event) {
      if (!lastPointerUp) return;
      if (now() - lastPointerUp.at > 700) {
        lastPointerUp = null;
        return;
      }
      const element = event.target && typeof event.target.closest === "function"
        ? event.target.closest("[data-s2c-section]") : null;
      if (element !== lastPointerUp.element) {
        lastPointerUp = null;
        return;
      }
      const record = records.get(element);
      if (record) {
        if (lastPointerUp.type === "mouse") record.mouseClicks += 1;
        else record.touchTaps += 1;
      }
      lastPointerUp = null;
    }

    const hoverHandlers = new Map();
    for (const element of elements) {
      const record = records.get(element);
      const enter = (event) => {
        if (event.pointerType !== "mouse") return;
        sample();
        activity();
        mouseSeen = true;
        lastMouseMove = now();
        record.hovered = true;
      };
      const leave = (event) => {
        if (event.pointerType !== "mouse") return;
        sample();
        record.hovered = false;
      };
      element.addEventListener("pointerenter", enter);
      element.addEventListener("pointerleave", leave);
      hoverHandlers.set(element, { enter, leave });
    }
    doc.addEventListener("pointermove", pointerMove, { passive: true });
    doc.addEventListener("pointerup", pointerUp, { passive: true });
    doc.addEventListener("click", click, { passive: true });
    doc.addEventListener("keydown", activity, { passive: true });
    root.addEventListener("scroll", activity, { passive: true });
    const resetClock = () => { lastSample = now(); };
    root.addEventListener("focus", resetClock);
    root.addEventListener("blur", resetClock);
    doc.addEventListener("visibilitychange", resetClock);
    const timer = root.setInterval(sample, sampleMs);

    function snapshot() {
      sample();
      const size = viewport();
      return {
        schema: "s2c-section-signals/v1",
        capturedOn: new Date().toISOString().slice(0, 10),
        pageLabel: String(options.pageLabel || "").slice(0, 120),
        basis: "foreground, recently active viewport exposure and pointer events",
        sampleMs,
        idleMs,
        minVisibleFraction,
        viewport: size,
        activeMs: Math.round(activeMs),
        mouseSeen,
        touchSeen,
        sections: Array.from(records.values(), (record) => ({
          id: record.id,
          visibleMs: Math.round(record.visibleMs),
          hoverMs: Math.round(record.hoverMs),
          mouseClicks: record.mouseClicks,
          touchTaps: record.touchTaps
        }))
      };
    }

    function stop() {
      const result = snapshot();
      stopped = true;
      root.clearInterval(timer);
      doc.removeEventListener("pointermove", pointerMove);
      doc.removeEventListener("pointerup", pointerUp);
      doc.removeEventListener("click", click);
      doc.removeEventListener("keydown", activity);
      root.removeEventListener("scroll", activity);
      root.removeEventListener("focus", resetClock);
      root.removeEventListener("blur", resetClock);
      doc.removeEventListener("visibilitychange", resetClock);
      for (const [element, handlers] of hoverHandlers) {
        element.removeEventListener("pointerenter", handlers.enter);
        element.removeEventListener("pointerleave", handlers.leave);
      }
      return result;
    }

    function download() {
      const json = JSON.stringify(snapshot(), null, 2);
      const url = root.URL.createObjectURL(new root.Blob([json], { type: "application/json" }));
      const link = doc.createElement("a");
      link.href = url;
      link.download = "s2c-section-signals.json";
      link.click();
      root.setTimeout(() => root.URL.revokeObjectURL(url), 0);
    }

    return { snapshot, stop, download };
  }

  const api = { start };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root.document) root.S2CSignals = api;
})(typeof window !== "undefined" ? window : globalThis);
