"""Build a relocatable static catalog. No skill code is executed."""
import html
import json
import shutil
from pathlib import Path
from validate import ROOT, validate

def build():
    records = validate()
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    for path in (ROOT / 'site').iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
    (out / '.nojekyll').touch()
    (out / 'catalog.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    shutil.copytree(ROOT / 'skills', out / 'skills', dirs_exist_ok=True)
    template = (out / 'index.html').read_text(encoding='utf-8')
    fallback = ''.join(f'<li><a href="skills/{r["name"]}/SKILL.md">{html.escape(r["title"])}</a> — {html.escape(r["description"])}</li>' for r in records)
    (out / 'index.html').write_text(template.replace('<!-- FALLBACK -->', fallback), encoding='utf-8')
    print(f'Built {len(records)} skills into {out}')

if __name__ == '__main__':
    build()
