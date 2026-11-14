# Writing an agent's spec

A spec is what an agent is supposed to do, written as plain rules. Connexity uses it to
tell the agent's real behaviour on calls from what was intended, and later to build tests.
You write it from the agent's prompt; Connexity stores it, one version at a time.

## When to write one

- **After the first scan,** for every added agent that has no spec yet.
- **When Connexity says the agent moved to a new version.** Connexity has copied the
  previous spec to the new version; review it (see "A new agent version" below).

Read the agent's spec with `get_spec` before you write, and write it with `write_spec`.

## How to write a rule

- **One behaviour, one plain sentence,** in the business's words. "Never book a slot
  outside opening hours." Not "The agent should ensure appropriate scheduling."
- **Only what the prompt settles.** Every rule from the prompt quotes the prompt's words
  it rests on (`quote`). If you cannot point at the words, it is not a rule.
- **Never infer a rule the prompt does not state,** however reasonable it seems. A rule
  you made up looks like the business decided it, and it did not.
- **Put each rule in one of the fixed categories** (`list_categories`), in their order.
  The technical ones (Responsiveness, Tools and integrations, Speech recognition) rarely
  hold rules.
- **Mark rules that protect money, safety or compliance** (`touches`): prices and
  refunds, medical or emergency advice, consent, recording and personal data.
- **No rules about how the agent sounds** (tone, warmth, wording) unless the prompt makes
  one a requirement, such as "always say the clinic's name when you answer".

## What is not a rule: a question for the person

Behaviour you see on calls that the prompt does not settle is a question for the person,
never a rule, and never something you answer alone.

Example: on 9 of 120 calls the agent changed an existing appointment, and the prompt says
nothing about changing one. Do not write "The agent may change appointments" or "The
agent must not change appointments". Ask the person: is it allowed to, only on request,
or never? Their answer becomes the rule.

Raise these as clarifications. Until Connexity has clarifications, list the questions
to the person in your session, with how often each behaviour happens.

## A new agent version

When the agent's prompt changes, Connexity copies the previous spec to the new version,
so the agent is never left without one. Then:

1. Compare the old prompt with the new one.
2. Keep the rules that still hold, with their keys.
3. Rewrite or drop the rules the change affects, and add rules for what it adds.
4. Raise a question for anything the change leaves unsettled, or that contradicts an
   answer the person gave before.
5. Write the result with `write_spec`.

## Keys

Every rule has a `key`. When you rewrite a spec, pass back the key of each rule you keep.
A kept rule without its key reads as dropped and added again, and its history is lost.
New rules have no key; Connexity gives them one.

## What Connexity does and does not do

- **It does:** store every version as it was written, record who wrote it and for which
  agent version, check that each rule has a category and a source, and tell you when a
  spec needs your review.
- **It does not:** read prompts with a model, decide what a prompt change means, or write
  or change rules itself.
- **Rules are never edited.** Every change is a new version, so earlier versions stay
  exactly as they were.
