# Password reset

- **Owner:** Dmytro
- **Slice:** Password reset (roadmap Order 102.1)
- **Design:** Claude Design project "Connexity", pages `Connexity Password Reset`,
  `Connexity Sign in` (screens `forgot`, `sent`, `newpw`, `expired`, `changed`, and the
  "Forgot password?" link on `signin`) and `Connexity Email` (variants `reset` and
  `google`), from the export Dmytro handed over on 2026-11-23. The export is copied into
  `designs/screens/` with this change.
- **MCP:** None needed. This is sign-in for a person; an assistant never handles a
  password, and no tool's inputs or answers change.

## Goal

A person who forgets their password can get back in by themselves. Today there is no
reset page or route (checked on `main`: only an unused email template from the starter
kit), so a forgotten password locks the person out until someone edits the database.

After this merges: the sign-in page has "Forgot password?", the person gets an email with
a link that works once and for one hour, sets a new password and is signed in. Nothing in
the flow says whether an email has an account.

This is also the first feature that sends email from Connexity. Invites and billing
emails will reuse the sending, the layout of the email and the "can this deployment send
email" answer.

## Changes

### What a person sees (as designed)

1. **Sign in:** a muted "Forgot password?" link on the Password label row. It is absent
   on a deployment that cannot send email.
2. **Reset your password** (`/forgot-password`): Email, "Send reset link". An address
   that is not a full email gets "Enter a full email address, like alex@example.com."
   under the field.
3. **Check your email** (same page after sending): "If an account uses **the address**,
   a reset link is on its way. The link works once and expires in 1 hour." "Send again"
   is disabled for 45 seconds after each send, with the countdown. When the limit is
   reached: "Too many attempts. Try again later." above the disabled button.
4. **Set a new password** (`/reset/<token>`): the account's email, New password with
   show/hide and "At least 8 characters", "Save password". Too short: "Use at least 8
   characters." under the field.
5. **This link no longer works:** the same page when the link is expired, used or
   unknown. "Send a new link" goes to the forgot page.
6. **Password changed:** "You're signed out on your other devices. Your connected AI
   assistants keep working." "Continue to Connexity" opens the app; the person is already
   signed in on this device.
7. **Two emails,** light, readable in dark mail clients: "Reset your Connexity password"
   with the button, the plain link and the one-hour line; and "Signing in to Connexity"
   for an account that signs in only with Google.

### Backend

- **Ask for a link:** `POST /api/v1/password-reset` with an email. Always answers the
  same way (202, no body that differs) whether or not the email has an account. The
  email is sent after the response, so the answer takes the same time either way.
  - Account with a password: the reset email.
  - Account with no password (signs in only with Google): the "Signing in to Connexity"
    email, no link.
  - No account, or an inactive account: nothing is sent.
  - 404 when the deployment cannot send email.
- **Limits:** per email address, one request every 45 seconds and at most 3 an hour; per
  network address, at most 10 an hour. Over a limit the answer is 429, the same for any
  email. Counted from stored requests, so the limits hold across backend instances.
- **Look at a link:** `GET /api/v1/password-reset/{token}` answers with the account's
  email while the link works, 404 otherwise (expired, used and unknown are the same
  answer).
- **Set the password:** `POST /api/v1/password-reset/{token}` with the new password (at
  least 8 characters, the existing rule). It stores the password, marks the link used,
  ends every web session the person had, and answers with a new session so this browser
  is signed in. A second use of the link is a 404.
- **Whether email works:** the public sign-in options answer (today `GET /auth/google`,
  which says only whether Google is offered) also says whether password reset is
  offered, so the sign-in page can leave the link out.

### Data

- **New table `password_reset_request`:** one row per request, for an account or not:
  a hash of the lower-cased email, a hash of the network address, `user_id` (empty when
  there is no account), a hash of the link's token (never the token), `expires_at`,
  `used_at`, `created_at`. No `company_id`: a person is not owned by one workspace.
  A new link for the same person makes the earlier unused ones stop working.
- **`user.session_version`** (integer, default 0): written into the web session token
  and compared on every request. A reset adds one, so older sessions are refused (401)
  and the browser goes to sign-in. Sessions issued before this change carry no version
  and count as 0, so nobody is signed out by the deploy.
- Personal access tokens and assistants' OAuth tokens do not carry the version and are
  untouched by a reset.

### Email

- `send_email` keeps using SMTP. A failure to send is logged with the provider's answer
  and never changes what the person sees.
- The starter kit's `reset_password` template is replaced by the designed one; a second
  template is added for Google-only accounts. Sources in MJML with the built HTML
  committed, as today.
- The link is `<site address>/reset/<token>`, built from the site address the backend
  already knows.

### Deleted

- The setting `EMAIL_RESET_TOKEN_EXPIRE_HOURS` (48 hours, unused): a link lives one
  hour, fixed.
- The old `reset_password` email template content (replaced, same file names).

### Design and docs

- `designs/17-password-reset.md`: the prompt for these screens. `designs/13-...` gets a
  note that its "do not show Forgot password" is replaced.
- `designs/screens/`: the new export of `Connexity Sign in`, plus `Connexity Password
  Reset` and `Connexity Email`; `designs/README.md` lists them.
- `docs-internal/`: how reset works (link, limits, sessions) in the sign-in doc;
  `data-model.md`; `deployment.md` (the SMTP settings and that reset stays hidden without
  them); `decisions.md`. `.env.example` gets the SMTP settings.
- `docs/` and `README.md` where they describe sign-in.

## Decisions

1. **Decided (Dmytro, roadmap row, 2026-11-23):** single-use link, one hour; the answer
   never reveals whether an email has an account; requests are rate limited; a reset
   ends the person's other web sessions; personal access tokens are not changed; a
   Google-only account gets an email saying so; no MCP tool.
2. **Decided (Dmytro, the design):** the wording and states of every screen and email;
   45 seconds before "Send again"; the link is absent when the deployment cannot send
   email.
3. **Proposed:** the person is signed in on this device when the password is saved (the
   design's "Continue to Connexity" and "signed out on your other devices" say so).
4. **Decided (Dmytro, 2026-11-23):** limits of 3 an hour per email address and 10 an
   hour per network address.
5. **Proposed:** assistants' OAuth connections keep working after a reset, like personal
   access tokens (the design's "Your connected AI assistants keep working").
6. **Proposed:** sessions are ended with a version number on the person, not a list of
   sessions; there is still no "sign out everywhere" button.
7. **Proposed:** expired, used and unknown links look the same.
8. **Proposed:** a Google-only account cannot add a password through reset.
9. **Proposed:** an inactive account gets no email.

## Done when

- Route tests through the API on the local database:
  - a request for a known email, an unknown email and a Google-only account all answer
    the same, and send the reset email, nothing, and the Google email;
  - the link's token is stored only as a hash; the link works once; it stops working
    after an hour; a newer link ends the older one;
  - setting a password signs the person in, the old password no longer works, a session
    from before the reset is refused, and a personal access token still works;
  - a password under 8 characters is refused and the link still works afterwards;
  - the 45-second, per-email and per-address limits answer 429, the same for a known and
    an unknown email;
  - without SMTP settings the request route is 404 and the sign-in options say reset is
    not offered;
  - SMTP timeout and refusal are logged and do not change the answer.
- `make check` passes.
- For Dmytro to check on screen: the six screens and both emails, in dark and light,
  against the design, on a local run with SMTP pointed at a test inbox.

## Out of scope

- **Setting up the email provider in production (Dmytro's; he chose Resend while this
  was built).** Production has no SMTP settings today (checked: the backend has none of `SMTP_*` or
  `EMAILS_FROM_EMAIL`). Needed on `connexity-backend`: `SMTP_HOST`, `SMTP_PORT`,
  `SMTP_USER`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME` as settings and `SMTP_PASSWORD` as
  a secret, plus the provider's DNS records (SPF, DKIM) on the sending domain. Until
  then production shows no "Forgot password?" link and nothing else changes.
- Email verification at sign-up.
- Changing a password while signed in (the Account page, roadmap Order 105.7).
- A "sign out everywhere" button.
- Invite screens and the invite and billing emails that the same design pages show
  (roadmap Orders 102.37 and 102.4 to 102.55).
- Limits on wrong passwords at sign-in.

## Risks

- **Mail lands in spam or is refused** if the sending domain's DNS records are missing.
  The person sees "Check your email" either way. The log line with the provider's answer
  is the only signal.
- **Every web request now reads the session version.** It is on the `user` row the
  request already loads, so no extra query.
- **The network address behind Cloud Run** comes from a forwarded header. If it is read
  wrongly, the per-address limit would apply to everyone at once; the test covers the
  header Cloud Run sends, and the per-email limit does not depend on it.
- **A reviewer should push back** on any answer, status or timing that differs between
  a known and an unknown email.

## Outcome

### Deviations from the plan

- **The email templates are hand-written HTML, not MJML.** The plan said "sources in
  MJML with the built HTML committed". Building MJML needs a tool the repo does not
  have, and the designed emails are two short tables. The starter kit's
  `src/reset_password.mjml` is deleted; `build/reset_password.html` and
  `build/google_sign_in.html` are the sources now.
- **The per-address limit depends on the web app passing the person's address on.** The
  sign-in forms call the backend from the web app's server, so without that every
  request would come from one address. The web app forwards the first address it was
  given, and the backend reads the first address in `X-Forwarded-For`. A caller that
  reaches the backend directly can write any address there, so this limit slows the web
  form but is not a guarantee. The per-email limit does not depend on it. This is the
  plan's third risk, now known to be real.
- **The logo travels inside the email** as a small inline image
  (`email-templates/assets/connexity-logo.png`, 96 pixels, from the design export). The
  first version loaded it from the site's address, which a mail client cannot reach on
  a local or private deployment; Dmytro saw it missing in a test email.
- **`EMAILS_FROM_NAME` was typed as an email address,** so a sender name such as
  "Connexity" would have been refused at start-up. It is plain text now.
- **`send_email` no longer raises and has a 10-second timeout.** It returns whether the
  provider accepted the email; its two existing tests gained the timeout in the options
  they expect.
- **One existing test changed, not weakened:** `test_status_says_whether_google_is_offered`
  compared the whole sign-in options answer with `{"enabled": ...}`. The answer gained
  `password_reset`, so the test now checks the `enabled` field.
- **No separate sign-in doc existed,** so the description is a new
  `docs-internal/password-reset.md`.
- **`docs-internal/deployment.md`:** besides the new email section, the line saying the
  Anthropic admin key was "not set up yet" is corrected; it was set up on 2026-11-23.

### Check results

Route tests through the API on the local database (`TestClient`; no separate
play-through server, the tests send the same requests):

| What | Result |
|---|---|
| `test_password_reset.py` (24 tests: same answer for known, unknown and Google-only; the designed email; hashes only; link works once, for an hour, newer ends older; short password; sessions ended, assistants keep working, sessions from before the change still work; the three limits; no email settings; provider timeout and refusal; the logo inside the email) | passed |
| `test_utils_email.py` | passed |
| Sign-in, Google, OAuth, users, workspaces, personal access tokens, readiness, schema drift | passed |
| Backend `ruff` and `pyright` | passed |
| Frontend `check-types` and `lint` | passed |
| Both emails through the API to Resend's test inbox (local, real SMTP on port 465) | accepted by Resend |
| Full `make check` (plan, backend lint, backend tests and coverage, MCP server tests, frontend lint and types, generated client) | passed, except backend types: 3 errors in the new test file |
| Backend types after fixing those 3 errors, and the new test file again | passed (0 errors; 24 tests) |

For Dmytro to check on screen (local run with SMTP pointed at a test inbox, dark and
light, against `designs/screens/Connexity Password Reset.dc.html`):

1. `/login`: "Forgot password?" on the Password label row. Remove `SMTP_HOST` and
   restart: the link is gone and `/forgot-password` is a 404.
2. `/forgot-password`: "alex@example" shows the error under the field with its icon;
   a full address shows "Sending…" then "Check your email" with the address in the line.
3. "Send again in 45 s" counts down, then "Send again" works; a fourth request within
   the hour shows "Too many attempts. Try again later." above a disabled button.
4. The email: logo, one button, the plain link, the muted line; readable in a dark mail
   client. For an account made with Google: "Signing in to Connexity", no link.
5. The link opens "Set a new password" with the account's email; the eye shows and hides
   the password; "abc12" shows "Use at least 8 characters."; at phone width nothing
   overflows.
6. Saving shows "Password changed"; "Continue to Connexity" opens Work, signed in.
   Another browser that was signed in is sent to sign-in on its next page.
7. Opening the same link again shows "This link no longer works"; "Send a new link"
   goes to the forgot page.

### Code review

Run before the pull request; three bugs found and fixed, two small points left:

- **Fixed:** a session ended by a reset could still approve connecting an assistant,
  because the connection pages read the session cookie themselves. They now check the
  session version too (`test_a_session_from_before_a_password_reset_cannot_allow`).
- **Fixed:** a new password over 40 characters was refused with "Use at least 8
  characters."; it now says "Use at most 40 characters." (not in the design, which has
  no such state).
- **Fixed:** a failed "Send again" showed nothing; it now shows "That didn't work. Try
  again." above the button (also not in the design).
- **Left:** two requests at the same instant can pass a limit by one; the sign-in page
  asks for the sign-in options twice per load.

### Not done

- Dmytro received a real reset email at his own address from a local run and reported
  it "all good" except the logo, which was then embedded and the email sent again; the
  second email's look is his to confirm. The link in those emails points at a local
  run.
- Beyond that, no reset email was opened in a real inbox. Both designed emails were sent through the
  API and Resend (the provider Dmytro chose on 2026-11-23, domain `mail.connexity.ai`)
  to Resend's test inbox, and Resend accepted them; that inbox cannot be read, so the
  link was followed only in the route tests.
- Production's email settings were added to Cloud Run on 2026-11-23, after this pull
  request opened, at Dmytro's request ("Set up Cloud Run"). The sender name
  (`EMAILS_FROM_NAME`) is left for after the deploy, because the code now in production
  refuses a name that is not an email address. No reset has been tried in production.
- How the emails render in real mail clients (Gmail, Outlook, Apple Mail) is not
  verified.
- The screens were not opened in a browser; that is Dmytro's check above.
