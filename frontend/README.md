# frontend/

Faraday's website: React 19 + Vite + TypeScript, black, white and greys only, no motion.

    npm ci            install (once)
    npm run build     type-check and build into dist/ — what `text-2-shorts serve` (FastAPI, :8765) serves
    npm run dev       live reload on http://127.0.0.1:5173 (API, media and previews proxied to :8765)

Every request and response is a Pydantic contract in `backend/schemas/api.py`, typed in `src/api.ts`.
