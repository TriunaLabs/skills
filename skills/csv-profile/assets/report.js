(() => {
  "use strict";
  const report = JSON.parse(document.getElementById("profile-data").textContent || "{}");
  const $ = (id) => document.getElementById(id);
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  };
  const format = (value) => new Intl.NumberFormat().format(value ?? 0);
  const pct = (value) => `${Number(value || 0).toFixed(value % 1 ? 1 : 0)}%`;
  const display = (value) => value === null || value === undefined ? "—" : String(value);
  const summary = report.summary;

  document.title = `${report.source.name} · CSV quality report`;
  $("report-title").textContent = report.source.name;
  $("report-meta").textContent = `${format(summary.rows)} rows · ${format(summary.columns)} columns · ${(report.source.bytes / 1024).toFixed(1)} KB · ${report.source.encoding}`;
  $("quality-score").textContent = summary.quality_score;
  $("quality-status").textContent = summary.status;
  $("quality-note").textContent = `${summary.issue_groups} grouped finding${summary.issue_groups === 1 ? "" : "s"}`;
  document.querySelector(".score-ring").style.setProperty("--score", summary.quality_score);
  $("generated-at").textContent = `Generated ${new Date(report.generated_at).toLocaleString()}`;

  const metrics = [
    ["ROWS", format(summary.rows), "records observed"],
    ["COLUMNS", format(summary.columns), `${report.columns.filter((item) => item.key_candidate).length} key candidate(s)`],
    ["COMPLETENESS", pct(100 - summary.missing_percent), `${format(summary.missing)} null-like cells`],
    ["DUPLICATES", format(summary.duplicate_rows), pct(summary.rows ? summary.duplicate_rows / summary.rows * 100 : 0)],
    ["TYPE ISSUES", format(summary.mixed_type_values), "non-dominant values"],
    ["ROW SHAPE", format(summary.width_issues), "width mismatches"],
  ];
  metrics.forEach(([label, value, note]) => {
    const item = node("article", undefined, "metric");
    item.append(node("span", label), node("strong", value), node("small", note));
    $("metrics").append(item);
  });

  function renderIssues(severity = "all") {
    const items = severity === "all" ? report.issues : report.issues.filter((item) => item.severity === severity);
    $("issue-list").replaceChildren();
    if (!items.length) {
      $("issue-list").append(node("p", "No findings at this severity.", "empty"));
      return;
    }
    items.forEach((item) => {
      const card = node("article", undefined, "issue");
      card.append(node("i", undefined, `severity ${item.severity}`));
      const copy = node("div");
      copy.append(node("strong", `${item.kind}${item.column ? ` · ${item.column}` : ""}`), node("p", item.detail));
      card.append(copy, node("span", format(item.count), "issue-count"));
      $("issue-list").append(card);
    });
  }
  renderIssues();
  document.querySelectorAll("[data-severity]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-severity]").forEach((peer) => peer.setAttribute("aria-pressed", String(peer === button)));
    renderIssues(button.dataset.severity);
  }));

  Object.entries(report.methodology.score_deductions).forEach(([label, points]) => {
    const wrap = node("div", undefined, "deduction");
    const head = node("div", undefined, "deduction-head");
    head.append(node("span", label), node("strong", `−${points}`));
    const track = node("div", undefined, "track");
    const bar = node("i");
    bar.style.width = `${Math.min(100, Number(points) / 35 * 100)}%`;
    track.append(bar);
    wrap.append(head, track);
    $("deductions").append(wrap);
  });

  function signal(column) {
    const denominator = Math.max(1, summary.rows * 3);
    return Math.max(0, 100 - Math.min(100, column.issue_count / denominator * 100));
  }
  function openColumn(column) {
    $("dialog-title").textContent = column.name;
    $("dialog-body").replaceChildren();
    const grid = node("div", undefined, "detail-grid");
    const stats = [
      ["INFERRED TYPE", column.inferred_type], ["COMPLETE", pct(100 - column.missing_percent)],
      ["DISTINCT", `${column.unique_is_lower_bound ? "≥" : ""}${format(column.unique)}`],
      ["TYPE ISSUES", format(column.type_issues)], ["WHITESPACE", format(column.whitespace)],
      ["KEY CANDIDATE", column.key_candidate ? "Yes" : "No"],
    ];
    stats.forEach(([label, value]) => {
      const stat = node("div", undefined, "detail-stat");
      stat.append(node("span", label), node("strong", value));
      grid.append(stat);
    });
    $("dialog-body").append(grid);
    const types = node("div", undefined, "distribution");
    types.append(node("h3", "Observed value types"));
    const typeList = node("div", undefined, "token-list");
    Object.entries(column.type_counts).forEach(([kind, count]) => typeList.append(node("span", `${kind} · ${format(count)}`)));
    types.append(typeList);
    $("dialog-body").append(types);
    if (column.numeric) {
      const distribution = node("div", undefined, "distribution");
      distribution.append(node("h3", `Numeric distribution · ${format(column.numeric.sample_size)} sampled`));
      const quartiles = node("div", undefined, "quartiles");
      [["MIN", column.numeric.min], ["Q1", column.numeric.q1], ["MEDIAN", column.numeric.median], ["Q3", column.numeric.q3], ["MAX", column.numeric.max]].forEach(([label, value]) => {
        const q = node("div"); q.append(node("span", label), node("strong", display(value))); quartiles.append(q);
      });
      distribution.append(quartiles, node("p", `${format(column.numeric.outliers)} values fall outside the 1.5× IQR fences.`, "subtle"));
      $("dialog-body").append(distribution);
    }
    if (column.case_or_spacing_variants.length) {
      const variants = node("div", undefined, "distribution");
      variants.append(node("h3", "Case or spacing variants"));
      const list = node("ul", undefined, "variants");
      column.case_or_spacing_variants.forEach((variant) => {
        const item = node("li");
        item.append(document.createTextNode(`${variant.count} occurrences normalize to `), node("code", variant.normalized), document.createTextNode(`: ${variant.values.join(" · ")}`));
        list.append(item);
      });
      variants.append(list); $("dialog-body").append(variants);
    }
    $("column-dialog").showModal();
  }
  function renderColumns(query = "") {
    const normalized = query.trim().toLowerCase();
    const columns = report.columns.filter((column) => `${column.name} ${column.inferred_type}`.toLowerCase().includes(normalized));
    $("column-table").replaceChildren();
    columns.forEach((column) => {
      const row = node("tr");
      const nameCell = node("td"); nameCell.append(node("strong", column.name));
      const signalCell = node("td"); const track = node("div", undefined, "signal"); const bar = node("i"); bar.style.width = `${signal(column)}%`; track.append(bar); signalCell.append(track);
      const typeCell = node("td"); typeCell.append(node("span", column.inferred_type, "type"));
      const complete = node("td", pct(100 - column.missing_percent));
      const unique = node("td", `${column.unique_is_lower_bound ? "≥" : ""}${format(column.unique)}`);
      const issues = node("td", format(column.issue_count));
      const action = node("td"); const button = node("button", "Inspect ↗", "inspect"); button.type = "button"; button.setAttribute("aria-label", `Inspect ${column.name}`); button.addEventListener("click", () => openColumn(column)); action.append(button);
      row.append(nameCell, signalCell, typeCell, complete, unique, issues, action); $("column-table").append(row);
    });
    $("column-empty").hidden = columns.length > 0;
  }
  renderColumns();
  $("column-search").addEventListener("input", (event) => renderColumns(event.target.value));

  if (report.semantic_review) {
    const review = report.semantic_review;
    const threshold = Number(review.policy.confidence_threshold || 0);
    $("semantic").hidden = false;
    $("semantic-nav").hidden = false;
    $("semantic-summary").textContent = `${review.columns.length} columns reviewed · ${(threshold * 100).toFixed(0)}% confidence gate · ${review.policy.mode}`;
    review.columns.forEach((item) => {
      const card = node("article", undefined, "semantic-card");
      const head = node("div", undefined, "semantic-card-head");
      head.append(node("strong", item.name), node("span", item.gate === "accepted" ? "ACCEPTED" : "REVIEW", `gate ${item.gate}`));
      const decisions = node("div", undefined, "decision-pair");
      [["SUGGESTED ROLE", item.semantic_role], ["REVIEW PRIORITY", item.review_priority]].forEach(([label, decision]) => {
        const block = node("div", undefined, "decision");
        block.append(node("span", label), node("strong", decision.label));
        const meter = node("div", undefined, "confidence");
        const fill = node("i"); fill.style.width = `${Math.max(0, Math.min(100, decision.confidence * 100))}%`; meter.append(fill);
        block.append(meter, node("small", `${(decision.confidence * 100).toFixed(1)}% confidence`));
        decisions.append(block);
      });
      card.append(head, decisions);
      $("semantic-cards").append(card);
    });
    $("semantic-model").textContent = `${review.engine.name} · ${review.engine.model}`;
    $("semantic-privacy").textContent = review.privacy.raw_values_sent ? "Raw values transmitted" : "Aggregate profile only · no raw values sent";
  }

  $("privacy-copy").textContent = report.privacy.values_included
    ? `Values are included for up to ${format(report.privacy.row_sample_limit)} sampled issue rows. Keep this report private if the CSV is sensitive.`
    : `Values are excluded. This view shows row numbers and issue labels for up to ${format(report.privacy.row_sample_limit)} rows.`;
  if (!report.row_samples.length && !report.width_issue_samples.length) {
    $("row-samples").append(node("p", "No sampled row-level issues were found.", "empty"));
  }
  report.width_issue_samples.forEach((sample) => {
    const card = node("article", undefined, "row-card");
    const summaryNode = node("div", undefined, "row-summary");
    summaryNode.append(node("strong", `ROW ${format(sample.row)}`), node("span", `Expected ${sample.expected} fields · found ${sample.actual}`, "chip"));
    card.append(summaryNode); $("row-samples").append(card);
  });
  report.row_samples.forEach((sample) => {
    const card = node("article", undefined, "row-card");
    const summaryNode = node("div", undefined, "row-summary");
    summaryNode.append(node("strong", `ROW ${format(sample.row)}`));
    const chips = node("div", undefined, "chips");
    sample.issues.slice(0, 8).forEach((issue) => chips.append(node("span", `${issue.column || "unnamed"}: ${issue.issue}`, "chip")));
    summaryNode.append(chips); card.append(summaryNode);
    if (sample.values) {
      const values = node("div", undefined, "row-values");
      const list = node("dl");
      report.columns.forEach((column, index) => { list.append(node("dt", column.name), node("dd", sample.values[index] || "∅")); });
      values.append(list); card.append(values);
    }
    $("row-samples").append(card);
  });

  const rules = [["Type detection", report.methodology.type_detection], ["Numeric outliers", report.methodology.numeric_outliers], ["Value exposure", report.privacy.values_included ? "Sampled issue-row values included." : "Raw values excluded from this report."]];
  rules.forEach(([term, description]) => $("method-rules").append(node("dt", term), node("dd", description)));
  report.methodology.limits.forEach((limit) => $("method-limits").append(node("li", limit)));
  report.methodology.null_tokens.forEach((token) => $("null-tokens").append(node("span", token === "" ? "empty string" : token)));

  $("dialog-close").addEventListener("click", () => $("column-dialog").close());
  $("print-report").addEventListener("click", () => window.print());
  $("theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("csv-profile-theme", next); } catch (_) { /* local file restrictions */ }
  });
  try {
    const saved = localStorage.getItem("csv-profile-theme");
    if (saved === "dark" || saved === "light") document.documentElement.dataset.theme = saved;
  } catch (_) { /* local file restrictions */ }
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) {
      document.querySelectorAll(".rail a").forEach((link) => link.classList.toggle("active", link.dataset.section === entry.target.id));
    }
  }), { rootMargin: "-20% 0px -70%", threshold: 0 });
  document.querySelectorAll(".report-section").forEach((section) => observer.observe(section));
})();
