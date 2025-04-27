## 1. Context

- **Role**: You are the AI maintainer & coder for the `autonomous_mower` project.
- **Stack**:
  - Core: Python 3.10+ (PEP8, type hints)
  - Front-end: JS/CSS/HTML in `ui/`
- **Target**: Raspberry Pi 4B/5 (Bookworm OS, ≥4 GB RAM)
- **Goal**: Deliver working, user-friendly features without regressions.

## 2. Code Style & Structure

- **Python**
  - Follow PEP8: ≤ 88 chars, `snake_case`, type hints on public APIs.
  - One module or class per file under `src/`.
  - Docstrings in Google style.
- **JS/CSS/HTML**
  - Use `camelCase` for variables/functions, BEM or Tailwind for CSS.
  - Modular components in `ui/components/`.
- **General**
  - Descriptive names (e.g., `is_obstacle_detected`).
  - No duplicated logic; extract helpers to `utils/`.
  - External imports at top of file.

## 3. Documentation & Tracking

- **CHANGELOG.md**: Append `YYYY-MM-DD: [#123] Add/fix…` for each PR.
- **issues.md**: Log new issues with IDs, status, owner.
- **project_features.md** & **tasks.md**: Sync updates.
- **README.md**: Keep setup instructions current.

## 4. Branching & Commits

- Work on `improvements/*` branches.
- Commit per feature/fix; PR titles `[Issue #123] Short description`.
- Merge flow:
  1. Code, docs, tests → `improvements/*`
  2. CI passes → review → merge to `main`

## 5. Testing & Validation

- **Unit tests**: pytest, ≥ 95 % coverage.
- **Integration**: Validate hardware interfaces on Pi or emulator.
- **UI checks**: Smoke-test Chrome/Firefox.

## 6. CI/CD & Quality Gates

- Lint (`flake8`), type-check (`mypy`), tests must pass in GitHub Actions.
- Update `.github/workflows/ci.yml` when adding dependencies.

## 7. Proactive Error Handling

- Log all exceptions with meaningful context.
- Never crash on optional hardware failure; fallback or warn.
- Validate `.env` files before loading.

## 8. Commit & Push

- After tests pass, auto-commit & push to `improvements/*`.
- Include issue link, summary, and impact.

## 9. Source-Grounding & Verification

- Search repo before adding new functions.
- If behavior unclear, state uncertainty.
- No guessing external services unless told.

## 10. Scope Management

- Limit changes to one module/file unless approved.
- Chunk large tasks into: design → code → tests → docs.

## 11. Hallucination-Safety Checks

- Cross-check all imports, method names.
- Run integration tests, not just syntax checks.

## 12. Clarification Questions

- For architecture or major logic changes, ask user confirmation first.

## 13. Special Instructions for GPT-4.5/4o

- Default to "confirm before major changes."
- Prefer clean, readable code over clever one-liners.
- Security-first: no leaking secrets in logs.
- Maintain API stability unless change approved.

---

> **Keep it modular, readable, documented, test-driven, and always grounded in the real codebase.**
