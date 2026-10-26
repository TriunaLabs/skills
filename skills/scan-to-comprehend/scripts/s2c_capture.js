/* Run as a DevTools Snippet on a page you are authorized to inspect.
   Save a screenshot of the current viewport as screenshot.png in the same folder
   as the downloaded s2c-capture.json. No data is sent anywhere. */
(() => {
  const cssHex = (value) => {
    const match = /^rgba?\(\s*(\d+)[, ]+\s*(\d+)[, ]+\s*(\d+)(?:[, /]+\s*([\d.]+))?\s*\)$/i.exec(value || "");
    if (!match || (match[4] !== undefined && Number(match[4]) < 1)) return null;
    return "#" + [1, 2, 3].map((i) => Math.min(255, Number(match[i])).toString(16).padStart(2, "0")).join("");
  };
  const solidBackground = (node) => {
    for (let current = node; current; current = current.parentElement) {
      const style = getComputedStyle(current);
      if (style.backgroundImage !== "none") return null;
      const color = cssHex(style.backgroundColor);
      if (color) return color;
    }
    return null;
  };
  const kindFor = (node) => {
    const tag = node.tagName.toLowerCase();
    if (/^h[1-6]$/.test(tag)) return "heading";
    if (tag === "button" || node.getAttribute("role") === "button") return "button";
    if (tag === "a") {
      if (node.querySelector("img,svg") && /logo|brand/i.test(node.textContent + " " + (node.querySelector("img")?.alt || ""))) return "logo";
      return cssHex(getComputedStyle(node).backgroundColor) ? "button" : "link";
    }
    if (tag === "img" || tag === "svg") return /logo|brand/i.test(node.getAttribute("alt") || node.getAttribute("aria-label") || "") ? "logo" : "image";
    return "text";
  };
  const width = window.innerWidth, height = window.innerHeight;
  const elements = [];
  const nodes = document.querySelectorAll("h1,h2,h3,h4,h5,h6,p,a,button,img,svg[role=img],[role=button]");
  for (const node of nodes) {
    if (elements.length >= 500) break;
    if (node.matches("img,svg") && node.closest("a,button")) continue;
    if (node.matches("a") && node.closest("h1,h2,h3,h4,h5,h6")) continue;
    const style = getComputedStyle(node);
    if (style.display === "none" || style.visibility !== "visible" || Number(style.opacity) < 0.1) continue;
    const box = node.getBoundingClientRect();
    const x = Math.max(0, box.left), y = Math.max(0, box.top);
    const right = Math.min(width, box.right), bottom = Math.min(height, box.bottom);
    if (right - x < 5 || bottom - y < 5) continue;
    const kind = kindFor(node);
    const label = (node.innerText || node.getAttribute("alt") || node.getAttribute("aria-label") || kind)
      .replace(/\s+/g, " ").trim().slice(0, 120);
    const entry = {
      id: `e${elements.length + 1}`, kind, label,
      x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10,
      width: Math.round((right - x) * 10) / 10, height: Math.round((bottom - y) * 10) / 10,
      font_px: Math.max(1, parseFloat(style.fontSize) || 16),
    };
    const foreground = cssHex(style.color), background = solidBackground(node);
    if (foreground && background) Object.assign(entry, { foreground, background });
    elements.push(entry);
  }
  const payload = {
    schema: "s2c-attention-capture/v1",
    frames: [{
      id: "first-viewport", label: document.title || location.hostname,
      captured_at: new Date().toISOString(),
      image: "screenshot.png", coordinate_width: width, coordinate_height: height,
      provenance: "Browser DOM boxes and computed CSS colors; image backgrounds and faces were not analyzed",
      elements,
    }],
  };
  const objectUrl = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = objectUrl; link.download = "s2c-capture.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  console.info(`S2C captured ${elements.length} visible elements; save the viewport screenshot beside s2c-capture.json as screenshot.png.`);
})();
