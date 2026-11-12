# Prompt for Claude Design: sign in, sign up, connecting an assistant, new workspace

Paste everything below the line into the existing Connexity project in Claude Design.
These screens come before or around the app shell already designed (`Connexity
Sidebar`), and use the Connexity Design System as it is.

---

Design the screens a person sees before they are inside Connexity, plus creating a
workspace from the profile menu, in dark and light. Use the existing design system:
tokens, Figtree, the button, and the logo. Dark is the default; light is equal.

## Context

Connexity is where a team checks on its fleet of conversational AI agents. The team's AI
assistant (Claude Code, ChatGPT or similar) does the operational work through MCP.
People come to the web app for a quick glance, and to approve what is theirs to decide.
An agency has one **workspace** per client.

A person signs in with **email and password** or with **Google**. Nothing else: no
other providers, no magic links. There is no password reset or email verification yet,
so do not show "Forgot password".

## Rules

- Calm and short. One column, centred, about 360px wide, on surface-0. The logo and
  "Connexity" above the form. No illustrations, no marketing copy, no testimonials.
- Sentence case, plain words, no exclamation marks.
- One primary button per screen (accent). "Continue with Google" is a secondary
  (outlined) button with the Google "G" mark in its own colours. This is the only place
  in the product where a third-party colour appears.
- Errors appear under the field they concern, in the critical colour with its icon.
  Errors that are about the whole form sit above the button.
- Orange is only the logo.

## Screen 1: Sign in

1. The logo and "Connexity".
2. Title: "Sign in".
3. **Continue with Google** (secondary, full width).
4. A divider with "or".
5. Email, Password, and the primary button **Sign in**.
6. Under the form, in muted text: "New to Connexity? **Create an account**".

States to show:

- A wrong email or password: one line above the button, "That email and password
  don't match."
- Google refused or cancelled: one line above the Google button, "Google sign-in didn't
  finish. Try again or use your email."
- A deployment without Google: the Google button and the divider are absent, and the
  rest is unchanged.

## Screen 2: Create an account

1. The logo and "Connexity".
2. Title: "Create an account".
3. **Continue with Google**, the divider, then Name, Work email, Password (with a muted
   hint "At least 8 characters"), and the primary button **Create account**.
4. Under the form: "Already have an account? **Sign in**".

States to show:

- An email already in use: under the email field, "An account already uses this email.
  Sign in instead", linking to Sign in.
- A password that is too short, under the field.

After the account is created, the app opens (the Readiness screen in `Connexity
Onboarding`). Its first workspace is named after the email's domain; the person can
rename it later.

## Screen 3: Connect an assistant

A person reaches this page from their assistant (for example Claude asks them to
approve access). Design it in two states:

- **Not signed in:** the same as Sign in, with a line above the title, "**Claude** wants
  to connect to Connexity", where the name is the assistant's own.
- **Signed in:** title "Connect **Claude** to Connexity". One short paragraph: "Claude
  will be able to see and work in the workspaces you can reach, on your behalf.
  Everything it does is recorded as done by your assistant." Then the person's name and
  email in muted text, the primary button **Allow**, and a secondary **Cancel**. Under
  them, in muted text: "Not you? **Sign in with another account**".

## Screen 4: New workspace (from the profile menu)

In the profile menu's Workspaces part (`Connexity Sidebar`), **New workspace** opens a
small dialog on surface-2:

- Title "New workspace". One field, Name, with a muted hint "Usually the client's name".
- The primary button **Create** and a secondary **Cancel**.
- An empty name disables Create. A name over 255 characters shows an error under the
  field.
- After Create, the dialog closes, the new workspace opens, and its name shows under the
  person's name in the sidebar. The new workspace has nothing in it yet.

Also show the profile menu with **two workspaces** (the open one ticked) and with
**nine** (the search field appears). Keep "Agency settings" out of this menu for now.

## Rejected, do not bring back

- A split screen with a product image or a quote.
- Social sign-in buttons other than Google.
- "Remember me" checkboxes.
- A workspace or company field on the sign-up form.
