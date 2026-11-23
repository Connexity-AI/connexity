# Password reset

How a person who forgot their password gets back in. Plan:
[`plans/2026-11-23-password-reset.md`](../plans/2026-11-23-password-reset.md). Screens and
emails: `designs/screens/Connexity Password Reset.dc.html`.

## The flow

1. **Sign in** shows "Forgot password?" when the deployment can send email
   (`password_reset` in `GET /api/v1/auth/google`, true when `SMTP_HOST`,
   `EMAILS_FROM_EMAIL` and `SITE_URL` are set).
2. **`POST /api/v1/password-reset`** with an email records the request and answers 202
   with no body, whatever the email. The email is sent after the response.
   - An active account with a password gets "Reset your Connexity password" with the
     link `<SITE_URL>/reset/<token>`.
   - An active account without a password (it signs in only with Google) gets "Signing
     in to Connexity", with no link. It cannot add a password this way.
   - No account, or an inactive one: nothing is sent.
3. **`GET /api/v1/password-reset/{token}`** answers the account's email while the link
   works. Expired, used and unknown links are the same 404.
4. **`POST /api/v1/password-reset/{token}`** with `new_password` (at least 8 characters)
   stores the password, uses up the link and answers a new web session, so the browser
   is signed in.

## Rules

- **Nothing reveals whether an email has an account:** same status, same body, and the
  same time taken, for every email. The limits below count requests for unknown emails
  too.
- **A link works once and for one hour.** Only its SHA-256 hash is stored
  (`password_reset_request.token_hash`). Asking again ends the person's earlier unused
  links.
- **Limits** (Decided by Dmytro, 2026-11-23): per email, one request every 45 seconds
  and 3 an hour; per network address, 10 an hour. Over a limit the answer is 429. They
  are counted from `password_reset_request`, so they hold across backend instances.
- **The network address** is the first one in `X-Forwarded-For`. The web app asks on the
  person's behalf and passes their address on. A caller that reaches the backend
  directly can write anything there, so the per-address limit is a brake on the web
  form, not a guarantee; the per-email limit does not depend on it.
- **A reset ends the person's other web sessions.** `user.session_version` is written
  into each web session token (`sv`) and compared on every request; a reset adds one.
  Tokens from before the claim existed count as version 0.
- **Assistants keep working.** Personal access tokens and OAuth tokens do not carry the
  version.
- **A send that fails** (the provider refuses or cannot be reached within 10 seconds) is
  logged as a warning with the provider's answer. The person sees "Check your email"
  either way.

## Email

Sent over SMTP (`send_email` in `app/utils.py`). The two templates are plain HTML in
`app/email-templates/build/`, written by hand, light with a dark variant for mail
clients that honour `prefers-color-scheme`. The logo travels inside the email as an
inline image (`app/email-templates/assets/connexity-logo.png`), so it shows whatever the
site's address is. Invites and billing emails will reuse the same sending
and layout.
