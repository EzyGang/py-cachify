# py-cachify Agent Guide

Python library for caching and distributed locking. Backend-agnostic with out-of-the box support for in-memory, Redis, and DragonflyDB.

## Essential Commands

**Install dependencies:**
```bash
uv sync
```

**Run checks (order matters):**
```bash
uv run task ruff        # Format & lint (includes unsafe fixes)
uv run task mypy-lint     # Type check
uv run task tests         # Unit tests (100% coverage enforced)
```

**Or run combined:**
```bash
uv run task format-and-lint  # ruff + mypy
```

**Integration tests** (requires Redis on localhost:6379):
```bash
uv run task integration-tests
```

**Docs local server:**
```bash
uv run task docs-dev
```

## Architecture

- **Public API**: Exported from `py_cachify/__init__.py`
- **Implementation**: `py_cachify/_backend/` (private)
- **Key exports**: `init_cachify()`, `cached()`, `lock()`, `once()`, `Cachify`
- **Library contract**: Users call `init_cachify()` once globally, then use decorators

## Testing Notes

- **Unit tests**: `tests/` - use in-memory cache, no external deps
- **Integration tests**: `integration_tests/` - requires Redis at `redis://localhost:6379`
- **Coverage**: 100% required (`--cov-fail-under=100` in pytest config)
- **Fixture**: `init_cachify_fixture` resets global state between tests

## Tooling Constraints

- **Ruff**: Line length 120, single quotes, Python 3.9+ target
- **MyPy**: Strict mode enabled
- **Python versions**: 3.9 - 3.14 (all tested in CI)
- **Package manager**: `uv` (frozen lockfile in CI via `UV_FROZEN=1`)
- **Build**: `hatchling` build backend

## Common Gotchas

1. **Global state**: Tests must reset `py_cachify._backend._lib._cachify` between runs or use `init_cachify_fixture`
2. **Integration tests**: Always require running Redis; use different DB indexes (0-3) to avoid collisions
3. **Decorators**: `@cached()`, `@lock()`, `@once()` require `init_cachify()` called first or raise `CachifyInitError`
4. **Async/sync**: Library supports both; check both paths when modifying backend code
5. **Coverage**: The CI fails if coverage drops below 100%

## CI & Release

- Checks run on PRs to `main`, `v/*`, `rc/*` branches
- Release is manual via `workflow_dispatch` on `build-and-publish.yml`
- SonarCloud analysis runs after tests pass
