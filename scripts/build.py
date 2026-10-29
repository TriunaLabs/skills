"""Build a relocatable static catalog. No skill code is executed."""
import html
import json
import shutil
import hashlib
import zipfile
from pathlib import Path
from validate import ROOT, validate

def build():
    records = validate()
    public_records = [record for record in records if record.get('visibility', 'public') == 'public']
    out = ROOT / 'dist'
    # Only remove this repository's generated output; never follow a symlink.
    if out.is_symlink() or out.resolve() != ROOT.resolve() / 'dist':
        raise ValueError('Unsafe build output path')
    if out.exists():
        for child in out.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)
    else:
        out.mkdir()
    for path in (ROOT / 'site').iterdir():
        if path.is_file():
            shutil.copy2(path, out / path.name)
        elif path.is_dir():
            shutil.copytree(path, out / path.name, dirs_exist_ok=True)
    demo = out / 'examples' / 's2c-demo'
    demo.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'app.js', 'styles.css', 'programs.html', 'siblings.html',
                 'sample.html', 'corrected.html', 'favicon.svg', 'showcase.html',
                 'showcase.css', 'showcase.js'):
        shutil.copy2(ROOT / 'examples' / 's2c-demo' / name, demo / name)
    (out / '.nojekyll').touch()
    (out / 'downloads').mkdir(exist_ok=True)
    for record in public_records:
        source=ROOT / 'skills' / record['name']
        package=out / 'skills' / record['name']
        shutil.copytree(source, package, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store','.git','node_modules'))
        if not (package/'LICENSE').exists():
            shutil.copy2(ROOT/'LICENSE',package/'LICENSE')
        files=sorted(p for p in package.rglob('*') if p.is_file())
        archive=out / 'downloads' / f"{record['name']}-{record['version']}.zip"
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
            for file in files:
                if not file.resolve().is_relative_to(package.resolve()):
                    raise ValueError('Package file escapes its skill folder')
                info=zipfile.ZipInfo(f"{record['name']}/{file.relative_to(package).as_posix()}",date_time=(2026,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                bundle.writestr(info,file.read_bytes())
        references=[]
        for file in sorted((package/'references').glob('*.md')):
            heading=next((line.lstrip('# ').strip() for line in file.read_text(encoding='utf-8-sig').splitlines() if line.startswith('# ')),file.stem.replace('-',' '))
            references.append({'title':heading,'href':f"skills/{record['name']}/references/{file.name}"})
        record['distribution']={'zip':archive.relative_to(out).as_posix(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'file_count':len(files)}
        record['evidence']={'script_count':sum(p.suffix in {'.py','.js','.mjs','.cjs','.sh','.ps1'} for p in files),
                            'reference_count':len(references),'references':references}
    (out / 'catalog.json').write_text(json.dumps(public_records, indent=2), encoding='utf-8')
    template = (out / 'index.html').read_text(encoding='utf-8')
    fallback = ''.join(f'<li><a href="skills/{r["name"]}/SKILL.md">{html.escape(r["title"])}</a> — {html.escape(r["description"])}</li>' for r in public_records)
    (out / 'index.html').write_text(template.replace('<!-- FALLBACK -->', fallback), encoding='utf-8')
    print(f'Built {len(public_records)} public skills into {out} ({len(records) - len(public_records)} hidden)')

if __name__ == '__main__':
    build()
