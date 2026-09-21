# STATUS — SuperInstance (portfolio archive)

## What this is

A snapshot of one team's *portfolio* repo called `SuperInstance`: a thousand
shellscript-flavoured bash scripts, Python services, deployment manifests,
operation runbooks, and bot-coordination experiments, all from the era
when the team was trying to be a "one platform" for many parallel
applications. The single commit `5235e1e` ("Initial commit: Complete
SuperInstance project portfolio") froze a very wide cross-section of work.

Concretely the tree includes:

- **`activelog/`** — the main "active log" / multi-bot coordination system
  (services directory, deployment scripts, audit bots, monitoring,
  ollama/langchain tooling).
- **`SuperInstance_Archive_Complete/`** — a self-contained archive of the
  SuperInstance web server.
- **`ai_society_portal/`** — an SF-TV Universe / character-evolution
  experiment with multi-model API integration.
- **`autocoder/`** — AutoGen-style code-generation harness.
- **`content-studio-dev/`** — multi-model content studio (Anthropic / OpenAI
  / Groq / GLM-4 route + cost-compare tooling).
- **`swarm_intelligence_production/`** — a "quantum orchestra" + deployment
  scripts for swarm-intelligence experiments.

## What it was good at

- **Operational density.** 6000+ tracked files, mostly scripts, mostly
  one-purpose deploy/run/test/monitor helpers. A field guide to "what
  to actually run when the alarms go off" in 2025-style cloud setups.
- **Cross-service deployment choreography.** `deploy.sh`,
  `deploy-remote.sh`, `deploy-superinstance.sh`, `deploy-all-domains.sh`
  form a layered deploy ladder — useful as a reference for anyone
  rolling deploys across many micro-services.
- **Multi-model router pattern.** `content-studio-dev/` shows the canonical
  "Anthropic + OpenAI + Groq + GLM-4 with cost comparison and one
  config file" pattern that was *the* canonical pattern in 2025.
- **Self-aware cost instrumentation.** `monitor_costs.sh`,
  `compare_costs.py`, COST-optimization infra. Cheap to copy-paste into
  any small project that suddenly has real API spend.

## Why we moved on

The scope spread was unrecoverable. The portfolio had at least seven
discrete projects in one tree, and every new feature cost context-switch
across all of them. The team's energy went toward smaller, single-purpose
repos and *toward* the kind of slice-of-life archive you are reading now.

## What's salvageable

- **`activelog/bin/`** — small, named ops scripts (backups, cleanup,
  health checks). These are generic enough to reuse.
- **`activelog/secrets/setup-secrets.sh`** + `production/scripts/
  setup-secrets.sh` — the "single source of truth for service secrets
  with .env generation" pattern. Reusable as a starting point.
- **`content-studio-dev/setup_api_keys.sh`** — interactive key-bootstrap
  script (safe in this archive, since it does not contain any secrets).
- **`consolidated-documents/environment-variables.md`** — a single-page
  reference for every env-var the platform wanted. Even though the
  platform itself is dead, the *list* is a useful checklist.

## What was redacted before push

- `ai_society_portal/API_KEYS.txt` originally held real keys for Zhipu,
  DeepInfra, Moonshot, Anthropic, OpenAI, DeepSeek. Replaced every line
  with `your_*_here` placeholders. No other live secrets were found in
  the tracked tree (`.claude/settings.local.json` was a Claude-Code
  permissions file with only paths, IP-shaped strings, and ARNs — not
  committed; `.gitignore` rules now exclude the whole `.claude/`
  directory from any future commits).

## What's here vs. upstream

| Aspect | This repo | Notes |
|--------|-----------|-------|
| Branch | `master` (preserved) | Single upstream commit `5235e1e` |
| Tracked files | 6135 | Plus a few untracked `.claude/` (excluded from history) |
| Modified lines | only filemode noise from the WSL checkout | Fixed with `core.filemode=false` |
| License | MIT (added at publication) | Original portfolio had none |
| `core.filemode` | `false` set, to silence cross-FS permission drift | |

## Reading order

1. `STATUS.md` (this file) — slice-of-life context
2. `README.archiver.md` (or `README.md` if you arrived there) — quick
   orientation + how to get around
3. `consolidated-documents/environment-variables.md` — env-var map
4. The leaf directories (`activelog/`, `ai_society_portal/`,
   `content-studio-dev/`, etc.) each tell their own story.

## Provenance

Archived from `~/SuperInstance` (also present as identically-named
copies under `wslbackup/`, `activelog2/activelog_v2/`, and
`activelogearlier/activelog_v2/` — all four kept the same `5235e1e`
head SHA). Pushed to `SuperInstance/SuperInstance-archive` on 2026-09
as part of the SuperInstance slice-of-life archive.

Take this, fork it, evolve it. No attribution required. We'd love to
hear what you build, but you owe us nothing.
