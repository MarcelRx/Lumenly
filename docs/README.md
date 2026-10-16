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

The following legacy documents are retained as authoritative references until fully migrated:

- [database_design.md](./database_design.md) - Detailed MongoDB schema and indexing strategy (retained for reference)
- [api_contracts.md](./api_contracts.md) - OpenAPI-style API specification (authoritative until migrated)
- [Roadmap.md](./Roadmap.md) - Master development roadmap (authoritative product roadmap)
- [project_structure.md](./project_structure.md) - Project structure (updated to reflect actual implementation)
- [PRD.md](./PRD.md) - Product Requirements Document (authoritative product requirements)

These documents contain detailed information that has not yet been fully integrated into the new structure. They should be consulted for their specific domains until migration is complete.

## Quick Navigation

**For Product Understanding:** Start with [product/vision.md](./product/vision.md)

**For Architecture Understanding:** Start with [architecture/system-architecture.md](./architecture/system-architecture.md)

**For Implementation Guidance:** See [architecture/ai-architecture.md](./architecture/ai-architecture.md) and [architecture/data-flow.md](./architecture/data-flow.md)

**For Technical Decisions:** See [decisions/README.md](./decisions/README.md)

**For Operations:** See [runbooks/](./runbooks/) directory
