const data=JSON.parse(document.getElementById('release-data').textContent);
const $=id=>document.getElementById(id),summary=data.summary||{},source=data.source||{},evidence=data.evidence||{},confidence=data.confidence||{},collaboration=data.collaboration||{};
const text=(id,value)=>$(id).textContent=value??'—';
const target=source.target_tag||source.target_ref||String(source.target_sha||'').slice(0,8);
const statusClass=value=>['verified','attention','unknown'].includes(value)?value:'unknown';

function fallbackContributors(){
  const people=new Map();
  for(const commit of data.commits||[]){
    const name=commit.author||'Unknown author',item=people.get(name)||{name,commits:0,files:new Set(),categories:new Set()};
    item.commits+=1;(commit.paths||[]).forEach(path=>item.files.add(path));item.categories.add(commit.category);people.set(name,item);
  }
  return [...people.values()].map(item=>({name:item.name,commits:item.commits,commit_share_percent:(item.commits/Math.max((data.commits||[]).length,1))*100,files_touched:item.files.size,categories:[...item.categories]}));
}
const contributors=collaboration.contributors||fallbackContributors();

text('release-name',target);text('audience',String(data.audience||'').toUpperCase());text('headline',`${target} release brief`);
text('range',`${source.repository} · ${source.base_ref}..${source.target_ref} · ${String(source.base_sha).slice(0,8)} → ${String(source.target_sha).slice(0,8)}`);
text('m-contributors',summary.contributors??contributors.length);text('m-commits',summary.commits||0);text('m-verified',`${summary.verified_domains??confidence.verified_domains??0}/5`);text('m-exposure',summary.new_critical_high??0);
text('m-files',summary.changed_files||0);text('m-add',`+${summary.additions||0}`);text('m-del',`−${summary.deletions||0}`);text('m-span',`${collaboration.commit_span_hours||0}h`);
const ready=document.createElement('b'),detail=document.createElement('span');ready.textContent='DRAFT · EVIDENCE REVIEW REQUIRED';detail.textContent=`${summary.evidence_gaps||0} gaps · ${summary.attention_domains??0} domains need attention · working tree ${source.dirty_entries?'not clean':'clean at collection'}`;$('readiness').append(ready,detail);

const domains=confidence.domains||[
  {label:'Quality',status:(evidence.tests||[]).length?'unknown':'unknown',detail:'No structured evidence matrix in this artifact.'},
  {label:'Security',status:'unknown',detail:'No structured evidence matrix in this artifact.'},
  {label:'Recoverability',status:'unknown',detail:'No structured evidence matrix in this artifact.'},
  {label:'Operability',status:'unknown',detail:'No structured evidence matrix in this artifact.'},
  {label:'Provenance',status:'unknown',detail:'No structured evidence matrix in this artifact.'}
];
$('confidence-grid').replaceChildren(...domains.map(item=>{const article=document.createElement('article'),top=document.createElement('div'),name=document.createElement('b'),status=document.createElement('span'),p=document.createElement('p');article.className=`confidence-card ${statusClass(item.status)}`;name.textContent=item.label;status.className='state';status.textContent=item.status;top.append(name,status);p.textContent=item.detail;article.append(top,p);return article;}));

text('collab-count',`${contributors.length} CONTRIBUTORS`);
const maxCommits=Math.max(...contributors.map(item=>item.commits),1);
$('contributors').replaceChildren(...contributors.map(item=>{const row=document.createElement('article'),top=document.createElement('div'),name=document.createElement('b'),meta=document.createElement('span'),track=document.createElement('div'),bar=document.createElement('i'),detail=document.createElement('small');name.textContent=item.name;meta.textContent=`${item.commits} ${item.commits===1?'commit':'commits'} · ${item.files_touched} ${item.files_touched===1?'file':'files'}`;top.append(name,meta);track.className='track';bar.style.width=`${Math.max(8,item.commits/maxCommits*100)}%`;track.append(bar);detail.textContent=(item.categories||[]).join(' · ');row.append(top,track,detail);return row;}));
const categoryCounts={};for(const entry of data.entries||[])categoryCounts[entry.category]=(categoryCounts[entry.category]||0)+1;
const maxCategory=Math.max(...Object.values(categoryCounts),1);
$('category-chart').replaceChildren(...Object.entries(categoryCounts).sort((a,b)=>b[1]-a[1]).map(([label,value])=>{const row=document.createElement('article'),name=document.createElement('span'),track=document.createElement('div'),bar=document.createElement('i'),count=document.createElement('b');name.textContent=label;track.className='track';bar.style.width=`${value/maxCategory*100}%`;track.append(bar);count.textContent=value;row.append(name,track,count);return row;}));

const categories=[...new Set((data.entries||[]).map(entry=>entry.category))];for(const category of categories){const option=document.createElement('option');option.value=category;option.textContent=category;$('category').append(option);}
function renderEntries(){const q=$('search').value.trim().toLowerCase(),category=$('category').value;const included=(data.entries||[]).filter(entry=>entry.included),matches=included.filter(entry=>`${entry.title} ${entry.category} ${(entry.paths||[]).join(' ')}`.toLowerCase().includes(q)&&(category==='all'||entry.category===category));text('entry-count',`${matches.length} of ${included.length} entries for ${data.audience}`);$('entries').replaceChildren(...matches.map(entry=>{const article=document.createElement('article'),top=document.createElement('div'),heading=document.createElement('h3'),badge=document.createElement('span');article.className='entry';top.className='entry-top';heading.textContent=entry.title;badge.className=`badge ${entry.category==='Breaking'?'breaking':''}`;badge.textContent=entry.category;top.append(heading,badge);article.append(top);if(entry.uncertainty){const p=document.createElement('p');p.textContent=entry.uncertainty;article.append(p);}const refs=document.createElement('div');refs.className='refs';for(const value of entry.evidence_refs||[]){const span=document.createElement('span');span.className='ref';span.textContent=value;refs.append(span);}article.append(refs);return article;}));}
$('search').addEventListener('input',renderEntries);$('category').addEventListener('change',renderEntries);renderEntries();

text('risk-count',`${(data.risk_flags||[]).length} SIGNALS`);$('risks').replaceChildren(...(data.risk_flags||[]).map(risk=>{const article=document.createElement('article'),head=document.createElement('div'),name=document.createElement('b'),severity=document.createElement('span'),p=document.createElement('p');article.className='risk';name.textContent=risk.kind;severity.className=`severity severity-${risk.severity}`;severity.textContent=risk.severity;head.append(name,severity);p.textContent=risk.reason;article.append(head,p);return article;}));if(!(data.risk_flags||[]).length)$('risks').textContent='No deterministic risk signals were detected. This is not proof of low risk.';

const tests=evidence.tests||[];$('tests').replaceChildren(...(tests.length?tests:[{name:'No test records supplied',status:'unknown'}]).map(test=>{const row=document.createElement('article'),name=document.createElement('span'),status=document.createElement('b');name.textContent=test.name;status.className=`test-${test.status}`;status.textContent=test.status;row.append(name,status);return row;}));
const delta=confidence.security_delta||{},severities=['critical','high','medium','low'];const securityTable=document.createElement('table'),head=document.createElement('thead'),headRow=document.createElement('tr');for(const label of ['Severity','New','Resolved','Remaining']){const th=document.createElement('th');th.textContent=label;headRow.append(th);}head.append(headRow);const body=document.createElement('tbody');for(const level of severities){const row=document.createElement('tr');for(const value of [level,delta.introduced?.[level]??0,delta.resolved?.[level]??0,delta.remaining?.[level]??0]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}body.append(row);}securityTable.append(head,body);$('security-delta').append(securityTable);

const dependency=evidence.dependency_review||{},supply=evidence.supply_chain||{},deployment=evidence.deployment||{},rollback=evidence.rollback||{},observability=evidence.observability||{},rollout=evidence.rollout||{};
const cards=[
  ['Dependency review',dependency.status||'unknown',`${dependency.added||0} added · ${dependency.updated||0} updated · ${dependency.vulnerable_added||0} vulnerable added`],
  ['SBOM',supply.sbom?.status||'unknown',supply.sbom?.format||'format not supplied'],
  ['Build provenance',supply.provenance?.status||'unknown',supply.provenance?.level||'level not supplied'],
  ['Artifact signature',supply.signature?.status||'unknown',supply.signature?.method||'method not supplied'],
  ['Deployment',deployment.status||'unknown',deployment.environment||'environment not supplied'],
  ['Rollback',rollback.status||'unknown',rollback.evidence_ref||'evidence not linked'],
  ['Observability',observability.status||'unknown',observability.summary||'monitoring detail not supplied'],
  ['Rollout',rollout.status||'unknown',rollout.strategy||'strategy not supplied']
];
$('evidence-grid').replaceChildren(...cards.map(([label,value,detail])=>{const article=document.createElement('article'),small=document.createElement('span'),strong=document.createElement('strong'),p=document.createElement('p');article.className='evidence-card';small.textContent=label;strong.textContent=value;p.textContent=detail;article.append(small,strong,p);return article;}));
function fillList(id,values,empty){$(id).replaceChildren(...((values||[]).length?values:[empty]).map(value=>{const li=document.createElement('li');li.textContent=value;return li;}));}fillList('gaps',data.evidence_gaps,'No evidence gaps recorded.');fillList('limitations',evidence.known_limitations,'No known limitations supplied.');

$('commit-rows').replaceChildren(...(data.commits||[]).map(commit=>{const row=document.createElement('tr');for(const value of [commit.short_sha,commit.author,commit.category,commit.subject,(commit.verified_issue_refs||[]).map(item=>`#${item}`).join(', ')||'unverified / none']){const cell=document.createElement('td');if(value===commit.short_sha){const code=document.createElement('code');code.textContent=value;cell.append(code);}else cell.textContent=value;row.append(cell);}return row;}));
$('raw').textContent=JSON.stringify(data,null,2);$('theme').addEventListener('click',()=>document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark');$('print').addEventListener('click',()=>window.print());
