# Project Management

## GitHub Workflow

- **Issues + Milestones**: Use labels `feat:`, `bug:`, `v0.2-`, `v0.3-`, `pipeline`, `infra`, `research`
- **Kanban**: Backlog → In Progress → Review → Done

### Branch & Commit

```bash
git checkout -b fix/issue-1-your-description
git add .
git commit -m "fix: describe what you did, closes #1"
git push origin fix/issue-1-your-description
```

## Documentation Workflow

### Architecture Decision Records

Key architectural choices are captured as ADRs in `docs/adr/`. Each ADR follows Context / Decision / Consequences format.

### Changelog

All notable changes tracked in `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and Semantic Versioning.

## Agent / Copilot Usage

- Prefer `brainstorm approaches for [problem]` over `/brainstorm`
- OpenCode specs → implementation: reference `docs/plans/<plan.md>` in your prompt
