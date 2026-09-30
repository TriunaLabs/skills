# Install a skill

Official documentation checked 2026-09-30. These instructions cover local skill folders, not a plugin marketplace or cloud upload flow.

Clone the library, review the selected folder and any scripts, and copy the whole folder. Keep its resources together. Run commands from the cloned library. Choose a destination that does not already contain that skill; do not merge over a customized copy. For a stable installation, check out a reviewed commit before copying. Record that commit in your own project notes.

```sh
git clone https://github.com/TriunaLabs/skills.git triunalabs-skills
cd triunalabs-skills
```

## Codex

Local discovery supports project `.agents/skills/` and personal `~/.agents/skills/`. These are the paths in current official docs; older installations may use different paths. Copy a selected folder into the project where you run Codex or into the personal directory.

POSIX shell, personal install:

```sh
mkdir -p ~/.agents/skills
test ! -e ~/.agents/skills/decision-record && cp -R skills/decision-record ~/.agents/skills/
```

PowerShell, personal install (refuses overwrite):

```powershell
$destination = Join-Path $HOME '.agents/skills/decision-record'
if (Test-Path $destination) { throw 'Skill already exists; review before updating.' }
New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
Copy-Item -Recurse skills/decision-record $destination
```

Start a new Codex session in your project and explicitly request `$decision-record` with your task. If discovery fails, check your installed version and current documentation.

Source: [OpenAI: Build skills / local discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).

## Claude Code

Use `.claude/skills/` for a project or `~/.claude/skills/` for personal local sessions.

POSIX shell, personal install:

```sh
mkdir -p ~/.claude/skills
test ! -e ~/.claude/skills/decision-record && cp -R skills/decision-record ~/.claude/skills/
```

PowerShell, personal install:

```powershell
$destination = Join-Path $HOME '.claude/skills/decision-record'
if (Test-Path $destination) { throw 'Skill already exists; review before updating.' }
New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
Copy-Item -Recurse skills/decision-record $destination
```

Invoke `/decision-record` with a concrete request. Personal local files do not automatically become available to Claude cloud or Cowork sessions; follow the corresponding official flow for those environments.

Source: [Anthropic: Extend Claude with skills](https://code.claude.com/docs/en/skills).

## Other agents

The packages use the [Agent Skills specification](https://agentskills.io/specification): a folder with `SKILL.md` and optional resources. No universal installation path or command is assumed. Check your agent's official documentation for skill discovery and permitted tools, then copy the selected folder to its documented location. Other-agent runtime behavior is untested.

## Updating and removal

Review upstream diffs before replacing a skill, preserving any local edits. Remove only the selected installed folder to uninstall; do not delete the parent skill directory. Templates and scripts may require tools listed in `catalog.json`; copying the folder does not install those tools.
