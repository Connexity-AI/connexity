from typing import Literal

from sqlmodel import SQLModel


class ErrorResponse(SQLModel):
    detail: str
    code: str
    status: int


class ConfigPublic(SQLModel):
    project_name: str
    api_version: str
    environment: Literal["local", "staging", "production"]
    docs_url: str
    default_llm_model: str
