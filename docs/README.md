# Lumenly Documentation

Central index for all architectural and product documents. Other agents should read these files before implementing features.

## Documentation Structure

Lumenly documentation is organized into specialized directories for clarity and maintainability:

### Product Documentation (`product/`)

- [vision.md](./product/vision.md) - Product vision, goals, and use cases
- [requirements.md](./product/requirements.md) - Functional and non-functional requirements with implementation status

### Architecture Documentation (`architecture/`)

- [system-architecture.md](./architecture/system-architecture.md) - System architecture, components, and deployment topology
- [ai-architecture.md](./architecture/ai-architecture.md) - AI components, model providers, and AI-specific architecture
- [agent-orchestration.md](./architecture/agent-orchestration.md) - Agent framework, types, and orchestration
- [data-flow.md](./architecture/data-flow.md) - Data architecture, storage systems, and data flows

### Decision Records (`decisions/`)

- [README.md](./decisions/README.md) - Architecture Decision Record (ADR) process and governance
- [ADR-0001-template.md](./decisions/ADR-0001-template.md) - Template for creating new ADRs

### Engineering Documentation (`engineering/`)

- [testing-and-evaluation.md](./engineering/testing-and-evaluation.md) - Testing strategy and evaluation framework
- [observability.md](./engineering/observability.md) - Metrics, logging, and monitoring
- [error-handling.md](./engineering/error-handling.md) - Error handling strategies and patterns

### Security Documentation (`security/`)

- [security-and-privacy.md](./security/security-and-privacy.md) - Security practices, tenant isolation, and privacy controls

### Deployment Documentation (`deployment/`)

- [deployment-and-infrastructure.md](./deployment/deployment-and-infrastructure.md) - Deployment architecture and infrastructure

### AI Development Documentation (`ai-development/`)

- [agent-workflow.md](./ai-development/agent-workflow.md) - AI agent development workflow for AI-assisted development
- [verification-policy.md](./ai-development/verification-policy.md) - Verification policy for AI-generated code

### Operational Documentation (`runbooks/`)

- Collection of operational runbooks for:
  - Backup and restoration procedures
  - Service recovery (PostgreSQL, MongoDB, Redis, Qdrant)
  - Incident response (backend down, high error rate, high latency)
  - LLM provider failure handling
  - Deployment rollback procedures

### Legacy Documentation (Superseded)

The following documents have been superseded by the reorganized structure above and have been removed:

- ~~system_architecture.md~~ - Removed; content migrated to `architecture/system-architecture.md`
- ~~ai_system_design.md~~ - Removed; content migrated to `architecture/ai-architecture.md`

### Legacy Documentation (Retained for Reference)

The following legacy documents are retained as authoritative references:

- [database_design.md](./database_design.md) - Detailed MongoDB schema and indexing strategy (authoritative MongoDB schema)
- [api_contracts.md](./api_contracts.md) - OpenAPI-style API specification (see `packages/shared/openapi.yaml` for live OpenAPI spec)
- [Roadmap.md](./Roadmap.md) - Master development roadmap (authoritative product roadmap, phases 0-15)
- [project_structure.md](./project_structure.md) - Project structure (updated to reflect actual web application implementation)
- [PRD.md](./PRD.md) - Product Requirements Document (authored product requirements, see `docs/product/requirements.md` for current requirements)

**Status Notes:**

- `database_design.md` - Authoritative MongoDB schema; may be migrated to `docs/data/` in future
- `api_contracts.md` - Retained for reference; live OpenAPI spec in `packages/shared/openapi.yaml`
- `Roadmap.md` - Authoritative product roadmap with all phases 0-15
- `project_structure.md` - Updated to reflect actual implementation (React 19 web app, not mobile)
- `PRD.md` - Authored requirements; current requirements in `docs/product/requirements.md`

## Quick Navigation

**For Product Understanding:** Start with [product/vision.md](./product/vision.md)

**For Architecture Understanding:** Start with [architecture/system-architecture.md](./architecture/system-architecture.md)

**For Implementation Guidance:** See [architecture/ai-architecture.md](./architecture/ai-architecture.md) and [architecture/data-flow.md](./architecture/data-flow.md)

**For Technical Decisions:** See [decisions/README.md](./decisions/README.md)

**For Operations:** See [runbooks/](./runbooks/) directory
