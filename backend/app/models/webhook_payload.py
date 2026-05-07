from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel


class WebhookToolCallParameter(SQLModel):
    name: str
    type: str | None = None
    required: bool = False
    description: str | None = None


class WebhookToolCall(SQLModel):
    name: str | None = None
    description: str | None = None
    method: str | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    parameters: list[WebhookToolCallParameter] = Field(default_factory=list)


class WebhookLlm(SQLModel):
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None


class WebhookAgent(SQLModel):
    id: str
    name: str
    version: int
    version_name: str | None = None
    version_description: str | None = None
    prompt: str
    llm: WebhookLlm
    tool_calls: list[WebhookToolCall] = Field(default_factory=list)


class WebhookEval(SQLModel):
    config_id: str | None = None
    config_name: str | None = None
    run_at: datetime | None = None
    passed: bool | None = None
    metrics_score: float | None = None
    metrics_pass_threshold: float | None = None
    cases_passed: int | None = None
    cases_total: int | None = None
    cases_pass_threshold: float | None = None
    results_link: str | None = None


class WebhookDeployPayload(SQLModel):
    event: str
    agent: WebhookAgent
    environment: str
    deployed_at: datetime
    deployed_by: str | None = None
    eval: WebhookEval
