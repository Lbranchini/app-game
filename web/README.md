# Web — React frontend

Vite + React 18 + TypeScript + Tailwind. Talks to the FastAPI backend at `http://localhost:8000` via the `/api` proxy configured in `vite.config.ts`.

## Setup

```bash
cd web
npm install
```

## Develop

In one terminal:
```bash
cd server && agora-api          # FastAPI on :8000
```

In another:
```bash
cd web && npm run dev           # Vite on :5173
```

Open http://localhost:5173. Use the **Dev token** button on the login screen to grab a local JWT until real OAuth credentials are configured.

## Layout

```
web/
├── package.json
├── vite.config.ts          /api proxy + path alias
├── tailwind.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx            React + Router + React Query providers
    ├── App.tsx             Routes + RequireAuth gate + header
    ├── index.css           Tailwind directives
    ├── api/client.ts       fetch wrapper with Bearer token
    ├── pages/              Login, Characters, Arenas
    ├── stores/authStore.ts JWT in localStorage + zustand
    └── types/api.ts        mirror of server Pydantic models
```

## Status

Scaffolded; pages render character and arena lists from the backend. Battle/draft screens are next once the engine is exposed via WebSocket. See `docs/04-roadmap.md`.
