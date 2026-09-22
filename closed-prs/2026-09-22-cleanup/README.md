# Closed PRs — Sept 22, 2026 inbox cleanup

## Why these are here (no-deletion doctrine)

Per Casey Digennaro's foundational fleet doctrine (2026-09-22):

> "We don't delete. Especially not ideations and creative works. These are slices of life and seeing the progress of versions is animating the past."

> "What we need to do is vectorize with timestamps that connect the maker to what they were making elsewhere to have that creative thought."

This directory preserves PR diffs that were closed during the Sept 22 inbox sweep. They were either superseded by other PRs, brought in via rescue branches, or had merge conflicts with newer main content. **None of the creative work is lost** — every diff, branch SHA, and metadata is preserved here for time-based creative-lineage reconstruction.

## What's in here

| PR | Repo | Title | Status |
|---|---|---|---|
| #11 | SuperInstance/jeviter | seed 7: sequential-merge governor | Superseded by #13 (cleaner naming). Reopened with archive note. |
| #1 | SuperInstance/cargo-line-tycoon | docs: recommendations-from-kimi1/ | Content already on main via `rescue/kimi1-recommendations-20260922`. Reopened with archive note. |
| #1 | SuperInstance/quilt-studio | CANON.md: quilt-studio joins the fleet canon | Superseded by main's newer CANON.md (verified 2026-09-20). Reopened with archive note. |

## Manifest format

Each PR's metadata (creator, branch, head SHA, body, timestamps) is in `manifest.json` alongside the `.diff` files.

## Recovery

To recover any closed PR's branch state:

```bash
# Get head SHA from manifest.json, then:
git fetch origin <head_sha>:recovered-pr-<num>
```

To re-view the diff:

```bash
cat closed-prs/2026-09-22-cleanup/archive-<repo>-pr<num>.diff
```

## Vectorization plan

For full doctrine compliance, the next step is to vectorize each archived diff with:
1. The maker's other in-flight PRs at the same timestamp
2. The maker's active branches in other repos
3. Issue/PRs they commented on around the same time

This creates a "creative context" vector that lets you ask: "What was Casey working on when this PR was filed?" — far richer than a single PR state.
