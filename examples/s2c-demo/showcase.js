const source = document.getElementById('view-source');
const rendered = document.getElementById('view-rendered');
const added = document.getElementById('added-card');
const caption = document.getElementById('view-caption');
const label = document.getElementById('evidence-label');
const title = document.getElementById('evidence-title');
const copy = document.getElementById('evidence-copy');
const code = document.getElementById('evidence-code');

function selectView(view) {
  const isRendered = view === 'rendered';
  source.setAttribute('aria-pressed', String(!isRendered));
  rendered.setAttribute('aria-pressed', String(isRendered));
  added.hidden = !isRendered;
  caption.textContent = isRendered
    ? 'JavaScript adds the sibling heading and direct schedule link.'
    : 'The sibling route is absent from the initial response.';
  label.textContent = isRendered ? 'RENDERED DOM · index.html' : 'INITIAL HTML · index.html';
  title.textContent = isRendered ? 'A direct route appears.' : 'The route needs another page.';
  copy.textContent = isRendered
    ? 'After the script runs, the sibling heading and link appear on the starting page. The description and canonical URL also change. This is a rendered-page observation, not proof of crawler behavior.'
    : 'The starting page has no sibling heading or link in its initial HTML. A parent can reach the schedule through the corrected example page, but the route is indirect.';
  code.textContent = isRendered
    ? '<article class="sibling-option">\n  <h3>Options for multiple children</h3>\n  <a href="siblings.html">Compare sibling schedules</a>\n</article>'
    : '<article id="family-options">\n  <h3>For one learner</h3>\n</article>\n<!-- no sibling link in this response -->';
}

source.addEventListener('click', () => selectView('source'));
rendered.addEventListener('click', () => selectView('rendered'));
