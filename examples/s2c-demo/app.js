const options = document.querySelector('#family-options');
if (options) {
  const section = document.createElement('section');
  section.className = 'option-card sibling-option';
  section.innerHTML = '<span class="card-index">02 / PLAN TOGETHER</span><div class="option-icon" aria-hidden="true">✳</div><h3>Options for multiple children</h3><p>Compare schedules for multiple children before choosing a program.</p><a href="siblings.html">Compare sibling schedules <span aria-hidden="true">→</span></a>';
  options.after(section);
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical) canonical.href = new URL('corrected.html', document.baseURI).href;
  const description = document.querySelector('meta[name="description"]');
  if (description) description.content = 'Explore learning paths and schedules for one or more children.';
}
