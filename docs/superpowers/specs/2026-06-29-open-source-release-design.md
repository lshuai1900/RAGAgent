# Open Source Release Preparation Design

Date: 2026-06-29

## Goal

Prepare Ragent-Py for a strict open-source release. The work focuses on repository hygiene, public-facing documentation, license and contributor files, CI, and release verification. It must not add new product features or expand the MVP scope.

## Current Context

Ragent-Py is a Python/FastAPI + Vue MVP inspired by the architecture ideas of `nageoffer/ragent`. The project already includes backend source, frontend source, tests, migrations, configuration templates, architecture docs, third-party notices, and contributor-facing AI collaboration rules.

`AGENTS.md` defines the current phase as "完整 MVP 代码版 — 开源整理与验收". This release preparation must stay inside that phase: publish-readiness, documentation alignment, security hygiene, and validation only.

## Scope

### In Scope

- Clean local/runtime artifacts from the working tree, including virtual environments, `node_modules`, Python bytecode caches, test caches, build outputs, logs, local Milvus data, and other generated files.
- Verify and update `.gitignore` so these artifacts remain excluded.
- Check for accidentally committed or working-tree secrets, including API keys, tokens, passwords, `.env` files, and provider credentials.
- Add an MIT `LICENSE` file.
- Rewrite `README.md` as a public open-source landing page.
- Add `CONTRIBUTING.md` with development, testing, commit, and pull request guidance.
- Add `SECURITY.md` with vulnerability reporting and secret-handling guidance.
- Add GitHub collaboration templates:
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - `.github/ISSUE_TEMPLATE/bug_report.yml`
  - `.github/ISSUE_TEMPLATE/feature_request.yml`
- Add `.github/workflows/ci.yml` for backend and frontend checks.
- Run local release verification where the environment supports it.
- Report any failing checks accurately.

### Out of Scope

- No new RAG business capabilities.
- No implementation of deferred MVP items such as MCP, JWT authentication, multi-tenancy, model rerank, complex trace spans, knowledge graph, or Celery/Dramatiq queues.
- No technology stack replacement.
- No broad business-code refactor unless a verification failure directly blocks the open-source release and the fix is narrow.
- No mandatory CI integration test job that requires PostgreSQL + Milvus services.

## README Design

`README.md` should become the main entry point for new users and contributors. It should be concise, navigable, and oriented around getting the project understood and running.

Recommended structure:

1. Project title and one-line positioning.
2. Project status: MVP/open-source preparation stage.
3. Feature overview:
   - Backend capabilities.
   - Frontend capabilities.
   - Engineering and observability capabilities.
4. Explicit non-goals and deferred features.
5. Architecture overview with a short layered diagram and links to `docs/ARCHITECTURE.md` and `AGENTS.md`.
6. Requirements:
   - Python 3.11+
   - uv
   - Docker / Docker Compose
   - Node.js 20+
7. Quick start:
   - Start dependencies.
   - Install backend dependencies.
   - Configure environment variables.
   - Run migrations.
   - Start backend.
   - Install and start frontend.
8. Configuration:
   - `.env.example`
   - `configs/config.yaml`
   - key environment variables such as `QWEN_API_KEY` and `RAGENT__MILVUS__URI`
   - secret safety warning.
9. Minimal API flow:
   - health check
   - create knowledge base
   - upload document
   - query document status
   - run SSE chat
10. Development and validation commands.
11. Documentation map linking to existing `docs/` files.
12. Contributing, security, third-party notices, and license.

The README should avoid becoming a full API reference. Existing detailed docs should remain linked rather than duplicated.

## Open Source File Design

### LICENSE

Use MIT License.

### CONTRIBUTING.md

Include:

- Required tooling.
- Backend setup and commands.
- Frontend setup and commands.
- Unit and integration testing expectations.
- Conventional Commit examples matching project style.
- Pull request checklist.
- Guidance to avoid committing generated files and secrets.

### SECURITY.md

Include:

- Supported version policy for the current MVP branch.
- How to report vulnerabilities privately.
- What information to include in a report.
- Secret-handling guidance.
- Reminder not to publish exploit details or real credentials in issues.

### GitHub Templates

Add issue templates for bug reports and feature requests. Add a pull request template with sections for summary, validation, risk, and checklist.

## CI Design

Add `.github/workflows/ci.yml` with two jobs.

### Backend Job

- Runs on `ubuntu-latest`.
- Uses Python 3.11.
- Installs `uv`.
- Runs:
  - `uv sync --dev`
  - `uv run ruff check src tests`
  - `uv run ruff format --check src tests`
  - `uv run mypy src/ragent`
  - `uv run pytest tests/unit`

### Frontend Job

- Runs on `ubuntu-latest`.
- Uses Node.js 20.
- Runs in `web/`:
  - `npm ci`
  - `npm run type-check`
  - `npm run build`

### Integration Tests

Do not include integration tests in the default CI job for this release preparation, because they require PostgreSQL and Milvus service orchestration. Document them as recommended local release checks:

```bash
make deps-up
make migrate
make test-integration
```

## Local Verification Design

Run the following if the local environment supports them:

```bash
make lint
make typecheck
make test-unit
cd web && npm run type-check
cd web && npm run build
```

Run integration checks only if Docker dependencies are available:

```bash
make deps-up
make migrate
make test-integration
```

All failures must be reported faithfully. If a failure predates this open-source cleanup and is not safe to fix within scope, document it instead of hiding it.

## Security and Repository Hygiene Design

- Use Git tracked-file inspection to identify committed files.
- Use content search for common secret patterns and known key variable names.
- Confirm `.env.example` only contains placeholders.
- Remove local generated artifacts from the working tree when safe.
- Do not delete user-created source, docs, migrations, configs, or tracked project files without inspecting them first.

## Implementation Boundaries

The implementation should primarily modify documentation, repository metadata, CI configuration, and ignore rules. It may remove generated local artifacts. It should not change application behavior unless a small fix is required to make existing quality gates pass and the cause is directly related to release readiness.

## Acceptance Criteria

- `README.md` is rewritten as a clear open-source landing page.
- MIT `LICENSE` exists.
- `CONTRIBUTING.md` exists.
- `SECURITY.md` exists.
- GitHub issue and PR templates exist.
- GitHub Actions CI exists for backend and frontend checks.
- `.gitignore` covers generated/runtime artifacts used by this project.
- No obvious committed secrets are found.
- Local generated artifacts are cleaned from the working tree where safe.
- Backend and frontend validation commands are run or explicitly marked as skipped with reasons.
- No deferred MVP feature is implemented.
