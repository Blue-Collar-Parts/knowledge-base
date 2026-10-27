# AGENTS.md — knowledge-base

Instructions for AI coding agents (Codex, Claude Code) working in this repository.
**Autonomy tier: `tier:draft-only`.** You may draft a branch and a pull request;
a human merges every pull request. Class 1–3 capabilities only
(`bcp-docs/adr/2026-08-26_capability-tiering-framework.md`): read, run the
repository's own checks, and draft.

## This repository is public

`Blue-Collar-Parts/knowledge-base` is the organisation's one public repository
(`bcp-docs/adr/2026-09-23_agent-write-access-to-public-knowledge-base.md`).

- **A push is a publication.** Anything pushed on any branch is public from that
  moment, and deleting the branch later does not retract it. Pull request review
  gates what reaches `/kb`, not what becomes public. Write every commit as final
  published content.
- **Nothing crosses from a private repository.** Do not copy in anything from
  `bcp-docs`, `ai-knowledge/`, plans, findings, ADRs, or internal prices and
  metrics that are not already public. Write pages as public content from the
  start.
- **No secret values**, in content, commit messages, branch names or pull request
  text.
- **Demonstration record only.** No real carrier name, USDOT number, technician
  or service area on a page.

## What the tier permits

- Create a branch, commit page content, push, and open a pull request.
- Run `python3 -m pytest -q` and `python3 scripts/validate_content.py`; the
  `Validate content` workflow runs the same on every pull request.
- Never merge. Never edit `.github/workflows/`, this file or `LICENSE` as part of
  content work; a change to any of them is its own pull request, decided by a
  human.

## Where the work is tracked

This repository has issues disabled. Content work is tracked as issues in
`bcp-docs`, and each pull request here links the `bcp-docs` issue it serves. Read
`README.md` for the front-matter fields, tracks and citation rules before adding
a page.
