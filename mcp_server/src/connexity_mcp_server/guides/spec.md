# Writing an agent's spec

A spec is what an agent is supposed to do, written as plain rules. Connexity uses it to
tell the agent's real behaviour on calls from what was intended, and later to build tests.
You write it from the agent's prompt; Connexity stores it, one version at a time.

## When to write one

- **After the first scan,** for every added agent that has no spec yet.
- **When Connexity says the agent moved to a new version.** Connexity has copied the
  previous spec to the new version; review it (see "A new agent version" below).

Read the agent's spec with `get_spec` before you write, and write it with `write_spec`.
Read the agent's prompt and config from the voice platform, with your own access, never
from Connexity: Connexity is not a go-between for you and the platform. Read the version
the agent's calls run on (`current_agent_version` in `get_spec`), the published one and
not a draft, because Connexity checks every quote against the prompt it recorded for
that version.

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

A rule comes only from the prompt. The only way to change a rule is to change the
prompt; anything else lets the spec drift from the agent. When the prompt leaves
something open, ask the person, never decide it alone. There are two kinds of question.

- **A clarification** says where an existing rule's boundary lies. On calls you see
  the rule could be read two ways: "never offer a time the availability tool did not
  return", and the agent offered a time a second lookup returned. Give the rule's key
  (`rule_key`). The person's answer is one sentence attached to that rule, and every
  check reads the rule with it. The rule itself does not change.
- **A prompt gap** is behaviour no rule covers at all. On 9 of 120 calls the agent
  changed an existing appointment, and the prompt says nothing about changing one. Do
  not write "The agent may change appointments". Raise a question with no `rule_key`,
  naming the behaviour in a few words (`gap_topic`, "changing appointments"). The
  person's answer is what the prompt should say. It is not checked until the prompt
  says it.

## Questions for the person

### When to raise one

- **After writing the first spec:** look at the agent's recent calls (`list_calls`)
  for behaviour the rules do not settle.
- **On a new agent version:** raise what the prompt change leaves unsettled.
- **While working on an issue or a call:** when a rule could be read two ways, or the
  spec does not say whether the behaviour is allowed.

Call `list_clarifications` for the agent first, so you never ask what is already open
or parked.

### How to write one

- **One behaviour, one question, in one plain sentence,** with how often it happened:
  "The agent changed an existing appointment on 9 of 120 calls. Is it allowed to?"
- **Two to four realistic answers** (a to d), each a short label the person picks:
  "Yes, always", "Only when the caller asks", "Never".
- **Every answer carries the sentence it adds** (`sentence`), so the person sees exactly
  what each choice writes:
  - for a clarification, the note on the rule;
  - for a prompt gap, what the prompt would need to say.
- **Name both sides of the boundary in a clarification:** what counts, and what does
  not. "Telling the caller the technician will call about 30 minutes before the visit
  is a notice about a booked visit, not a callback promise; a callback promise is
  saying someone will call back to schedule, confirm or answer something."
  - A note that names only what does not count ("a voicemail greeting is not a call
    screener") also pulls down the real cases next to it. Checks then miss them.
  - Cover the case you saw and nothing next to it.
- **A prompt gap needs a category and `touches`** as a rule would. A clarification
  takes its rule's.
- **The calls where you saw it** (`call_ids`, at most 50). A question from a prompt
  change may have none.

### Replacing a clarification

A person's answer is final. When a clarification no longer fits its rule (the rule's
text changed, or calls show it was too broad), raise a question on the same rule with
`replaces_id` set to the clarification. Quote the earlier answer in the question. Its
answer replaces the earlier clarification, which stays in the history.

### Answering

- **The person answers, never you alone.** Ask them in your chat, one question at a time
  or in one batch, as suits them. Connexity records only the answer they give, never a
  suggestion.
- **Propose answers where you can.** Where the spec, the prompt or the calls support an
  answer, propose it and say why. The person can confirm your proposals as one batch
  and answer the rest. Mark each answer they confirmed from a proposal `proposed`; never
  send one they have not seen.
- **When none of the choices fits,** submit `other` with the person's words as `text`.
  It is kept in their words.
- **Submit with `answer_clarifications`:** a letter, or `park` for what is not important
  now. A parked question can still be answered later, or brought back to the open
  list with `reopen`.
- **When the person leaves a decision to you,** it is still recorded as theirs, with you
  as the assistant that acted. Tell them so.
- **An answer never makes a rule or a spec version.** Tell the person which rules gained
  a clarification, and which prompt gaps now wait for a prompt change.
- **The person can also answer in the app,** on Work. Check `list_clarifications`
  before asking them, so you never ask what they already answered.

### After a prompt gap is answered

Connexity hands you a task: "Propose the prompt change". Read the agent's prompt from
the voice platform and propose to the person the change that says what they decided.
The change is made with their approval, outside Connexity. Once the new version is
live, write its spec with `write_spec`. Name the gap in `closes` on the rule that now
covers it, and the gap closes.

## Critical rules

Every rule is critical or not. In testing, a failed critical rule fails the agent
version: it must not be released. A failed rule that is not critical is a Warning, and
only enough Warnings fail a version. Marking is yours to decide; you do not need to ask
the person, and they can ask you to change it.

- **Critical:**
  - making up facts the business owns, such as prices, availability and policies;
  - money: quoting, charging and refunding;
  - safety, and sending emergencies to the right place;
  - legal and compliance, such as disclosures, consent and personal data;
  - actions with real effects, such as booking, cancelling and transferring.
- **Not critical:** style, phrasing, the length of a turn, and the order of small talk.
  "No more than one question per turn" is a Warning.
- **When unsure, not critical.** A spec where most rules are critical fails every
  version and stops meaning anything.

How to mark:
- **When you write the spec,** give `critical: true` on each rule that is. A kept rule
  you pass without `critical` keeps its mark; a new one is not critical.
- **Afterwards,** call `mark_critical_rules` with the keys
  to mark (`critical`) and to clear (`not_critical`). It makes a new spec version with
  the rules unchanged.
- **Marks carry over** into every later version by key, including a version Connexity
  adopts. A rule that closes a gap left by an earlier answer takes that answer's rule's
  key and mark.

`touches` and critical are separate: `touches` says what a rule protects, critical says
whether its failure stops a release. Most rules that touch money, safety or compliance
are critical; not every critical rule touches one.

## A new agent version

When the agent's prompt changes, Connexity copies the previous spec to the new version,
so the agent is never left without one. Then:

1. Compare the old prompt with the new one.
2. Keep the rules that still hold, with their keys.
3. Rewrite or drop the rules the change affects, and add rules for what it adds.
4. Raise a question for anything the change leaves unsettled.
5. Write the result with `write_spec`, with `critical` on rules that are new and
   critical, and `closes` on rules that now cover an answered prompt gap.
6. Read `check_clarifications` in the answer: clarifications on rules whose text
   changed. Where one no longer fits, raise a question with `replaces_id`.

## Keys

Every rule has a `key`. When you rewrite a spec, pass back the key of each rule from the
prompt you keep. Rules with source `clarification` are earlier answers, carried over by
Connexity until the prompt covers them; leave them out, or name their `prompt_gap_id` in
`closes` on the rule that now covers one. A rule's clarifications stay with its key.
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
