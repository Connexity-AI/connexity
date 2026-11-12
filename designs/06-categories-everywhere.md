# Prompt for Claude Design: one fixed set of categories everywhere

Paste everything below the line into the existing Connexity project in Claude Design. It changes every issues list to use the spec's categories.

---

Use one fixed set of categories across the whole app, in dark and light: the spec and the issues, and as labels on roadmap work. Remove the value-named areas ("Callers are never cut off" and the rest) everywhere. People should learn one set of names and see it on every screen.

## The categories

Always in this order. The first ten group behaviour (and the spec's rules); the next three group technical problems that any agent can have, whatever its spec says.

1. Greeting and identification
2. Information collection
3. Booking
4. Rescheduling and cancelling
5. Pricing and quotes
6. Objection handling
7. Transfers and escalation
8. Compliance and privacy
9. Conversation flow quality
10. Ending the call
11. Responsiveness (latency, slow replies, talking over the caller)
12. Tools and integrations (failed or empty tool calls, backend workflow errors)
13. Speech recognition (names, numbers and addresses misheard)
14. Other

A category with nothing in it is hidden; the order of the rest never changes.

## Issues

Every issues list (the agent profile's Issues tab, and anywhere issues are grouped) groups by the same categories, collapsed to name and count. The issue row shows its category instead of a value area.

## Spec

Unchanged: it already uses these categories. Technical categories (11 to 13) rarely hold spec rules and are usually hidden there.
