# Testing: decisions

What was settled about scenarios, test runs and the gate, and what is still open. Only Dmytro's own words make something Decided. It builds on prompt 08 ([`designs/08-testing.md`](../designs/08-testing.md)) and the chain production issues → spec → scenarios → test runs. Where the two disagree, this file wins. It is the reference for the roadmap rows that build testing, starting with scenarios linked to spec rules.

## Words

- **Scenario:** what used to be called a test case, reshaped. It is the stage for a simulated call. Dmytro's word in this conversation; decisions 1 and 2 were said about "test cases" and mean scenarios.
- **Spec rule:** a rule in the agent's spec. A run judges spec rules and gives each a **rule verdict**.
- **Code check:** a code-based check (`CheckKind` `code_based`, "Found by: Code-based" in [`issue-types.md`](./issue-types.md)). "Rule" always means a spec rule (Dmytro, 2026-11-17).
- **Model check:** a check decided by a model: a classifier or an LLM judge (`CheckKind` `classifier`, `judge`). Runs on simulated calls only with code checks for now; model checks there are open question 5.

## Decided

| # | Decision | Dmytro's words | Date |
|---|---|---|---|
| 1 | Scenarios need no approval from people. The assistant writes them. | "No, I dont think users will care about test cases much" (to: do people approve new test cases?) | 2026-11-16 |
| 2 | A person who disagrees with a scenario asks the assistant to change it. | "they ask agent to change it" | 2026-11-16 |
| 3 | No whole conversation to prove a single rule, and no conversations that start from a fixed point partway through. | "We cannot do a end to end voice conversation or even text to check one rule - the pricing model will just not work" · "We cannot do partial conversations cause then we will start always from same point and it will be predefined" | 2026-11-17 |
| 4 | Code checks alone are not enough. Tests are scenarios with several success criteria. | "code checks … are not enough they are very limited" · "it was always based on different scenarios and criterias of success so it works well" | 2026-11-17 |
| 5 | A scenario is a stage. It has no pass or fail of its own. What counts is the total of rule verdicts passed and failed. | "maybe we shouldnt take scenarios as passed or fail, maybe we use them just as stage and count only total of pass and fail checks?" (decisions 6 to 9 build on it) | 2026-11-17 |
| 6 | Every spec rule is Critical or not. A failed critical rule fails the version. A failed non-critical rule is a Warning, and non-critical rules have a threshold. | "if critical rule failed - like agent made up pricing thats a fail. If non critical rule failed - like no two questions per one turn - it's a warning … Then we will have treshold for non critical rules" | 2026-11-17 |
| 7 | The assistant sets whether a rule is Critical without asking. The assistant can do anything a person can; critical actions need the person's approval, as shipping a version that failed its tests does (`decisions.md`, 2026-11-11). Marking a rule Critical is not one of them. | "There is nothing only user can do - its always something that assistant can do either but for critical things we need to make assistant ask for approval. In this case this decision is not critical" | 2026-11-17 |
| 8 | A rule from a Critical issue does not start out Critical, for now. | "for now probably not" | 2026-11-17 |
| 9 | A run judges only the rules its scenario lists. | "listed only" | 2026-11-17 |
| 10 | Code checks also run on simulated calls, and a regression they find is flagged. | "SO what. if its a regression bug that found on sim call and will go to prod and we dont flag it?" (to: code checks on simulated calls, but not as production issues) | 2026-11-17 |
| 11 | Named sets of scenarios, as before. The assistant picks what to run. | "name sets like in [the earlier version] very useful … Doing full run every time is extreme. AI Assistant should be able to pick what to run" | 2026-11-17 |
| 12 | The gate runs every scenario. Replaces "what the gate runs is customizable" (`decisions.md`, 2026-11-11). | "Gate should run all cause it's part of new release and we need to check for regression bugs" | 2026-11-17 |
| 13 | The assistant can also run a one-off pick of scenarios without saving a set. | "Yes" (to: can the assistant also run a one-off pick?) | 2026-11-17 |
| 14 | Failures found by the gate are issues, like production bugs. | "Maybe we treat as production bugs all produciton bugs plus found during gates?" (decision 15 builds on it) | 2026-11-17 |
| 15 | Issue analytics count production only. People still have to know about a gate failure so it is fixed before release. | "We 100% need analytics for production only … it shows maturity of the team. But they need to know if some bug happens during the gate eval so it should be fixed to not get on prod" | 2026-11-17 |

## Proposed (not decided)

**Scenarios**
- A scenario holds:
  - the caller: who they are, their goal, how they behave;
  - what the caller knows, kept apart from the agent's variables (one `user_context` dict used to be both);
  - the tool results to fake;
  - the spec rules it expects to come up, as links, never as free text.
- If a scenario needs to check something no rule covers, the spec is missing a rule. The assistant adds the rule, or raises a clarification, before writing the scenario.

**Runs and rule verdicts**
- One judge call per run judges the transcript against the scenario's listed rules.
- Each rule gets one of three verdicts: Passed, Failed or Didn't come up. "Didn't come up" is not counted. It replaces a pass or fail per case, where every expected outcome had to pass.
- Each scenario in a run repeats N times. A rule that passes in some repeats and fails in others is flaky. A flaky critical rule counts as failed; a flaky non-critical rule counts its failures towards the threshold.
- Code checks run on every simulated call where they apply. Checks that need audio or timing, if such checks exist, are skipped in text runs. A failed code check counts like a failed rule, with the check's own severity (Critical or Warning).

**The version and the gate**
- A version's verdict comes from its latest completed full run (every scenario) and nothing else: Verified when every spec rule was checked and nothing critical was found; Failed on a critical rule (flaky included) or a critical code check; Partially tested when some rule was not checked; Not verified without one. Runs of a set or a pick are on demand and never change it. Non-critical failures never fail a version: the 20% threshold is gone. Coverage is tests written: the latest spec's rules that an active scenario lists. A run counts rules, each once. (Dmytro, 2026-11-19; `plans/2026-11-19-tests-tab-runs-and-verified.md`.) Replaces the 2026-11-17 rules that every run counts and that coverage counts rules judged.
- A full run that judged no rule gives no verdict: the version is Not verified, whatever the code checks found (Dmytro, 2026-11-19: "Verdict only happens when all rules checked").
- A text conversation ends when the agent hangs up or after 40 agent replies, and is judged on what was said; a hang-up or a transfer ends it there. A conversation still going after 10 minutes is stopped as an error. A run makes up to 25 conversations at once, the `SIMULATION_CONCURRENCY` setting (Dmytro, 2026-11-20, replacing 10 of 2026-11-19; `plans/2026-11-19-simulations-finish.md`).
- What limits a run's result is said by the run (Dmytro, 2026-11-20;
  `plans/2026-11-20-trustworthy-test-runs.md`). Every run says whether its version still
  has the content it tested, read on Retell when the run is asked for (`same`, `edited`,
  `unknown`). The judge writes its reason before its verdict. A verdict that rests on a
  default fake (the fake had answered by the last turn the verdict cites) is marked and
  not counted, and a rule with only such verdicts is not checked, so a full run can end
  Partially tested because of it. Every run says tool schemas were not applied, names
  its spec version, and warns when the tested agent version is newer than the one the
  spec's rules were written for; the warning never refuses a run.
- A run says how far it is and what it lost (Dmytro, 2026-11-20;
  `plans/2026-11-20-test-run-progress-and-speed.md`). A call's start is written when it
  starts, so counts tell queued, running and finished apart. The process running a run
  writes a heartbeat every 30 seconds; without one for 2 minutes the run reads stalled,
  and after 15 it is marked failed, keeping the verdicts of calls that finished. A
  starting server no longer fails every running run, only those with no sign of life.
  Calls without verdicts are counted as stopped or judge errors, with no judge retry,
  and an on-demand run that lost calls and found no failure reads `incomplete`. Every
  call says where its time went (agent, caller, judge, Connexity's server), and counts
  the platform's "too many requests" answers.
- For the demo the threshold is one fixed default. Gate settings come in Milestone 7.
- Coverage: a rule is covered when the version's runs checked it at least once, with how many times next to it. This replaces prompt 08's "rules without tests", which counted rules that had no test case.

**Issues from the gate**
- Only gate runs create issues. Set runs and one-off picks are work in progress.
- A gate issue reads "Found in testing, version 15". Its occurrences are simulated calls. Its severity is the rule's or check's: Critical or Warning.
- When the same problem already exists as a production issue, the gate failure is added to that issue instead of opening a second one.
- Testing issues are left out of production analytics: the dashboard, the issue counts and calls per day. They show on the Tests tab and in the issue list filtered to "Found in testing".
- A failed version is a task on Work for the assistant.

**What earlier code is reused**
- Kept: the user simulator, repeats per case, the transcript and costs per run, eval configs as named sets.
- Kept and reviewed: the Retell text runtime. It passes only dynamic variables to Retell's playground and fakes no tools, so faked tool results are new work.
- Reshaped: `expected_outcomes` become links to spec rules; the judge gives one verdict per listed rule instead of a score; code checks are added.
- Deleted (2026-11-20, `plans/2026-11-20-remove-old-eval-stack.md`): the judge's generic metrics, custom metrics, pass thresholds, `evaluation_criteria_override`, `difficulty`, `tags`, the old runner and its REST routes, and the custom endpoint runtime, which is planned again when a self-hosted stack is connected.
- Still to decide: `first_turn` and `first_message`, `status`, `source_call_id`.

## Open

1. The default threshold for non-critical rules and code checks. For the demo: a version fails when more than 20% of the non-critical rules judged failed (`plans/2026-11-17-test-results.md`, accepted 2026-11-17); code checks that only flag are warnings and do not count towards it. Per-agent thresholds are open.
2. Faking tools on platforms other than Retell. Retell text runs fake every tool: the scenario's fake results, then a default fake for any other tool (`plans/2026-11-17-text-runner.md`, accepted 2026-11-17).
3. The Tests tab design adjustment for scenarios, sets, rule totals and failed code checks. The demo shows test results, so it is needed before the demo.
4. When audio simulation comes. It needs a test environment for tools.
5. Whether model checks also run on simulated calls, or only code checks.
6. How a failed spec rule becomes an issue: issues are keyed by an issue type from the library ([`issue-types.md`](./issue-types.md)), and a spec rule is not one.
7. How a gate issue moves through the issue chain (Found → In the spec → Tested → Fixed in a version → Confirmed on real calls, [`designs/10-issues.md`](../designs/10-issues.md)), and whether it is resolved when a later version passes the gate or when it is marked fixed, as other issues are ([`checks-and-incidents.md`](./checks-and-incidents.md)).
