```ts


// endpoints
POST /api/register          // Registracija Korisnika
POST /api/login             // Prijava Korisnika
POST /api/sites             // Kreiranje Novog Markdown Sadržaja
GET /api/sites/:id          // Učitavanje Markdown Sadržaja
PUT /api/sites/:id          // Ažuriranje Markdown Sadržaja
DELETE /api/sites/:id       // Brisanje Markdown Sadržaja
GET /api/sites              // Dohvatanje Liste Svi Web Sajtova Korisnika
GET /api/sites/search       // Pretraga i Filtriranje Web Sajtova

// file system za md fajlove
/user_files/
  /user1/
    /site1/
      page1.md
      page2.md
    /site2/
      page1.md
  /user2/
    /site1/
      page1.md

// render .md files next.js
npm install next-mdx-remote @mdx-js/react
npm install react-markdown
incremental static regeneration kad updatuje website - next.js api endpoint
// .mdx custom components
npm install @next/mdx @mdx-js/loader @mdx-js/react

------------
povuce 1 github repo for md or my local files
samo 1 link od github repoa, kreira navbar i ruter
github api or files
login with github, google
------------
mdx custom components - navbar, maybe all h1, h2...
publish to gh-pages - write permission, no google login, or app account, too much about github api
// dilemmas
1. host md files or gh-pages?
2. md editor on site or git pull?
3. custom md css themes?
4. my component library or global css sindresorhus/github-markdown-css
5. admin buttons or panel
6. what in database?
7. monorepo or not? // TO, glavno
8. shadcn or tailwind?
9. which auth? tianlgolo has only user/pass; github only for gh-pages and to export/import app
10. login in next.js lucia and just token in fastapi, or github login in fastapi?
11. define and write down functionality clearly to know what you are building
--------
// research
next.js 15 new features
fastApi boilerplate, auth
review this https://github.com/MaxLeiter/Drift
talk with chatGpt
--------
// features
list all websites
export - build app to host gh-pages or anywhere, nextjs app per each website, packages turborepo // this
just copy app subfolder, css and package.json with next.js and build
download source and dist
add form to set app url

------------
    1. set up pyenv and venv
2. find fastapi starter with auth
3. set up separate frontend and backend with Dockerfiles and docker-compose.yml, easy to find separate next.js and fastapi examples
4. set up Docker and Github Actions preview deployment first
merge https://github.com/tiangolo/full-stack-fastapi-postgresql and https://github.dev/benavlabs/SQLModel-boilerplate


-------------
    run backend locally and in docker
add tiangolo frontend so it can map
review tiangolo backend code, merge with benavlabs/SQLModel-boilerplate
add github actions, deploy to vps
test dev and prod sh scripts
choose next.js project


----------------
// practical
create constants file
create single logger util
fix lint password optional type

// next.js
update dependencies
multi-tenant config https://github.com/vercel/platforms
css vars colors
    Dockerfile
    github actions
    migrate auth ui from tiangolo
testing
openapi client generation
metadata in pages
    typescript folder aliases for prettier sort import
setup prettier for parent folder, root, pogledaj biome tiangolo kako je raspodeljen ruff i biome
prettier ignores parent of node_modules

---------------
add semversioning for both frontend and backend images
common.yml reusable workflow part, print commit hash...
    decide weather to use static next.js with output: "standalone" or next.js api and ssr too
cp and standalone scripts in apps/web call from frontend, turbo
turbo and docker cache maybe, and article

------
    docker-compose.yml database migration, bind mount, env files, env vars Dockerfile NEXT_PUBLIC_, SITE_URL...
migrate healthchecks
use .env (common and docker-compose.yml), .env.frontend, .env.backend and database containers
    extract and reuse workflows checkout, qemu
backend container 500mb ram, alpine
dependantbot yaml, semver
----------
    implement ui for existing login and set up workflow on that example
    run backend, database, frontend locally in dev, only db in docker
run frontend, backend in docker locally
convert client components and hooks to server, e.g. router, react-query - provider, client, ssr
    generate client types
ts path aliases and sort imports config
    replace chakra toast with shadcn toast
------
rewrite with react-hook-form, remove state and onChange, use ShadCN form https://ui.shadcn.com/docs/components/form
use server actions for forms
    test "generate-client": "openapi-ts"
replicated .env in frontend/apps/web for next.js app
-----
        monorepo, eslint 9, tailwind css, typescript, prettier, turbo
clean up ssr csr components, break into small files, tailwind color vars
multitenant, 2 or more apps, dashboard, website
semversioning packages, docker, tag milestones, deploy tag
    log env vars on frontend, must log to see what is runtime, what buildtime
NEXT_PUBLIC_API_URL set at runtime, page must use ssr
    alpine python image
tests
update dependencies
migrate axios to react query, provider, ssr
        review turborepo examples, packages - eslint, prettier, typescript, tailwind, maybe biome
multitenant config
remove github login
break components and clean up, react hook form, react query, ssr layouts
clean up and separate env vars, frontend, backend DOMAIN, FRONTEND_HOST, ENVIRONMENT, PROJECT_NAME, STACK_NAME, SMTP_, SENTRY_DSN, DOCKER_IMAGE_BACKEND, GITHUB_CLIENT_ID
constants folder, routes file
----
formatting in project root, separate prettier and ruff, ignore folders
        import from ui package, not relative path
set up build for all packages, turbo, complex, ui is used as source currently, exports
review workspace packages building and turborepo in examples
https://github.com/vercel/turborepo/blob/main/examples/
its tailwind 4 already
fix git staging lag vs code, watch some complex folder
commit message and version in footer

```
