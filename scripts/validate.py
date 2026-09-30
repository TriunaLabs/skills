"""Validate public skill packages without executing their scripts."""
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

def validate(root=ROOT):
    records = []
    folders = sorted((root / 'skills').iterdir())
    if not folders:
        raise ValueError('At least one skill is required')
    for folder in folders:
        if not folder.is_dir():
            raise ValueError(f'Unexpected file: {folder}')
        name = folder.name
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 64:
            raise ValueError(f'Invalid skill name: {name}')
        for path in folder.rglob('*'):
            if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
                raise ValueError(f'Unsafe resource: {path}')
        source = (folder / 'SKILL.md').read_text(encoding='utf-8')
        parts = source.split('---', 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f'{name}: missing frontmatter')
        front = yaml.safe_load(parts[1])
        if not isinstance(front, dict) or front.get('name') != name:
            raise ValueError(f'{name}: frontmatter name must match folder')
        description = front.get('description')
        if not isinstance(description, str) or not 1 <= len(description) <= 1024:
            raise ValueError(f'{name}: invalid description')
        if not parts[2].strip():
            raise ValueError(f'{name}: instructions required')
        for target in re.findall(r'\]\(([^)]+)\)', parts[2]):
            if '://' in target or target.startswith('#'):
                continue
            resource = (folder / target.split('#')[0]).resolve()
            if not resource.is_relative_to(folder.resolve()) or not resource.is_file():
                raise ValueError(f'{name}: broken or escaping reference {target}')
        meta = json.loads((folder / 'catalog.json').read_text(encoding='utf-8'))
        expected = {'title', 'category', 'tags', 'version', 'license', 'author', 'origin', 'requirements', 'compatibility', 'examples'}
        if set(meta) != expected:
            raise ValueError(f'{name}: metadata keys must be {sorted(expected)}')
        for field in ['title', 'category', 'author', 'origin']:
            if not isinstance(meta[field], str) or not meta[field].strip():
                raise ValueError(f'{name}: invalid {field}')
        if meta['license'] != 'MIT' or front.get('license') != 'MIT':
            raise ValueError(f'{name}: this library accepts MIT contributions')
        if not re.fullmatch(r'\d+\.\d+\.\d+', meta['version']):
            raise ValueError(f'{name}: use a semantic version')
        for field in ['tags', 'requirements', 'examples']:
            if not isinstance(meta[field], list) or not meta[field] or not all(isinstance(x, str) and x.strip() for x in meta[field]):
                raise ValueError(f'{name}: {field} must be a nonempty string array')
        if set(meta['compatibility']) != {'codex', 'claude-code', 'other-agents'}:
            raise ValueError(f'{name}: all compatibility targets required')
        if any(v not in ['format-compatible', 'untested', 'unsupported'] for v in meta['compatibility'].values()):
            raise ValueError(f'{name}: unsupported compatibility claim')
        records.append(dict(meta, name=name, description=description, instructions=parts[2].strip()))
    return records

if __name__ == '__main__':
    try:
        print(f'Validated {len(validate())} skill packages')
    except (ValueError, OSError, yaml.YAMLError, TypeError) as error:
        raise SystemExit(str(error))
