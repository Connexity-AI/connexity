```ts
// next 14, tailwind 3, jest
https://github.com/theodorusclarence/ts-nextjs-tailwind-starter

// vercel templates
// vercel fastapi template, next.js 13, minimal, no docker
https://github.com/vercel-labs/ai-sdk-preview-python-streaming
https://github.com/digitros/nextjs-fastapi

// multi-tenant, subdomains demo, only minimal subdomain logic // this
// next.js 15, shadcn, cva, tailwind 4
https://github.com/vercel/platforms

// vercel templates
https://vercel.com/templates

// not bad, next.js 15, cva, shadcn, tailwind 4, eslint 9, jest, playwright, storybook
// no turborepo, no docker
https://github.com/Blazity/next-enterprise

// shadcn, drizzle postgres, login user/pass
https://github.com/nextjs/saas-starter

// lucia drizzle user/pass, shadcn, server actions, trpc // dobar zapravo
https://github.com/saasykits/nextjs-sessionauth-template

// turborepo filter
https://vercel.com/templates?type=monorepos
// multi-tenant filter
https://vercel.com/templates?type=multi-tenant-apps

// turborepo packages and apps, vitest, biome no eslint, next.js 15, tailwind 4, storybook with all components, clerk auth junk,
// for monorepo and tests, storybook, for reference
// sta ovo kreira zapravo? // ne radi
npx next-forge@latest init
https://github.com/haydenbleasel/next-forge


// second day

// tailwind 4, next.js 15, eslint 9 ok, contentlayer2 - njegov content collections
// like astro, remark, rehype
// messy structure, useless // to
https://github.com/timlrx/tailwind-nextjs-starter-blog

// eslint 8, tailwind 3, jest, next-auth, prisma postgres, stripe, i18n, outdated shadcn // no
https://github.com/Skolaczk/next-starter

// starters bangladesh, all 3 very bad, useless
https://github.com/NextJSTemplates
https://github.com/NextJSTemplates/solid-nextjs
https://github.com/NextJSTemplates/startup-nextjs
https://github.com/NextJSTemplates/play-nextjs

// not bad structure, specific app, not starter
https://github.com/radix-ui/themes


// next.js starters gallery
https://nextjstemplates.com/starter

// shadcn starter - component library
pnpm dlx shadcn@latest init

// todo: fastApi starter // to

/*-------------------------------- fastapi starters ------------------------------*/

// also has @hey-api/openapi-ts, lose, ne moze bez docker
has auth, emails, uv, user and item models, github actions
https://github.com/fastapi/full-stack-fastapi-template

// excellent structure, only fastcrud drawback
https://github.dev/benavlabs/SQLModel-boilerplate

// lightweight, probably
https://github.com/testdrivenio/fastapi-sqlmodel-alembic

// openapi types, @hey-api/openapi-ts
pydantic types -> schema.json -> typescript types
moze i http client, not just types
https://github.com/vintasoftware/nextjs-fastapi-template

// good turborepo, next 14, fastapi
https://github.com/cording12/next-fast-turbo
nikakve prednosti monorepo nema, 2 separate apps deployed
container moze da tera samo 1 proces, inace mora hack uvicorn and next start
docker-compose.yml with frontend and backend services
easy to find separate next.js and fastapi examples

// lightweight, full stack react, flask, docker
https://gitlab.com/testdriven/flask-react-auth

// not bad, comprehensive, full stack, docker, github actions, real world, 1.2k stars, outdated next.js
https://github.com/evroon/bracket

-----
// 7. june

// not bad structure, auth, no sqlmodel, no github actions
https://github.com/MahmudJewel/fastapi-starter-boilerplate

// todo list crud, sqlalchemy, docker, no auth, no migrations, no github actions
https://github.com/testdrivenio/fastapi-crud-async

// reddit
// not good, too minimal, sqlalchemy todo list crud
https://github.com/Saas-Starter-Kit/fastapi_starter
// next.js, bad, bloat, prisma models, services layers
https://github.com/Saas-Starter-Kit/Saas-Kit-prisma


// this next
merge https://github.com/tiangolo/full-stack-fastapi-postgresql and https://github.dev/benavlabs/SQLModel-boilerplate

// todo:

    1. remove docker
    2. extract app
    3. add run scripts
4. merge with benavlabs/SQLModel-boilerplate
5. add minimal docker
6. reuse github actions
7. add next.js, multitenant, docker

-------------
// to review:
// not bad, based on tiangolo starter, uv commands
https://github.com/stevephary/fastapi-base
// aws, too simple, no d-c.yml
https://github.com/ferdinandbracho/bp_fastAPI-sqlalchemy-alembic-docker_uv
// next.js synchronous, big but too simple
https://github.com/manjurulhoque/edu-pulse
// very big project
https://github.com/definableai/definable.backend

----------------------------
----------------------------
// final, next.js


// not bad next.js, tailwind 3
https://github.com/saasykits/nextjs-sessionauth-template

// full stack, openapi client
https://github.com/vintasoftware/nextjs-fastapi-template

// fastapi, can be useful maybe
https://github.com/MahmudJewel/fastapi-starter-boilerplate
// google login
https://github.com/MahmudJewel/fastapi-production-boilerplate
// todo
https://github.com/GabrielVGS/fastapi-base

// todo
https://github.com/moinulmoin/chadnext
https://github.com/deveshshrestha20/FastAPI_Project_Starter
// github gists clone
https://github.com/MaxLeiter/Drift
// next.js starter, review this, no shadcn, bun, turbo, cursor, junk
https://github.com/midday-ai/v1
https://www.reddit.com/r/nextjs/comments/1hg7f4p/what_are_the_best_opensource_codebases_showcasing/
// this is the one actually, ruby, no next.js
https://github.com/maybe-finance/maybe
// this one is next.js
// nx, next.js 13
https://github.com/maybe-finance/maybe-archive


// todo, turborepo, to review
https://github.com/search?q=shadcn%20turborepo&type=repositories
-----
https://github.com/midday-ai/v1 // useless
tailwind 3, biome, next 14, supabase function_
server actions, next-safe-action for ts
@t3-oss/env-nextjs - validating env vars with zod, server, client, runtime // good point
t3 env unused, nonsense
not big, nothing special
-----
https://github.com/codersaadi/turborepo-shadcn // mess, relative paths, big project
tailwind 4, biome
-----
https://github.com/vercel/turborepo/blob/main/examples/with-tailwind/packages/ui/package.json
ui package has build step, tsc and tailwind
-----
// Todo:
next.js dashboard, forms
https://github.com/silicondeck/shadcn-dashboard-landing-template

// Todo: review
https://github.com/launch-ui/launch-ui

// Todo: review, full stack
claude code bloat, big project
https://github.com/UllrAI/SaaS-Starter

// forms tutorial
https://ui.shadcn.com/docs/forms/react-hook-form

// Todo, Next.js part
https://github.com/allipiopereira/turborepo-bun-next-expo

// Todo:
// very clean, good form examples with next-safe-action
https://github.com/shadcnblocks/mainline-nextjs-template
metadata, font, themes
https://github.com/shadcnblocks/mainline-nextjs-template/blob/master/src/app/layout.tsx
-----
// astro
https://github.com/shadcnblocks
-----
// nothing, few components, style tag, useless
https://github.com/akash3444/homeguardian-shadcn-landing-page

// Todo: review, backend only
https://github.com/eslam5464/Fastapi-Template

// Todo: review this again, vercel official
// example how to deploy fastapi to vercel
no database, no code to deploy to vercel, rewriting open-ai stream to vercel ai-sdk stream
https://github.com/vercel-labs/ai-sdk-preview-python-streaming/

// next 16, shadcn, useless
https://github.com/arhamkhnz/next-shadcn-admin-dashboard/

https://github.com/xclusive36/MarkItUp/
// obsidian, markdown, next 16, useful for githubcities
tailwind 4, eslint 9, zustand good, llm apis, drizzle, sqlite, auth, Playwright ci

// Todo: review, fastapi only
https://github.com/manjurulhoque/edu-pulse
// django style
https://github.com/AGTGreg/Djast
// next-auth, review this:
https://www.david-crimi.com/blog/user-auth
// packages
https://github.com/nfraxio/svc-infra
// maybe bad 
https://github.com/manjurulhoque/edu-pulse
-----------
// todo: next.js
https://github.com/Rovis91/saas-builder
// big, nextjs, prisma
https://github.com/boxyhq/saas-starter-kit
// review this, looks promising
https://github.com/vstorm-co/full-stack-fastapi-nextjs-llm-template

```
