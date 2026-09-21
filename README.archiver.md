# SuperInstance (archive snapshot)

> A slice-of-life artifact from the SuperInstance era: a single-commit,
> 6,000-file portfolio of operational scripts, multi-bot coordination
> systems, multi-model API tooling, and deployment choreography —
> captured at one frozen moment.

**What this is:** One team's "everything we've built, in one tree"
commit. Mostly small bash and Python scripts: deploy, monitor, audit,
test, run. Useful as a reference for *how to operate many micro-services
in 2025-style clouds*.

**What it isn't:** A runnable system. The scripts assume specific service
names, ports, and AWS ARNs that are stale by design. Treat the tree as
a *vocabulary* to copy from, not as software to deploy.

## Reading order

1. `STATUS.md` — slice-of-life context, what was good, what's
   salvageable, what was redacted
2. `consolidated-documents/environment-variables.md` — the
   env-var map; even a dead platform is useful as a checklist
3. Pick a leaf that catches your eye:
   - `activelog/` — multi-bot / multi-service operations
   - `ai_society_portal/` — multi-model SF character sim
   - `content-studio-dev/` — multi-model content studio
   - `swarm_intelligence_production/` — swarm experiments
   - `autocoder/` — AutoGen-style code-generation harness

## What was redacted

- `ai_society_portal/API_KEYS.txt` had real keys (Anthropic, OpenAI,
  etc.) — replaced every value with `your_*_here` placeholders.
- `.claude/settings.local.json` was excluded via `.gitignore` rules
  (Claude Code permissions file with local paths and dev-history).

## How to use it

Don't try to run anything top-down. Instead:

```bash
# browse the env-var map
less consolidated-documents/environment-variables.md

# lift the small ops scripts you like
cp activelog/bin/backup-rotation.sh your-project/bin/

# skim the multi-model router example
ls content-studio-dev/
less content-studio-dev/setup_api_keys.sh
```

## License

MIT. See `LICENSE`.

Take this, fork it, evolve it. No attribution required. We'd love to
hear what you build, but you owe us nothing.
