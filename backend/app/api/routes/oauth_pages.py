"""The pages a person sees when their assistant asks to connect to Connexity.

Built from `designs/screens/Connexity Sign in.dc.html` (screen "connect"): sign in or
create an account, then approve the connection. The backend renders them because the
OAuth flow runs on the backend (proxied by the MCP server), not in the web app. The
colours are the design system's tokens, dark unless the browser prefers light.
"""

import base64
import html
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi.responses import HTMLResponse

type ErrorField = Literal["form", "email", "password"]

# The three-loop logo, the same image as the web app's favicon.
LOGO_DATA_URI = (
    "data:image/png;base64,"
    + base64.b64encode(
        (
            Path(__file__).resolve().parents[2] / "assets" / "connexity-logo.png"
        ).read_bytes()
    ).decode()
)


@dataclass(frozen=True)
class AuthorizeParams:
    """The OAuth request carried through every page as hidden fields."""

    response_type: str
    client_id: str
    redirect_uri: str
    scope: str | None
    state: str | None
    code_challenge: str | None
    code_challenge_method: str | None
    resource: str | None

    def hidden_fields(self) -> str:
        fields = {
            "response_type": self.response_type,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
            "resource": self.resource,
        }
        return "\n".join(
            f'<input type="hidden" name="{html.escape(name)}" '
            f'value="{html.escape(value or "")}">'
            for name, value in fields.items()
        )


_STYLE = """
:root {
  --s0:#121314; --s1:#1a1b1d; --border:#2a2c2f; --bc:#6b6f75; --ink:#ececea;
  --ink2:#a3a5a9; --ink3:#8b8e93; --accent:#ececea; --on-accent:#121314;
  --crit:#f59ab0; --wash:#26282b;
}
@media (prefers-color-scheme: light) {
  :root {
    --s0:#f5f4f2; --s1:#ffffff; --border:#e3e1dd; --bc:#85837e; --ink:#17181a;
    --ink2:#5e6065; --ink3:#6e7075; --accent:#17181a; --on-accent:#f5f4f2;
    --crit:#a3173f; --wash:#efeeea;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh; background: var(--s0); color: var(--ink);
  font-family: 'Figtree', system-ui, sans-serif; font-size: 15px; line-height: 22px;
  -webkit-font-smoothing: antialiased;
}
main {
  width: 100%; max-width: 360px; margin: 0 auto; padding: 96px 16px 48px;
  display: flex; flex-direction: column; gap: 32px;
}
.brand { display: flex; align-items: center; gap: 8px; height: 32px; }
.brand img { width: 22px; height: 22px; border-radius: 6px; }
.brand span { font-size: 15px; font-weight: 500; }
.stack { display: flex; flex-direction: column; gap: 24px; }
.head { display: flex; flex-direction: column; gap: 4px; }
.lead { color: var(--ink2); }
h1 { margin: 0; font-size: 20px; line-height: 28px; font-weight: 500; }
p { margin: 0; }
form { display: flex; flex-direction: column; gap: 16px; margin: 0; }
label { display: flex; flex-direction: column; gap: 6px; }
.label, .muted, .hint, .error, .switch { font-size: 13px; line-height: 18px; }
.label, .muted, .switch { color: var(--ink2); }
.hint { color: var(--ink3); }
.error { color: var(--crit); }
input[type=email], input[type=password], input[type=text] {
  height: 40px; padding: 0 12px; border-radius: 8px; border: 1px solid var(--bc);
  background: var(--s1); color: var(--ink); font: inherit; outline: none;
}
input.bad { border-color: var(--crit); }
.actions { display: flex; flex-direction: column; gap: 8px; padding-top: 8px; }
button {
  width: 100%; height: 40px; border-radius: 8px; font: inherit; cursor: pointer;
}
.primary { border: 0; background: var(--accent); color: var(--on-accent); font-weight: 500; }
.primary:hover { opacity: .88; }
.secondary { border: 1px solid var(--bc); background: transparent; color: var(--ink); }
.secondary:hover { background: var(--wash); }
a { color: var(--ink); }
.switch a { color: var(--ink); }
"""


# Another site must not frame these pages and trick a person into pressing Allow.
_NO_FRAMING = {
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
}


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        headers=_NO_FRAMING,
        content=f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500&display=swap" rel="stylesheet">
<style>{_STYLE}</style>
</head>
<body>
<main>
<div class="brand"><img src="{LOGO_DATA_URI}" alt=""><span>Connexity</span></div>
{body}
</main>
</body>
</html>""",
    )


def sign_in_page(
    *,
    params: AuthorizeParams,
    assistant: str,
    switch_query: str,
    signup: bool = False,
    error: str | None = None,
    error_field: ErrorField = "form",
    email: str = "",
    full_name: str = "",
) -> HTMLResponse:
    """Sign in, or create an account, before approving the assistant."""

    def field_error(field: ErrorField) -> str:
        if error and error_field == field:
            return f'<span class="error">{html.escape(error)}</span>'
        return ""

    def bad(field: ErrorField) -> str:
        return ' class="bad"' if error and error_field == field else ""

    title = "Create an account" if signup else "Sign in"
    action = "/oauth/authorize/signup/confirm" if signup else "/oauth/authorize/confirm"
    name_field = (
        '<label><span class="label">Name</span>'
        f'<input type="text" name="full_name" autocomplete="name" '
        f'value="{html.escape(full_name)}"></label>'
        if signup
        else ""
    )
    password_hint = (
        '<span class="hint">At least 8 characters</span>'
        if signup and not (error and error_field == "password")
        else ""
    )
    if signup:
        switch = (
            "Already have an account? "
            f'<a href="/oauth/authorize?{html.escape(switch_query)}">Sign in</a>'
        )
    else:
        switch = (
            "New to Connexity? "
            f'<a href="/oauth/authorize/signup?{html.escape(switch_query)}">'
            "Create an account</a>"
        )
    body = f"""
<div class="stack">
  <div class="head">
    <span class="lead">{html.escape(assistant)} wants to connect to Connexity</span>
    <h1>{title}</h1>
  </div>
  <form method="post" action="{action}" novalidate>
    {params.hidden_fields()}
    {name_field}
    <label>
      <span class="label">{"Work email" if signup else "Email"}</span>
      <input type="email" name="email" autocomplete="email" value="{html.escape(email)}"{bad("email")}>
      {field_error("email")}
    </label>
    <label>
      <span class="label">Password</span>
      <input type="password" name="password" autocomplete="{"new-password" if signup else "current-password"}"{bad("password")}>
      {password_hint}
      {field_error("password")}
    </label>
    <div class="actions">
      {field_error("form")}
      <button type="submit" class="primary">{"Create account" if signup else "Sign in"}</button>
    </div>
  </form>
  <span class="switch">{switch}</span>
</div>"""
    return _page(f"{title} · Connexity", body)


def consent_page(
    *,
    params: AuthorizeParams,
    assistant: str,
    person: str,
    switch_query: str,
) -> HTMLResponse:
    """Approve or cancel the assistant's connection, once signed in."""
    name = html.escape(assistant)
    body = f"""
<div class="stack">
  <h1>Connect {name} to Connexity</h1>
  <p>{name} will be able to see and work in the workspaces you can reach, on your behalf. Everything it does is recorded as done by your assistant.</p>
  <span class="muted">{html.escape(person)}</span>
  <div class="actions">
    <form method="post" action="/oauth/authorize/allow">
      {params.hidden_fields()}
      <button type="submit" class="primary">Allow</button>
    </form>
    <form method="post" action="/oauth/authorize/cancel">
      {params.hidden_fields()}
      <button type="submit" class="secondary">Cancel</button>
    </form>
  </div>
  <span class="switch">Not you? <a href="/oauth/authorize/switch?{html.escape(switch_query)}">Sign in with another account</a></span>
</div>"""
    return _page(f"Connect {assistant} · Connexity", body)
