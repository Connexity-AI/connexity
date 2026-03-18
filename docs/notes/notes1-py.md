```py

# .env file is passed here

# backend/app/core/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",

# local database url in Docker
SQLALCHEMY_DATABASE_URI=postgresql+psycopg://postgres:password@localhost:5432/app

# Dbeaver connection
url: jdbc:postgresql://localhost:5432/app
user: postgres
password: password

scripts folders in root and in /backend

# openapi.json is available on this url
http://localhost:8000/api/v1/openapi.json

# routes/pages

# auth
'/login'
'/recover-password'
'/reset-password'
'/signup'

# root
'/'
'/admin'
'/items'
'/settings'

----------
prettier formats all files, /backend in prettierignore
ruff formats /backend
---
docker-compose.yml special name, disabled format by containers extension
----
cant format (.json) in folder above node_modules
------------------
# standalone server.js path fro monorepo
githubcities/frontend/apps/web/.next/standalone/apps/web/server.js
SITE_URL can be different (env var) in each environment, but must be prefixed with NEXT_PUBLIC_* not to be inlined during build for static site
-------
dev and prod docker-compose.yml and folder structure must match

--------------
prettier in frontend root, not in package
format imports aliases in different packages
project root without formatting for now
------
exports is paths mapping for imports from @workspace/ui
exported as source, without build to dist and transpile
"exports": {
# . is @workspace/ui
"./globals.css": "./src/styles/globals.css",
}
@workspace/ui - package
@workspace/ui/src/styles/globals.css to @workspace/ui/globals.css
import '@workspace/ui/globals.css';
import { useIsMobile } from '@workspace/ui/hooks/use-mobile'; # without .ts
-----
# reminder
must copy static and public folders for standalone node server.js
-----
# desktop markdown editor
https://typora.io/
-----
can import .mdx in next.js page
import Privacy from "./privacy.mdx";
# https://github.com/shadcnblocks/mainline-nextjs-template/blob/master/src/app/privacy/page.tsx
------
user session is checked with current_user: CurrentUser dependency in backend/app/api/deps.py
cookie is checked with CookieDep = Annotated[str, Depends(cookie_scheme)] dependency
jwt is created in create_access_token() and cookies is set in set_auth_cookie() in backend/app/core/security.py
----
python debugger vs code
rewrite from localStorage to cookie (server only js)
frontend/apps/web/src/lib/auth.ts
-----
# api url where is defined originally
frontend/src/main.tsx
OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}
----------------------


```

## Global dependencies

1. use pynev
2. install `uv` globally in pyenv

```bash
pip install uv
```
3. install dependencies

```bash
# in activated venv
source .venv/bin/activate

# install
uv sync

# run
uvicorn app.main:app --reload

```

If renamed folder `githubcities` to `full-stack-fastapi-template-nextjs` must delete and recreate venv, it has outdated absolute path to venv.

```bash
cd backend
rm -rf .venv
uv venv
```

unify env vars
frontend NEXT_PUBLIC_SITE_URL and FRONTEND_HOST 
backend NEXT_PUBLIC_API_URL and DOMAIN
-----
DOMAIN is only used in Traefik in original repo, can be deleted, backend doesn't use it

