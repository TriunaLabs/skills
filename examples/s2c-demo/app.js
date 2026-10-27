const options = document.querySelector('#family-options');
if (options) {
  const section = document.createElement('section');
  section.className = 'sibling-option';
  section.innerHTML = '<h2>Options for multiple children</h2><p>Compare schedules for multiple children before choosing a program.</p><p><a href="siblings.html">Compare sibling schedules</a></p>';
  options.after(section);
  const canonical = document.querySelector('link[rel="canonical"]');
  if (canonical) canonical.href = new URL('corrected.html', document.baseURI).href;
  const description = document.querySelector('meta[name="description"]');
  if (description) description.content = 'Explore learning paths and schedules for one or more children.';
}
