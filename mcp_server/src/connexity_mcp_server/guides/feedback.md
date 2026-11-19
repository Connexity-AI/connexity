# Reporting a problem in Connexity

Connexity's team reads every report. `send_feedback` is how you tell them that
Connexity itself let you down, so they can fix it.

## When to report

- **A Connexity tool fails:** an error that says the problem is in Connexity, a timeout,
  or the same failure after one retry.
- **Two answers contradict each other:** for example a count on one tool that another
  tool's list does not match.
- **Connexity cannot do what the work needs:** a tool, an input or an answer you needed
  and could not find. That is a feature request.

Report without asking the person first, once per problem, after one retry. Then tell
the person in one sentence that you reported it, and carry on, around the problem if
you can.

## When not to

- **A problem in the person's own agent** (a wrong answer, a failed booking) is an
  issue Connexity found, not feedback. Work it through `list_issues`.
- **A refusal that tells you what to change** (a missing input, an unknown id) is not a
  bug: fix your request and call again.

## A good report

- **`kind`:** `bug` or `feature_request`.
- **`title`:** one line, what is wrong or missing.
- **`what_happened`** (a bug): what you did, which tool with which inputs, what you
  expected and what came back.
- **`wanted`** (a request): what the work needed and could not do.
- **`tool`**, **`error`** (the answer's text, as it came) and **`ids`** (the call,
  issue, run, agent or task ids involved).
- **`session`:** this session's name, as on `get_next_task`.

## What never goes in a report

- **Caller data:** no transcripts, phone numbers or names. Describe what happened and
  give the call's id instead.
- **Secrets:** no keys, tokens or passwords.

A workspace sends at most 20 reports a day.
