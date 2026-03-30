#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import sys


def _sync_api_keys_from_settings_to_environ() -> None:
    """LiteLLM reads provider keys from the process environment."""
    from app.core.config import settings

    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    if settings.ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY


async def _run(*, model: str) -> int:
    from app.services.llm import LLMCallConfig, LLMMessage, call_llm

    resp = await call_llm(
        [LLMMessage(role="user", content="Reply with exactly the word: pong")],
        LLMCallConfig(model=model, max_tokens=32, temperature=0),
    )
    print(resp.model_dump_json(indent=2))
    print("\n--- LLM call tracking ---")
    print(f"  latency_ms:        {resp.latency_ms}")
    print(f"  usage:             {json.dumps(resp.usage)}")
    if resp.response_cost_usd is not None:
        print(f"  response_cost_usd: {resp.response_cost_usd:.6f}")
    else:
        print(
            "  response_cost_usd: (none — LiteLLM may not set _hidden_params.response_cost)"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Single real OpenAI call via call_llm")
    parser.add_argument(
        "--model",
        default=os.environ.get("LLM_SMOKE_MODEL", "gpt-4.1-nano"),
        help="LiteLLM model id (default: gpt-4.1-nano or LLM_SMOKE_MODEL)",
    )
    args = parser.parse_args()

    _sync_api_keys_from_settings_to_environ()
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is missing. Set it in the repo root .env or the environment.",
            file=sys.stderr,
        )
        return 1

    return asyncio.run(_run(model=args.model))


if __name__ == "__main__":
    raise SystemExit(main())
