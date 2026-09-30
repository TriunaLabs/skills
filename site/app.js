const $ = (id) => document.getElementById(id);
const names = {codex: 'Codex', 'claude-code': 'Claude Code', 'other-agents': 'Other agents'};
let skills = [];
let returnFocus;
const el = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
function render() {
  const query = $('search').value.trim().toLowerCase();
  const agent = $('agent').value;
  const category = $('category').value;
  const matches = skills.filter(s => `${s.title} ${s.description} ${s.tags.join(' ')} ${s.requirements.join(' ')}`.toLowerCase().includes(query) && (category === 'all' || s.category === category) && (agent === 'all' || s.compatibility[agent] === 'format-compatible'));
  $('cards').replaceChildren();
  for (const s of matches) {
    const card = el('article', '', 'card');
    const top = el('div', '', 'card-top');
    top.append(el('span', ({Planning:'◇',Engineering:'⌘',Documentation:'≡',Data:'▦'})[s.category] || '◇', 'icon'), el('span', s.category, 'category'));
    card.append(top, el('h3', s.title), el('p', s.description));
    const tags = el('div', '', 'tags');
    s.tags.forEach(t => tags.append(el('span', t, 'tag')));
    const bottom = el('div', '', 'card-bottom');
    const supported = Object.entries(s.compatibility).filter(([,v])=>v==='format-compatible').map(([k])=>names[k]);
    bottom.append(el('span', supported.length ? `${supported.join(' · ')} / format-compatible` : 'Runtime compatibility untested', 'status'));
    const button = el('button', 'Explore skill ↗'); button.type='button'; button.setAttribute('aria-label', `Explore ${s.title}`);
    button.addEventListener('click', () => show(s, button)); bottom.append(button); card.append(tags, bottom); $('cards').append(card);
  }
  $('count').textContent = `${matches.length} of ${skills.length} skills${agent !== 'all' ? ' format-compatible with ' + names[agent] : ''}`;
  $('empty').hidden = matches.length !== 0;
  const params = new URLSearchParams();
  if(query) params.set('q', $('search').value); if(agent !== 'all') params.set('agent', agent); if(category !== 'all') params.set('category', category);
  history.replaceState(null, '', location.pathname + (params.size ? '?' + params : '') + location.hash);
}
function show(s, button) {
  returnFocus = button;
  $('detail-title').textContent = s.title;
  $('detail-description').textContent = s.description;
  $('detail-meta').replaceChildren(el('p', `v${s.version} · ${s.license} · ${s.author}`), el('p', s.origin));
  const list=el('ul',''); s.requirements.forEach(r=>list.append(el('li',r))); $('detail-meta').append(el('h3','Requirements'),list);
  Object.entries(s.compatibility).forEach(([k,v])=>$('detail-meta').append(el('p',`${names[k]}: ${v}`)));
  $('detail-example').textContent=s.examples.join('\n'); $('detail-instructions').textContent=s.instructions;
  $('source').href=`https://github.com/TriunaLabs/skills/tree/main/skills/${s.name}`;
  $('raw').href=`skills/${s.name}/SKILL.md`;
  $('detail').showModal();
}
$('close').addEventListener('click', ()=>$('detail').close());
$('detail').addEventListener('close', ()=>returnFocus?.focus());
$('detail-install').addEventListener('click', ()=>$('detail').close());
['search','agent','category'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));
$('reset').addEventListener('click',()=>{$('search').value='';$('agent').value='all';$('category').value='all';render();});
function install(agent) {
  document.querySelectorAll('[data-install]').forEach(b=>b.setAttribute('aria-pressed', String(b.dataset.install===agent)));
  const data={codex:['Project: .agents/skills/ · Personal folder below.','~/.agents/skills/decision-record/SKILL.md','Start a new session and request $decision-record.','https://learn.chatgpt.com/docs/build-skills'], 'claude-code':['Project: .claude/skills/ · Personal local folder below.','~/.claude/skills/decision-record/SKILL.md','Invoke /decision-record with your task. Cloud sessions use a separate flow.','https://code.claude.com/docs/en/skills'], 'other-agents':['Use your agent’s documented skill directory.','<agent-skill-directory>/decision-record/SKILL.md','No universal install path is assumed. Runtime compatibility is untested.','https://agentskills.io/specification']}[agent];
  $('install-description').textContent=data[0];$('install-path').textContent=data[1];$('invoke').textContent=data[2];$('official').href=data[3];
}
document.querySelectorAll('[data-install]').forEach(b=>b.addEventListener('click',()=>install(b.dataset.install)));
install('codex');
fetch('catalog.json').then(r=>{if(!r.ok)throw new Error('catalog');return r.json();}).then(data=>{
  skills=data;
  [...new Set(skills.map(s=>s.category))].sort().forEach(c=>{const o=el('option',c);o.value=c;$('category').append(o);});
  const p=new URLSearchParams(location.search);$('search').value=p.get('q')||'';
  if(['all',...Object.keys(names)].includes(p.get('agent'))) $('agent').value=p.get('agent');
  if([...$('category').options].some(o=>o.value===p.get('category'))) $('category').value=p.get('category');
  render();
}).catch(()=>{$('count').textContent='Catalog unavailable';$('error').hidden=false;document.querySelectorAll('.controls input,.controls select,#reset').forEach(e=>e.disabled=true);});
