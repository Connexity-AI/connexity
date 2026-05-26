# Agent contracts

Connexity eval agents integrate differently depending on run mode:

| Mode | Contract | When to use |
|------|----------|-------------|
| **Text** | [Text agent contract](./text-agent-contract.md) | HTTP `POST /agent/respond` — OpenAI-style request/response per turn |
| **Voice** | [Voice agent contract](./voice-agent-contract.md) | Phone call + `POST /api/v1/voice-simulations/results` after hangup |

## Reference implementations

| Example | Mode | Path |
|---------|------|------|
| Mock text agent | Text | [examples/mock-text-agent/](../examples/mock-text-agent/) |
| Mock voice agent | Voice | [examples/mock-voice-agent/](../examples/mock-voice-agent/) |

Backend canonical models: `app.models.agent_contract` (text) and `VoiceSimulationResultSubmit` in `app.models.voice_simulation_job` (voice).
