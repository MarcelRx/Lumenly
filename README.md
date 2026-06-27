# Lumenly

AI-powered wellness coaching platform — TurboRepo monorepo.

## Structure

```
Lumenly/
├── apps/
│   ├── backend/          # FastAPI service
│   └── frontend/         # React Native / Expo app
├── packages/
│   └── shared/           # OpenAPI specs, JSON schemas, shared contracts
├── docs/                 # Architecture & product documentation
├── ai/                   # AI modules (agents, knowledge brain, memory)
├── infra/                # IaC (Docker Compose, Helm, Terraform)
├── tests/                # Cross-cutting integration & e2e suites
└── scripts/              # Helper scripts (seeding, initialization)
```

## Prerequisites

- Node.js >= 20
- npm >= 10
- Python >= 3.11 (backend & AI modules)
- Docker (local dev stack)

## Getting Started

```bash
# Install dependencies
npm install

# Run all workspaces in dev mode
npm run dev

# Build all workspaces
npm run build
```

## Documentation

All architectural and product documents live in [`docs/`](./docs/):

| Document | Description |
|----------|-------------|
| [PRD.md](./docs/PRD.md) | Product Requirements Document |
| [system_architecture.md](./docs/system_architecture.md) | High-level component diagram |
| [database_design.md](./docs/database_design.md) | MongoDB schema & indexing |
| [ai_system_design.md](./docs/ai_system_design.md) | AI/ML architecture blueprint |
| [api_contracts.md](./docs/api_contracts.md) | API specification |
| [Roadmap.md](./docs/Roadmap.md) | Master development roadmap |
| [project_structure.md](./docs/project_structure.md) | Monorepo layout & ownership |

## License

Proprietary — Lumenly Engineering Team.
