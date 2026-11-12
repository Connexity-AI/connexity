# Prompt for Claude Design: fixed spec categories

Paste everything below the line into the existing Connexity project in Claude Design. It changes the Spec tab from prompt 04.

---

Change the Spec tab of the agent profile, in dark and light:

1. **Group rules by fixed categories, not by value areas.** The categories are the same for every agent and never change, so people learn them as patterns. Use this set, always in this order:
   - Greeting and identification
   - Information collection
   - Booking
   - Rescheduling and cancelling
   - Pricing and quotes
   - Objection handling
   - Transfers and escalation
   - Compliance and privacy
   - Conversation flow quality
   - Ending the call
   - Other

   A category with no rules for this agent is not shown, but the order of the rest never changes. Each category is collapsed by default to its name and rule count.
2. **Remove the "Carried over" marker.** Almost every rule carries over to the next version, so marking it is noise. Mark only what changed: "Added" and "Dropped" when comparing versions, and "In conflict" when a new prompt contradicts an earlier answer.
3. Keep everything else on the tab as it is.
