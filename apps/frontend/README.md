# Lumenly Frontend (React + TypeScript + Vite)

Lumenly's web frontend: React 19, TypeScript, Vite, React Router DOM, Axios, Tailwind CSS.

## Environment Configuration

The frontend reads configuration from Vite environment variables. Create an `apps/frontend/.env.local` file (git-ignored) or set variables in your build environment. **Never put secrets in `VITE_*` variables — anything prefixed `VITE_` is bundled into the client build.**

### API Base URL

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the Lumenly backend API |

All API calls (login, chat, knowledge base) use this single value via `src/api.ts`. Local development needs no configuration — the default points at the local backend.

```bash
# Development (apps/frontend/.env.local) — optional, this is the default:
VITE_API_BASE_URL=http://localhost:8000

# Deployment build (public, non-secret value):
VITE_API_BASE_URL=https://api.yourdomain.com
```

Note: changing `.env.local` requires restarting `npm run dev` (Vite reads env at startup).

## Commands

```bash
npm ci        # reproducible install from package-lock.json
npm run dev   # start Vite dev server
npm run build # tsc -b && vite build (type check + production build)
npm run lint  # ESLint
npm run preview
```

## Original Vite Template Notes

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/plugin-react/blob/main/packages/vite-plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/plugin-react/blob/main/packages/vite-plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, use this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
])

```
