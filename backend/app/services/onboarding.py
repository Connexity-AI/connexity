"""Onboarding: the steps a new workspace goes through, in order, in one list.

Reordering is a one-line change in ``ONBOARDING_STEPS`` (Dmytro, 2026-11-18, while
experimenting with the order). Everything follows it: Readiness's steps
(`crud/readiness.py`), the onboarding rows on Work and the order they block each other
(`services/work.py`), the instructions `get_next_task` and `get_readiness` give the
assistant, and the Onboarding section of the public `/mcp-docs` page
(`GET /api/v1/onboarding/steps`).

How each Readiness step's state is worked out reads the database, so it stays in
`crud/readiness.py`, keyed by the step's key; a test fails when a Readiness step here
has no state there, or the other way round.

Instructions are written once, for both readers:

- a tool or an input as `like_this`;
- a guide as ``[[spec]]``: `connexity://guides/spec` for the assistant, a link on the
  page;
- ``{scan_days}`` and ``{agents}``: filled from the workspace for the assistant
  ("Front desk, Night line"), and with neutral words on the public page ("each agent").
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from app.models.readiness import ReadinessStepKey


class Actor(StrEnum):
    PERSON = "person"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Instruction:
    # Which instruction, when a step has more than one and the state picks.
    key: str
    text: str


@dataclass(frozen=True)
class OnboardingStep:
    key: str
    # The onboarding row's title on Work.
    title: str
    # Its name on Readiness; None for a step Readiness does not show.
    readiness_name: str | None
    who: Actor
    # When it counts as done, in one plain sentence.
    done_when: str
    instructions: tuple[Instruction, ...]

    def instruction(self, key: str) -> Instruction:
        return next(item for item in self.instructions if item.key == key)


SPECS = "specs"
ANSWERS = "answers"

ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        key=ReadinessStepKey.ASSISTANT.value,
        title="Connect your AI assistant",
        readiness_name="Assistant connected",
        who=Actor.PERSON,
        done_when="Done when a member of the workspace has a working assistant "
        "connection.",
        instructions=(
            Instruction(
                "connect",
                "Add Connexity's MCP server to your assistant, then sign in.",
            ),
        ),
    ),
    OnboardingStep(
        key=ReadinessStepKey.VOICE_PLATFORM.value,
        title="Connect your voice platform",
        readiness_name="Voice platform connected",
        who=Actor.ASSISTANT,
        done_when="Done when the workspace has a voice platform connected.",
        instructions=(
            Instruction(
                "connect",
                "Connect the voice platform: ask the person for their Retell API key "
                "(Retell's dashboard, under API Keys), then call "
                "`connect_voice_platform` with it. Do not repeat the key in your reply.",
            ),
        ),
    ),
    OnboardingStep(
        key=ReadinessStepKey.SYNC.value,
        title="Add the agents to watch",
        readiness_name="Agents and calls synced",
        who=Actor.ASSISTANT,
        done_when="Done when every added agent's first scan has finished.",
        instructions=(
            Instruction(
                "add",
                "The voice platform is connected; do not ask for the key again. Use "
                "your own access to Retell to see its agents and their recent calls, "
                "ask the person which belong to this client, then call `add_agents` "
                "with their Retell agent ids.",
            ),
            Instruction(
                "scan",
                "Bring in the added agents' calls from the last {scan_days} days: call "
                "`scan_calls` and keep calling it until it says finished. Tell the "
                "person how far it has got from time to time.",
            ),
        ),
    ),
    OnboardingStep(
        key=ReadinessStepKey.FIRST_SCAN.value,
        title="Scan recent calls",
        readiness_name="First scan done",
        who=Actor.ASSISTANT,
        done_when="Done the first time every added agent's calls from the last "
        "{scan_days} days are in.",
        instructions=(
            Instruction(
                "scan",
                "Keep calling `scan_calls` until it says finished; tell the person how "
                "far it has got.",
            ),
        ),
    ),
    OnboardingStep(
        key=SPECS,
        title="Write the spec for each agent",
        readiness_name=None,
        who=Actor.ASSISTANT,
        done_when="Until the first scan is done; after it, each agent's own spec task "
        "takes its place.",
        instructions=(
            Instruction(
                "write",
                "Write each agent's spec from its prompt: {agents}. Read [[spec]], then "
                "call `get_spec` with include_prompt and `write_spec`.",
            ),
        ),
    ),
    OnboardingStep(
        key=ANSWERS,
        title="Answer the open questions",
        readiness_name=None,
        who=Actor.ASSISTANT,
        done_when="Done when no question is open: each is answered or parked. Then "
        "onboarding is complete and the dashboard is ready.",
        instructions=(
            Instruction(
                "ask",
                "Raise what the specs leave open with `raise_clarifications`. Propose an "
                "answer where the spec, the prompt or the calls support one, and say "
                "why. Then ask the person once, in one message: the proposed answers to "
                "confirm as a batch, and the rest to answer. Call "
                "`answer_clarifications` once with everything they decided, marking "
                "the answers they confirmed from your proposals `proposed`.",
            ),
        ),
    ),
)

STEPS_BY_KEY = {step.key: step for step in ONBOARDING_STEPS}
READINESS_STEPS = tuple(step for step in ONBOARDING_STEPS if step.readiness_name)

_GUIDE = re.compile(r"\[\[([a-z-]+)\]\]")


def _scan_days() -> int:
    # Imported here: `first_scan` imports `crud`, which imports this list.
    from app.services.first_scan import SCAN_DAYS

    return SCAN_DAYS


def for_assistant(text: str, *, agents: str = "each agent") -> str:
    """The text as the assistant reads it: guides as their URIs, values filled in."""
    filled = text.replace("{scan_days}", str(_scan_days())).replace("{agents}", agents)
    return _GUIDE.sub(lambda match: f"connexity://guides/{match.group(1)}", filled)


def for_page(text: str) -> str:
    """The text for the public page: values neutral, guide links kept for the page."""
    return text.replace("{scan_days}", str(_scan_days())).replace(
        "{agents}", "each agent"
    )
