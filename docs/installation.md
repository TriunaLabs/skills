# Install a skill

Official documentation checked 2026-10-28. The [guided installer](https://triunalabs.github.io/skills/?skill=scan-to-comprehend&setup=1#install) offers separate paths for Codex, Claude Code, Claude desktop/web, and other agents. The website provides instructions and complete ZIP packages; installation happens in your agent.

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
test ! -e ~/.agents/skills/scan-to-comprehend && cp -R skills/scan-to-comprehend ~/.agents/skills/
```

PowerShell, personal install (refuses overwrite):

```powershell
$destination = Join-Path $HOME '.agents/skills/scan-to-comprehend'
if (Test-Path $destination) { throw 'Skill already exists; review before updating.' }
New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
Copy-Item -Recurse skills/scan-to-comprehend $destination
```

In Codex, explicitly request `$scan-to-comprehend` with your task. Codex detects changes automatically; restart it if discovery fails. Check current documentation for your installed version.

Source: [OpenAI: Build skills / local discovery](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).

## Claude Code

Use `.claude/skills/` for a project or `~/.claude/skills/` for personal local sessions.

POSIX shell, personal install:

```sh
mkdir -p ~/.claude/skills
test ! -e ~/.claude/skills/scan-to-comprehend && cp -R skills/scan-to-comprehend ~/.claude/skills/
```

PowerShell, personal install:

```powershell
$destination = Join-Path $HOME '.claude/skills/scan-to-comprehend'
if (Test-Path $destination) { throw 'Skill already exists; review before updating.' }
New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
Copy-Item -Recurse skills/scan-to-comprehend $destination
```

Invoke `/scan-to-comprehend` with a concrete request. Personal local files do not automatically become available to Claude cloud or Cowork sessions; follow the corresponding official flow for those environments.

Source: [Anthropic: Extend Claude with skills](https://code.claude.com/docs/en/skills).

## Claude desktop or web

Download the selected skill ZIP from the catalog. In Claude, go to Customize → Skills, choose + → Create skill → Upload a skill, upload the ZIP and enable it. The archive contains a named skill folder and all supporting resources. Enable code execution/file creation in Settings → Capabilities if needed; organization policies may govern access. Ask Claude to use the skill by name with your input.

Tool requirements still apply. A successful upload is not a runtime test of browser capture, local files, or optional integrations. See [Anthropic: Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

## Other agents

The packages use the [Agent Skills specification](https://agentskills.io/specification): a folder with `SKILL.md` and optional resources. No universal installation path or command is assumed. Check your agent's official documentation for skill discovery and permitted tools, then copy the selected folder to its documented location. Other-agent runtime behavior is untested.

## Updating and removal

Review upstream diffs before replacing a skill, preserving any local edits. Remove only the selected installed folder to uninstall; do not delete the parent skill directory. Templates and scripts may require tools listed in `catalog.json`; copying the folder does not install those tools.
