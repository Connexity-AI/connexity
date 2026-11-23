# 17. Password reset

Pasted into Claude Design on 2026-11-23, on top of
[`13-sign-in-and-workspaces.md`](./13-sign-in-and-workspaces.md), whose "do not show
Forgot password" it replaces. The result is `screens/Connexity Password Reset.dc.html`
(every screen and state), the new screens in `screens/Connexity Sign in.dc.html` and the
`reset` and `google` variants of `screens/Connexity Email.dc.html`. How it works:
[`docs-internal/password-reset.md`](../docs-internal/password-reset.md).

```txt
Add password reset to the Connexity sign-in screens (Connexity Sign in), in dark and light. Use the existing design system and the same layout as Sign in: one centred column about 360px wide on surface-0, the logo and "Connexity" above the form, no illustrations or marketing copy. Sentence case, plain words, no exclamation marks. One primary button per screen. Orange is only the logo. Errors appear under the field they concern, in the critical colour with its icon.

This replaces the earlier rule "do not show Forgot password".

## 1. Sign in: one new link
On the existing Sign in screen, add a small muted link "Forgot password?" on the Password field's label row, aligned right. Nothing else on the screen changes. On a deployment that cannot send email, the link is absent.

## 2. Forgot password
- Title: "Reset your password"
- One muted line: "Enter your email and we'll send you a link."
- Field: Email
- Primary button: "Send reset link"
- Under the form, muted: "Back to **Sign in**"

States: an invalid email under the field; the button while sending.

## 3. Check your email
Same screen, after sending. It must read the same whether or not the email has an account.
- Title: "Check your email"
- Line: "If an account uses **alex@example.com**, a reset link is on its way. The link works once and expires in 1 hour."
- Secondary button: "Send again", disabled with a short muted countdown after each send ("Send again in 45 s")
- Muted: "Back to **Sign in**"

State: too many requests, one line above the button: "Too many attempts. Try again later."

## 4. Set a new password
Opened from the link in the email.
- Title: "Set a new password"
- Muted line: the account's email
- Field: New password, with a show/hide icon and the muted hint "At least 8 characters"
- Primary button: "Save password"

States: password too short, under the field; the button while saving.

## 5. The link doesn't work
Same layout, when the link is expired or already used.
- Title: "This link no longer works"
- Line: "Reset links work once and expire after 1 hour."
- Primary button: "Send a new link"
- Muted: "Back to **Sign in**"

## 6. Password changed
- Title: "Password changed"
- Line: "You're signed out on your other devices. Your connected AI assistants keep working."
- Primary button: "Continue to Connexity"

## 7. The email
Design the reset email: plain and light, works in dark and light mail clients. The logo and "Connexity", then:
- Subject: "Reset your Connexity password"
- "Someone asked to reset the password for this account."
- One button: "Reset password"
- The plain link under it, for clients that block buttons
- Muted: "This link works once and expires in 1 hour. If this wasn't you, ignore this email and your password stays the same."

A second version for an account that signs in only with Google, which has no password to reset:
- Subject: "Signing in to Connexity"
- "This account signs in with Google, so there's no password to reset."
- One button: "Sign in to Connexity"

## Show
Screens 1 to 6 in dark at desktop width, screen 3 and screen 4 in light, screen 4 at phone width, and both emails.

## Avoid
- Security questions, codes, magic links or a password strength meter.
- Any wording that reveals whether an email has an account.
- Illustrations, success animations or extra links.
- Real names or addresses: use Alex and alex@example.com.
```
