const $ = selector => document.querySelector(selector);
const form = $('#run-form');
const runButton = $('#run-button');
const applyButton = $('#apply-profile');
const sourceChoices = document.querySelectorAll('input[name="source-kind"]');
function sourceKind() { return document.querySelector('input[name="source-kind"]:checked').value; }
function selectSource(kind) {
  document.querySelector(`input[name="source-kind"][value="${kind}"]`).checked = true;
  $('#url-source').hidden = kind !== 'url';
  $('#html-source').hidden = kind !== 'html';
  $('#url').required = kind === 'url';
  $('#html-file').required = kind === 'html';
}
sourceChoices.forEach(choice => choice.addEventListener('change', () => selectSource(sourceKind())));
let activeRun = null;
let baselineResult = null;
let reportUrl = null;
let defaults = null;
let labels = null;

async function json(response) {
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || `Request failed (${response.status}).`);
  return value;
}

function show(id, state) {
  for (const name of ['empty-state', 'progress', 'error', 'result']) $(`#${name}`).hidden = name !== id;
  $('#state-pill').textContent = state;
  $('#state-pill').dataset.state = state.toLowerCase();
}

function profileError(message) {
  $('#profile-error').textContent = message;
  $('#profile-error').hidden = !message;
  if (message) $('#rubric-editor').open = true;
}

function updateTotal() {
  const total = [...document.querySelectorAll('[data-path^="browser_weights."]')].reduce((n, field) => n + (Number(field.value) || 0), 0);
  const output = $('#browser-total');
  if (output) { output.textContent = `${total} / 100 points`; output.dataset.valid = String(total === 100); }
}

function group(id, title, note) {
  const element = $(`#${id}`);
  element.replaceChildren();
  const heading = document.createElement('h3'); heading.textContent = title;
  const paragraph = document.createElement('p'); paragraph.textContent = note;
  element.append(heading, paragraph);
  return element;
}

function control(parent, path, label, value, min, max, step) {
  const row = document.createElement('div'); row.className = 'weight-row';
  const caption = document.createElement('label'); caption.textContent = label;
  const input = document.createElement('input');
  Object.assign(input, { type: 'number', required: true, min, max, step, value });
  input.dataset.path = path;
  caption.append(input);
  const track = document.createElement('div'); track.className = 'weight-track';
  const fill = document.createElement('span'); track.append(fill);
  const update = () => {
    fill.style.width = `${Math.max(0, Math.min(100, Number(input.value) / max * 100))}%`;
    profileError(''); updateTotal();
  };
  input.addEventListener('input', update);
  row.append(caption, track); parent.append(row); update();
}

function renderProfile(profile) {
  if (!labels) return;
  const browser = group('browser-weights', 'Browser checklist · 100 points',
    'Pass earns its weight; warning earns zero. Review and not checked stay outside the assessed denominator.');
  const total = document.createElement('strong'); total.id = 'browser-total'; total.className = 'browser-total'; browser.append(total);
  for (const [key, label] of Object.entries(labels.browser_labels))
    control(browser, `browser_weights.${key}`, label, profile.browser_weights[key], 0, 100, 1);
  const crawler = group('crawler-weights', 'Crawler element weights', 'Relative editorial weights. Title and meta proxies add to visible boxes.');
  for (const [key, label] of Object.entries(labels.crawler_labels))
    control(crawler, `crawler_weights.${key}`, label, profile.crawler_weights[key], 0, key === 'boilerplate_multiplier' ? 1 : 3, 0.05);
  const retrieval = group('retrieval-controls', 'Passage retrieval', 'BM25 uses only the saved page’s retained heading and paragraph chunks. Lowercase word tokens and a fixed stopword list; no stemming, embeddings, or AI.');
  for (const [key, label, min, max, step] of [
    ['k1', 'Term repetition (k1)', 0.1, 3, 0.05], ['b', 'Length normalization (b)', 0, 1, 0.05],
    ['max_words', 'Chunk split target (words)', 50, 500, 1], ['length_target', 'No-question length target', 20, 250, 1],
  ]) control(retrieval, `retrieval.${key}`, label, profile.retrieval[key], min, max, step);
  profile.retrieval.position_priors.forEach((value, index) =>
    control(retrieval, `retrieval.position_priors.${index}`, `No-question chunk ${index + 1}${index === 3 ? '+' : ''} prior`, value, 0, 1, 0.05));
  const gap = group('gap-controls', 'Cross-view gap', 'Minimum rank difference for a callout.');
  control(gap, 'gap.rank_threshold', 'Difference threshold', profile.gap.rank_threshold, 0, 1, 0.05);
  updateTotal(); profileError('');
}

function currentProfile() {
  if (!defaults) return null;
  const profile = structuredClone(defaults);
  for (const field of document.querySelectorAll('[data-path]')) {
    if (!field.checkValidity()) throw new Error(`Check ${field.closest('label').textContent.trim()}.`);
    const keys = field.dataset.path.split('.');
    let target = profile;
    for (const key of keys.slice(0, -1)) target = target[key];
    target[keys.at(-1)] = field.step === '1' ? Number.parseInt(field.value, 10) : Number(field.value);
  }
  const total = Object.values(profile.browser_weights).reduce((sum, value) => sum + value, 0);
  if (total !== 100) throw new Error(`Browser points total ${total}; they must total 100.`);
  return profile;
}

function displayResult(result) {
  $('#result-url').textContent = result.url;
  $('#result-meta').textContent = `Audited ${result.audited_on} (UTC) · Browser rubric ${result.rubric_version} · ${result.input_kind === 'html' ? 'Offline HTML prototype' : 'Ownership unverified'}`;
  $('#result-score').textContent = `${result.score.earned} / ${result.score.assessed}`;
  $('#warnings').textContent = result.counts.warning;
  $('#reviews').textContent = result.counts.review;
  $('#site-basics-count').textContent = result.site_basics_reviews ?? '—';
  $('#robot-count').textContent = result.robot_visibility_reviews ?? '—';
  $('#source-findings').textContent = result.source_findings;
  $('#open-report').href = result.report_url;
  $('#report-frame').src = result.report_url;
  reportUrl = result.report_url;
  $('#view-nav').hidden = !result.reader_views;
  $('#views-json').hidden = !result.reader_views;
  if (result.reader_views) $('#views-json').href = result.views_url;
  document.querySelectorAll('[data-view]').forEach(button => button.setAttribute('aria-pressed', button.dataset.view === 'overview' ? 'true' : 'false'));
  if (result.revision_id) {
    $('#revision-label').textContent = `Revision ${result.revision_id.slice(0, 8)} · saved capture`;
    $('#revision-detail').textContent = `Original ${baselineResult.score.earned}/${baselineResult.score.assessed} → revised ${result.score.earned}/${result.score.assessed} points. Rescored ${result.rescored_at}; original report retained.`;
    $('#restore-original').hidden = false;
  } else {
    $('#revision-label').textContent = 'Original scoring';
    $('#revision-detail').textContent = 'Edit the rubric or reader question, then apply it to this saved capture.';
    $('#restore-original').hidden = true;
  }
  show('result', 'COMPLETE');
}

function renderHistory(revisions) {
  const history = $('#revision-history');
  history.replaceChildren();
  history.hidden = !revisions.length;
  if (!revisions.length) return;
  const heading = document.createElement('strong'); heading.textContent = 'Saved scoring revisions'; history.append(heading);
  for (const item of revisions) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = `${item.revision_id.slice(0, 8)} · ${item.score.earned}/${item.score.assessed} points · ${item.question || 'No question'}`;
    button.addEventListener('click', async () => {
      try {
        const result = await json(await fetch(`/api/runs/${activeRun}/revisions/${item.revision_id}`, { cache: 'no-store' }));
        $('#question').value = result.question;
        renderProfile(result.profile);
        displayResult(result);
      } catch (cause) { profileError(cause.message); }
    });
    history.append(button);
  }
}

function error(message) { $('#error-text').textContent = message; show('error', 'FAILED'); runButton.disabled = false; }

async function poll(id) {
  try {
    const result = await json(await fetch(`/api/runs/${id}`, { cache: 'no-store' }));
    if (activeRun !== id) return;
    if (result.status === 'complete') {
      baselineResult = result;
      $('#question').value = result.question || '';
      renderProfile(result.profile || defaults);
      displayResult(result);
      renderHistory(result.revisions || []);
      runButton.disabled = false;
      return;
    }
    if (result.status === 'failed') return error(result.error || 'The audit failed.');
    $('#progress-stage').textContent = result.stage || 'Waiting for the audit runner';
    setTimeout(() => poll(id), 1800);
  } catch (cause) { if (activeRun === id) error(cause.message); }
}

async function loadProfile() {
  try {
    labels = await json(await fetch('/api/scoring-profile', { cache: 'no-store' }));
    defaults = labels.profile;
    renderProfile(defaults);
    const requested = new URLSearchParams(location.search).get('run');
    const previous = requested || localStorage.getItem('s2c.lastRunId');
    if (previous && /^[0-9a-f]{32}$/.test(previous)) {
      try {
        const result = await json(await fetch(`/api/runs/${previous}`, { cache: 'no-store' }));
        activeRun = previous;
        if (result.status === 'complete') {
          baselineResult = result;
          selectSource(result.input_kind === 'html' ? 'html' : 'url');
          $('#url').value = result.url;
          $('#question').value = result.question || '';
          renderProfile(result.profile || defaults);
          displayResult(result);
          renderHistory(result.revisions || []);
        } else if (result.status === 'running' || result.status === 'queued') {
          show('progress', 'RUNNING'); poll(previous);
        }
      } catch (_) { if (!requested) localStorage.removeItem('s2c.lastRunId'); }
    }
  } catch (cause) { profileError(`Scoring controls unavailable: ${cause.message}. The default rules can still run.`); }
}
loadProfile();

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  let profile;
  try { profile = currentProfile(); profileError(''); } catch (cause) { profileError(cause.message); return; }
  activeRun = null; baselineResult = null; runButton.disabled = true;
  show('progress', 'RUNNING'); $('#progress-stage').textContent = 'Submitting audit'; $('#run-id').textContent = '';
  try {
    const kind = sourceKind();
    const important = $('#important').value.split(/\r?\n/).map(item => item.trim()).filter(Boolean);
    if (important.length > 5 || important.some(item => item.length < 3 || item.length > 160))
      throw new Error('Enter at most five important phrases of 3–160 characters each.');
    let source = { kind, url: $('#url').value.trim() };
    if (kind === 'html') {
      const file = $('#html-file').files[0];
      if (!file || !/\.html?$/i.test(file.name) || file.size > 2_000_000)
        throw new Error('Choose one .html file under 2 MB.');
      source = { kind, html: await file.text() };
    }
    const result = await json(await fetch('/api/runs', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...source, important, question: $('#question').value.trim(), ...(profile ? { profile } : {}) }),
    }));
    activeRun = result.run_id; $('#run-id').textContent = `Run ${result.run_id}`; poll(result.run_id);
    localStorage.setItem('s2c.lastRunId', result.run_id);
    history.replaceState(null, '', `/?run=${result.run_id}`);
  } catch (cause) { error(cause.message); }
});

applyButton.addEventListener('click', async () => {
  if (!activeRun || !baselineResult) return;
  let profile;
  try { profile = currentProfile(); profileError(''); } catch (cause) { profileError(cause.message); return; }
  applyButton.disabled = true; applyButton.textContent = 'Rescoring saved capture…';
  try {
    const result = await json(await fetch(`/api/runs/${activeRun}/revisions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: $('#question').value.trim(), profile }),
    }));
    displayResult(result);
    const latest = await json(await fetch(`/api/runs/${activeRun}`, { cache: 'no-store' }));
    renderHistory(latest.revisions || []);
  } catch (cause) { profileError(cause.message); }
  finally { applyButton.disabled = false; applyButton.textContent = 'Apply to saved capture'; }
});

$('#restore-original').addEventListener('click', () => {
  if (!baselineResult) return;
  $('#question').value = baselineResult.question || '';
  renderProfile(baselineResult.profile || defaults);
  displayResult(baselineResult);
});
$('#reset-profile').addEventListener('click', () => { if (defaults) renderProfile(defaults); });
document.querySelectorAll('[data-url]').forEach(button => button.addEventListener('click', () => {
  selectSource('url'); $('#url').value = button.dataset.url; $('#url').focus();
}));
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
  if (!reportUrl) return;
  $('#report-frame').src = `${reportUrl}#${button.dataset.view}`;
  document.querySelectorAll('[data-view]').forEach(item => item.setAttribute('aria-pressed', item === button ? 'true' : 'false'));
  $('#report-frame').scrollIntoView({ behavior: 'smooth', block: 'start' });
}));
