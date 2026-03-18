
git checkout -b feature/github-login-2

better to send token as param, no need to unset forwarded cookie
send token, maxAge, expires as json and query params for login and oauth callback, next.js server action and api sets cookie
cookie is limited per domain to pass args
cookie subdomain will fail for completely different backend domain