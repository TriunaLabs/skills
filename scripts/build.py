"""Build a relocatable static catalog. No skill code is executed."""
import html
import json
import shutil
from pathlib import Path
from validate import ROOT, validate

def build():
    records = validate()
    out = ROOT / 'dist'
    # Only remove this repository's generated output; never follow a symlink.
    if out.is_symlink() or out.resolve() != ROOT.resolve() / 'dist':
        raise ValueError('Unsafe build output path')
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for path in (ROOT / 'site').iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
    (out / '.nojekyll').touch()
    (out / 'catalog.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    shutil.copytree(ROOT / 'skills', out / 'skills', dirs_exist_ok=True)
    template = (out / 'index.html').read_text(encoding='utf-8')
    fallback = ''.join(f'<li><a href="skills/{r["name"]}/SKILL.md">{html.escape(r["title"])}</a> â€” {html.escape(r["description"])}</li>' for r in records)
    (out / 'index.html').write_text(template.replace('<!-- FALLBACK -->', fallback), encoding='utf-8')
    print(f'Built {len(records)} skills into {out}')

if __name__ == '__main__':
    build()
