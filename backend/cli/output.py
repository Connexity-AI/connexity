"""Format CLI command output as JSON or plain tables."""

import json
from typing import Any

import click


def emit(data: Any, *, output_format: str) -> None:
    """Write payload to stdout in the requested format."""
    if output_format == "json":
        click.echo(json.dumps(data, indent=2, default=str))
        return
    if output_format == "table":
        click.echo(_format_table_auto(data))
        return
    raise ValueError(f"Unknown output format: {output_format}")


def progress(message: str) -> None:
    click.echo(message, err=True)


def _format_table_auto(data: Any) -> str:
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        if not data["data"]:
            return f"(empty — count={data.get('count', 0)})"
        first = data["data"][0]
        if isinstance(first, dict):
            return format_dict_rows(data["data"], title=f"count={data.get('count')}")
    if isinstance(data, dict):
        return _format_key_value(data)
    if isinstance(data, list):
        return format_dict_rows(data)
    return str(data)


def _format_key_value(row: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in sorted(row.keys()):
        val = row[key]
        if isinstance(val, dict | list):
            val = json.dumps(val, default=str)
        lines.append(f"  {key}: {val}")
    return "\n".join(lines)


def format_dict_rows(rows: list[dict[str, Any]], title: str | None = None) -> str:
    if not rows:
        return "(no rows)"
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    widths = {k: len(str(k)) for k in keys}
    for r in rows:
        for k in keys:
            cell = (
                json.dumps(r.get(k), default=str)
                if isinstance(r.get(k), dict | list)
                else str(r.get(k, ""))
            )
            widths[k] = max(widths[k], min(len(cell), 80))
    parts: list[str] = []
    if title:
        parts.append(title)
    header = "  ".join(str(k).ljust(widths[k]) for k in keys)
    parts.append(header)
    parts.append("  ".join("-" * widths[k] for k in keys))
    for r in rows:
        line_parts: list[str] = []
        for k in keys:
            v = r.get(k, "")
            if isinstance(v, dict | list):
                cell = json.dumps(v, default=str)
            else:
                cell = str(v)
            if len(cell) > 80:
                cell = cell[:77] + "..."
            line_parts.append(cell.ljust(widths[k]))
        parts.append("  ".join(line_parts))
    return "\n".join(parts)


def format_run_detail(run: dict[str, Any]) -> str:
    lines = [
        f"Run {run.get('id')}",
        f"  name:              {run.get('name')}",
        f"  status:            {run.get('status')}",
        f"  agent_id:          {run.get('agent_id')}",
        f"  agent_mode:        {run.get('agent_mode', 'endpoint')}",
        f"  eval_config_id:    {run.get('eval_config_id')}",
        f"  eval_config_ver:   {run.get('eval_config_version')}",
        f"  started_at:        {run.get('started_at')}",
        f"  completed_at:      {run.get('completed_at')}",
    ]
    if run.get("agent_model"):
        lines.append(f"  agent_model:       {run.get('agent_model')}")
    if run.get("agent_provider"):
        lines.append(f"  agent_provider:    {run.get('agent_provider')}")
    metrics = run.get("aggregate_metrics")
    if metrics:
        lines.append("  aggregate_metrics:")
        lines.append(json.dumps(metrics, indent=4, default=str))
    return "\n".join(lines)
