# Example traces

Invented calls that are valid against [`../trace-schema.md`](../trace-schema.md). The
test suite loads every `.json` file in this folder, so they are guaranteed to stay
valid. No real call data lives here.

| File | Shows | Capabilities it has |
|---|---|---|
| `hosted-platform-full.json` | A hosted platform that reports everything: timings, tool calls with results, inputs, component versions, a recording, post-call outputs. | all seven |
| `hosted-platform-partial.json` | A hosted platform that reports less: start times but few end times, one tool call with no logged result, no versions, no recording. | `tool_calls`, `timing`, `inputs`, `outputs` |
| `self-hosted-text-only.json` | The minimum: a self-hosted agent that supplies only who said what. | none |
