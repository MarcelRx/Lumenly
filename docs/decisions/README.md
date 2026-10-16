# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for Lumenly. ADRs preserve the rationale behind significant technical decisions so that future developers and AI agents can understand why the system was designed as it was.

## Purpose

ADRs serve as:
- Historical record of architectural decisions
- Context for future development
- Guidance for AI-assisted development
- Documentation of trade-offs and consequences

## ADR Format

Each ADR follows the template in [ADR-0001-template.md](./ADR-0001-template.md).

## ADR Status

- **Proposed:** Decision is proposed but not yet approved
- **Accepted:** Decision has been approved and implemented
- **Deprecated:** Decision is no longer recommended but may still be in use
- **Superseded:** Decision has been replaced by a newer ADR

## Reading ADRs

ADRs are numbered sequentially. Start with the most recent ADR for current architecture, or read in sequence to understand the evolution of the system.

## Creating New ADRs

1. Copy the template from ADR-0001-template.md
2. Assign the next sequential number
3. Fill in all required sections
4. Use "Proposed" status until approved
5. Update status to "Accepted" after implementation
6. Reference related ADRs, commits, and issues

## ADR Index

Currently, no ADRs have been created. The first ADR will be ADR-0001.

## Historical Context

The Lumenly repository has undergone multiple phases of development (Phases 0-15). Significant decisions from these phases should be documented as ADRs for future reference.

## Related Documentation

- [System Architecture](../architecture/system-architecture.md)
- [AI Architecture](../architecture/ai-architecture.md)
- [Agent Orchestration](../architecture/agent-orchestration.md)
- [Data Flow](../architecture/data-flow.md)
