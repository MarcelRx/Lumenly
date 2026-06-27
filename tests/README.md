# Cross-Cutting Tests

Integration and end-to-end test suites that span multiple workspaces.

| Suite | Path | Description |
|-------|------|-------------|
| Unit | `unit/` | Shared unit test utilities |
| Integration | `integration/` | API tests via HTTPX + Docker Compose |
| E2E | `e2e/` | Full-stack mobile flows |
| Contract | `contract/` | OpenAPI schema validation |
| Performance | `performance/` | Load & WebSocket benchmarks |
| Security | `security/` | OWASP scans, JWT tests |

Workspace-specific tests live in `apps/backend/tests/` and `apps/frontend/__tests__/`.

See [`docs/project_structure.md`](../docs/project_structure.md) §11.
