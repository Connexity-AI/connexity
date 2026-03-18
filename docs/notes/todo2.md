```ts
fix css formatting
separate ssr layouts from client components, maybe server actions for forms
fix danger button text, tab title cursor pointer
fix eslint errors, error checking didnt work before
handle runtime env vars for multiple envs, arm1, opi, rpi, mpc and deploy
runtime env vars - must use ssr components
github actions deploy with tailscale
react-query for fetching or ssr
card list fix flex full height
cva css for components
frontend tests, vitest, playwright
--------
client components because of localStorage auth
const token = localStorage.getItem('access_token');
refactor backend to use cookie instead of localStorage // important
look in other fastApi starters

git checkout -b feature/cookie-auth

https://github.com/fastapi/full-stack-fastapi-template/pull/1606/files
https://github.com/sinkozs/full-stack-fastapi-template/tree/use-http-only-cookie
https://github.com/fastapi/full-stack-fastapi-template/discussions/1564

fix python formatting, 2 newlines between functions, 1 new lines ..., installed "charliermarsh.ruff" extension
keep backend tests running correctly
migrate cookie logic in frontend
tiangolo already uses react-query, its replaced with axios in next.js project
frontend has no tests, next.js deleted them, original has only playwright e2e, no unit tests
------
forward cookie from client on each request, instead of localStorage token
setup react query and regenerate client
setup error logger
forward cookie in verifySession()
simply call const me = ApiClient.usersReadUserMe() ?
client next.js and react-query plugin // better next.js that uses fetch options for ssr
https://heyapi.dev/openapi-ts/clients/next-js
https://heyapi.dev/openapi-ts/plugins/tanstack-query
fix format script and turbo
// which client
https://chatgpt.com/s/t_68fde3f3aac481918ed11203317d902a
find react-query client with server components tutorial
react-query only for client side events, e.g. infinite scroll
server state management lib for client
analyze existing react-query openapi client in tiangolo
----
use only next-client and for client calls use next-client in react-query fetch data function_
use next-client in queryFn in react-query for client fetching and thats it // final
const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
})

do i need to pass token as header from cookie?
must configure react-query for client fetching with client-next queryFn
----
server actions
https://github.com/vintasoftware/nextjs-fastapi-template/blob/main/nextjs-frontend/components/actions/items-action.ts
simple client.setConfig({ baseURL }) call, axios client, "@hey-api/openapi-ts": "^0.60.1",
https://github.com/vintasoftware/nextjs-fastapi-template/blob/main/nextjs-frontend/lib/clientConfig.ts
validate env vars with createEnv t3
// client-next config example
https://github.dev/hey-api/openapi-ts/tree/main/examples/openapi-ts-next
bash scripts/generate-client.sh is in root but must use activated backend venv
in root because it uses both frontend and backend
-----
build docker scripts
implement login so i can generate cookie and test client calls
form server actions but it hits fastApi?
rename LoginService.loginAccessToken on backend to LoginService.loginAccessCookie
no react-query for forms, but server actions
server action needs to forward cookie from response
maybe better login direct call without server action
---------
always use default ThrowOnError = false variant, LoginService.loginAccessToken<false>
so no exception and error prop is returned, for ApiResponse
ApiResponse union type 1 branch possible, must work for isError and isSuccess utils
const isError = isErrorApiResult(state);
const isSuccess = isSuccessApiResult(state);
3 states, initial, success, error
both isSuccess === false and isError === false  => initial state
set correct host for forwarded cookie, for cors
ts ignore any
read about parallel fetch and loading and error handling in server component
-----
loading.tsx, error.tsx, not-found.tsx
Promise.all or Promise.allSettled
skeletons for loading, 404 page design
isLoading optional prop on Card components, handle loading and errors with Suspense and ErrorBoundary wrappers
nested components folder dashboard/cards
handle errors and loading in dashboard server components
create Error classes
page should check auth first and display error.tsx or redirect
----
make existing ui work, then refactor auth, error, loading
add 404, 500 pages, styling
improve docker, traefik deployment
add no-monorepo branch
fix tests
add github auth and ui
extract metadata as constants
t3 env for env vars https://github.com/t3-oss/t3-env
skeleton, noData components
        create seed with many users and items for pagination
consistent naming UserEditDialogAction - clean up perfectly
        mount DialogUserUpdate in a single place, event
maybe add sorting in read_users() read_items()
use sentence case in all text
redirect to login on expired cookie
fix sidebar jumping
custom error (exception) classes
understand Client options, throwOnError handling - rejected promise
lint, unused imports, tests
use class-variance-authority in ui
toaster on login success, ssr?
tag existing docker image for backup deploy
prettier like ruff, 1 newline lines, 2 newlines functions
        handle max page for user and item with 404
sort by updatedAt
        uuid truncate in table maybe, responsive table
        per page folder structure in dashboard
        remove unused auth and client files in lib
extract constants on backend
reuse and extend zod schemas
default_ sort by updatedAt in SQLModel
add register form, user/pass and github
deploy original tiangolo template // to
add success, warning vars in css vars theme
        current dashboard only for admin, items and settings for user
cursor pointer for tabs
        tabs skeleton // to
extract backend messages as_ constants, maybe i18
isr pooling ssr, multiple admins, maybe
        write truncate and reseed db script
        refactor sidebar
-----
        ui for user and admin and redirects, roles on frontend
        redirect from server component on non existing pages in pagination
        currentUser must fetch in page for protected routes, is_superuser redirect, middleware?
        colocate admin pages under /admin route segment and protect in middleware.ts
        dashboard-admin and dashboard-user
        admin vidi sve iteme, user samo njegove
        no delete account for superuser
-----
fix cookie expiration - must be in seconds
response.set_cookie(
    # Cookie expiration and JWT expiration match
    # ! Cookie expiration must be in seconds
    max_age=int(expires_delta.total_seconds()),
    expires=int(expires_delta.total_seconds()),
)
use all env vars from tiangolo
add toasts
```
