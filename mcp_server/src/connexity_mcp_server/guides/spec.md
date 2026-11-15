# Writing an agent's spec

A spec is what an agent is supposed to do, written as plain rules. Connexity uses it to
tell the agent's real behaviour on calls from what was intended, and later to build tests.
You write it from the agent's prompt; Connexity stores it, one version at a time.

## When to write one

- **After the first scan,** for every added agent that has no spec yet.
- **When Connexity says the agent moved to a new version.** Connexity has copied the
  previous spec to the new version; review it (see "A new agent version" below).

Read the agent's spec with `get_spec` before you write, and write it with `write_spec`.
Pass `include_prompt` to `get_spec` for the prompt Connexity recorded for the agent's
current version; write against that prompt, because Connexity checks every quote
against it.

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

Raise these as clarifications (`raise_clarifications`). The person's answer becomes the
rule.

## Questions for the person

### When to raise one

- **After writing the first spec:** look at the agent's recent calls (`list_calls`)
  for behaviour the rules do not settle.
- **On a new agent version:** raise what the prompt change leaves unsettled, and what
  contradicts an earlier answer.
- **While working on an issue or a call:** when the spec does not say whether the
  behaviour is allowed.

Call `list_clarifications` for the agent first, so you never ask what is already open
or parked.

### How to write one

- **One behaviour, one question, in one plain sentence,** with how often it happened:
  "The agent changed an existing appointment on 9 of 120 calls. Is it allowed to?"
- **Two to four realistic answers** (a to d), each a short label the person picks:
  "Yes, always", "Only when the caller asks", "Never".
- **Every answer carries the rule it becomes,** in one plain sentence like any rule:
  "Change an existing appointment only when the caller asks for it". The person sees
  exactly what each choice writes. There is no "doesn't matter": every answer is a rule,
  or the behaviour stays unsettled and comes up again. The person can park a question
  instead.
- **A category and `touches`,** as for a rule: the rule takes them.
- **The calls where you saw it** (`call_ids`, at most 50). A question from a prompt
  change may have none.

### Replacing an answer

A person's answer is final, and Connexity carries its rule into every later version.
`write_spec` refuses it. When a new prompt contradicts an answered rule, raise a
question with `replaces_key` set to that rule's key, and quote both the earlier answer
and the new prompt's words in the question. Its answer replaces the rule.

### Answering

- **The person answers, never you alone.** Prepare the answers, then confirm them in one
  batch: "I can answer 6 confidently; I need your help with the other 1."
- **Submit with `answer_clarifications`:** a letter, or `park` for what is not important
  now. A parked question can still be answered later.
- **When the person leaves a decision to you,** it is still recorded as theirs, with you
  as the assistant that acted. Tell them so.
- **Answers for one agent make one new spec version.** Tell the person which rules were
  added.

## A new agent version

When the agent's prompt changes, Connexity copies the previous spec to the new version,
so the agent is never left without one. Then:

1. Compare the old prompt with the new one.
2. Keep the rules that still hold, with their keys.
3. Rewrite or drop the rules the change affects, and add rules for what it adds.
4. Raise a question for anything the change leaves unsettled, or that contradicts an
   answer the person gave before (`replaces_key`).
5. Write the result with `write_spec`.

## Keys

Every rule has a `key`. When you rewrite a spec, pass back the key of each rule from the
prompt you keep. Rules with source `clarification` are carried over by Connexity; leave
them out.
A kept rule without its key reads as dropped and added again, and its history is lost.
New rules have no key; Connexity gives them one.

## What Connexity does and does not do

- **It does:** store every version as it was written, record who wrote it and for which
  agent version, check that each rule has a category and a source, and tell you when a
  spec needs your review.
- **It does not:** read prompts with a model, decide what a prompt change means, raise
  questions itself (yet), or write or change rules itself.
- **Rules are never edited.** Every change is a new version, so earlier versions stay
  exactly as they were.
