# connexity-evals

## Stack

- Next.js v16, React Server Components
- React Hook Form and server actions for forms
- HttpOnly cookie auth (enables SSR)
- Hey API with client-next for auto-generated typed API client
- Suspense and error boundaries
- Turborepo monorepo, TailwindCSS v4, ShadcnUI (new-york style)
- Validated env vars with Zod (both backend Pydantic and frontend Zod)
- Simple local dev environment, simplified Docker production
- FastAPI backend with SQLModel (SQLAlchemy + Pydantic), Alembic migrations

## Project Structure

```
backend/                        # FastAPI Python backend
  app/
    api/routes/                 # API route handlers
    core/config.py              # Settings (Pydantic BaseSettings)
    models.py                   # SQLModel models (DB + API schemas in one file)
    crud.py                     # Database operations
frontend/                       # Turborepo monorepo
  apps/web/                     # Next.js app
    src/
      app/                      # App Router pages and layouts
      actions/                  # Server actions (form submissions)
      client/                   # AUTO-GENERATED — never edit manually
      components/               # React components (server + client)
      config/                   # Runtime env config
      constants/                # Routes, events, auth constants
      hooks/                    # Custom React hooks
      lib/hey-api.ts            # API client runtime config (fetch strategies)
      schemas/                  # Zod schemas (forms, env config)
      types/                    # Shared TypeScript types
      utils/                    # Utility functions
    openapi-ts.config.ts        # Hey API codegen config
  packages/ui/                  # Shared UI components (ShadcnUI + Radix)
scripts/
  generate-client.sh            # Regenerates frontend API client from backend OpenAPI
```

## Type-Safe End-to-End Contract

The type chain flows: **SQLModel → FastAPI → OpenAPI schema → Hey API codegen → TypeScript SDK → Server Components**

### 1. Define models in backend

`backend/app/models.py` uses SQLModel which is both SQLAlchemy ORM and Pydantic:
- `User(UserBase, table=True)` — DB table model
- `UserCreate`, `UserUpdate` — request body schemas
- `UserPublic` — response schema (excludes sensitive fields like hashed_password)
- `UsersPublic` — paginated wrapper `{ data: list[UserPublic], count: int }`

### 2. Define routes with response_model

Routes in `backend/app/api/routes/` use `response_model=` to control serialization:
```python
@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    return current_user
```

### 3. Regenerate the frontend client

After ANY backend API change (new route, changed model, changed response):
```bash
bash scripts/generate-client.sh
```
This extracts `openapi.json` from FastAPI and runs `@hey-api/openapi-ts` to generate:
- `src/client/types.gen.ts` — all TypeScript types matching backend models
- `src/client/schemas.gen.ts` — JSON schemas for validation
- `src/client/sdk.gen.ts` — service classes (`UsersService`, `ItemsService`, etc.)
- `src/client/client.gen.ts` — HTTP client setup

### 4. Use generated SDK in frontend

```typescript
const result = await UsersService.readUserMe();
const user = result.data; // Type: UserPublic | undefined
```

### Rules

- **NEVER edit files in `src/client/`** — they are regenerated and changes will be lost
- **ALWAYS run `bash scripts/generate-client.sh`** after modifying backend routes or models
- Backend `response_model` controls what gets exposed to the frontend — never return raw DB models without a public schema
- The `openapi-ts.config.ts` strips method prefixes (e.g. `itemsCreateItem` → `createItem`)

## Authentication

### Cookie-based JWT auth

- Backend issues JWT tokens, frontend stores them as HttpOnly cookies
- Cookie name: `auth_cookie` (constant `AUTH_COOKIE`)
- Token expiry: 7 days (168 hours), stored as Unix timestamp in seconds
- Cookie settings: `httpOnly: true`, `secure: true` (prod), `sameSite: 'lax'`, `path: '/'`

### Two fetch strategies in `src/lib/hey-api.ts`

- **Server-side** (`serverFetch`): reads cookies from `next/headers` and forwards them to the backend
- **Client-side** (`clientFetch`): proxies requests through `/api/client-proxy/[...path]` Next.js route handler (browser cannot read httpOnly cookies directly)

The SDK automatically picks the right strategy based on `isServer()`.

### Auth check in layouts

Dashboard layout is an async server component that calls `UsersService.readUserMe()`. Redirects to `/login/` if unauthenticated.

## Frontend Patterns

### Server Components (default)

- Use `async` server components for data fetching — no `useEffect`/`useState` for server data
- Wrap each async component in `<ErrorBoundarySuspense fallback={<Skeleton />}>`
- This enables parallel streaming — components load independently

### Client Components (`'use client'`)

- Forms, theme toggle, interactive elements, anything using hooks
- Dialogs use custom event system (`window.dispatchEvent(new CustomEvent(...))`) defined in `src/constants/events.ts`

### Server Actions (`src/actions/`)

Pattern for form submissions:
```typescript
'use server';
export const createItemAction = async (
  _prevState: ApiResult,
  formData: FormData
): Promise<ApiResult> => {
  const body = Object.fromEntries(formData) as ItemCreate;
  const apiResponse = await ItemsService.createItem({ body });
  const { response: _, ...result } = apiResponse; // strip Response object
  revalidatePath(ITEMS);
  return result;
};
```

### Forms (React Hook Form + Server Actions)

1. Define Zod schema in `src/schemas/forms.ts`
2. Use `useForm()` with `zodResolver` for client-side validation
3. Use `useActionState(serverAction, initialState)` for server action integration
4. On submit: validate with RHF first, then call server action via `startTransition`
5. Handle success/error from `ApiResult` discriminated union

### API Result Type

```typescript
type ApiResult<TData, TError> =
  | { data: TData; error: undefined }
  | { data: undefined; error: TError };
```
Use `isSuccessApiResult()` / `isErrorApiResult()` type guards.

## Environment Variables

### Backend (`.env` from `.env.example`)

Key variables: `SITE_URL`, `DATABASE_URL` or `POSTGRES_*`, `JWT_SECRET_KEY`, `SESSION_SECRET_KEY`, `ENVIRONMENT` (local/staging/production)

### Frontend (`frontend/apps/web/.env` from `.env.example`)

Key variables: `API_URL` (backend URL, no trailing slash), `SITE_URL` (frontend URL, no trailing slash)

Both validated at runtime — backend with Pydantic `BaseSettings`, frontend with Zod via `@next-public-env`.

## Commands

```bash
# Backend
cd backend && uv venv && source .venv/bin/activate && uv sync
uvicorn app.main:app --reload

# Database
docker compose up -d database adminer
cd backend && bash scripts/prestart.sh  # migrations + seed

# Frontend
cd frontend && pnpm install && pnpm dev

# Regenerate API client (requires backend venv activated)
bash scripts/generate-client.sh

# Generate new migration after model changes
cd backend && alembic revision --autogenerate -m "description"
```
