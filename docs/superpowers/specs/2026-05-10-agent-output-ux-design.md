# CompShare CLI Agent Output UX Design

## Context

The CompShare CLI is primarily intended for code agents that help prepare short-lived GPU servers before coding or experiments. The agent needs more than raw API data: it needs stable machine-readable facts, cost and destructive-action risk markers, and suggested next commands. Human output still matters, but the most important interface is now the agent-facing command contract.

The current CLI supports human text and `--json`, but `--json` is raw API-shaped output and can be polluted by SDK INFO request/response logs. Some default text output also prints large JSON blocks. This design adds an agent-specific output mode while preserving script-friendly JSON.

## Goals

- Keep default output concise and human-readable.
- Make `--json` parseable JSON on stdout only.
- Add `--agent` as a stable decision envelope for code agents.
- Add `doctor` as the first command a future agent should run.
- Mark generated follow-up commands with risk and confirmation metadata.
- Disable SDK INFO logs by default so structured output is not polluted.
- Keep credentials and secrets redacted in all modes.

## Non-Goals

- Do not replace high-level commands with a generic raw API command in this iteration.
- Do not automate full server provisioning without explicit user confirmation.
- Do not add interactive prompts for agent workflows.
- Do not implement SSH/file synchronization yet; this design only improves CLI output and agent guidance.

## Output Modes

### Default Text

Default output remains for humans. It should prefer short summaries and tables over raw dicts or large JSON blocks.

Examples:

- `resource zones`: table of region, zone, name.
- `instance list`: table of ID, name, state, zone, GPU, CPU, memory.
- `price create`: short price summary.

### `--json`

`--json` is for scripts and shell pipelines. It must emit legal JSON to stdout only.

Rules:

- No SDK logs, progress text, tables, or natural language on stdout.
- Errors use a stable JSON error shape.
- Data can remain close to API responses, but should not include credentials.
- Diagnostics go to stderr or, only when explicitly requested, into a debug field.

`--json` keeps value because it is the best mode for `jq`, CI, shell scripts, and exact field extraction.

### `--agent`

`--agent` is for code agents. It emits a stable JSON envelope with facts and decision support.

Default `--agent` output is concise. `--agent --debug` adds diagnostic details in the envelope `debug` field.

`--agent` differs from `--json` because it includes summaries, warnings, next actions, risk markers, and copyable commands.

## Agent Envelope

All `--agent` commands return this top-level structure:

```json
{
  "ok": true,
  "command": "resource zones",
  "summary": "Found 2 supported zones.",
  "data": {},
  "warnings": [],
  "next_actions": [],
  "commands": [],
  "cost_risk": "read-only",
  "debug": {}
}
```

Field rules:

- `ok`: true when the command completed successfully; false for auth failure, invalid input, network failure, API error, or missing setup.
- `command`: stable command name without secrets.
- `summary`: one-sentence conclusion suitable for an agent to show to a user.
- `data`: normalized CLI-owned fields, not arbitrary raw SDK response blobs.
- `warnings`: non-fatal issues such as resource shortage, missing auth, nonzero cost, or ambiguous state.
- `next_actions`: natural language recommendations.
- `commands`: copyable follow-up commands, each with risk metadata.
- `cost_risk`: one of `none`, `read-only`, `may-incur-cost`, `cost-incurring`, `destructive`, `sensitive`.
- `debug`: empty by default; populated only with `--agent --debug`.

Command-level `risk` may be `safe`, `read-only`, `may-incur-cost`, `cost-incurring`, `destructive`, or `sensitive`. Top-level `cost_risk` uses `none` instead of `safe` when the current command has no cost or mutation risk.

Command suggestion shape:

```json
{
  "label": "Create instance",
  "command": "compshare instance create ... --agent",
  "risk": "cost-incurring",
  "requires_confirmation": true
}
```

Agents may present commands with any risk level, but must not execute `cost-incurring`, `destructive`, or `sensitive` commands without explicit user approval.

## Doctor Command

Add:

```bash
compshare doctor
compshare doctor --json
compshare doctor --agent
compshare doctor --agent --debug
```

`doctor` is the recommended first command for code agents.

Responsibilities:

- Report CLI version.
- Check whether credentials are configured without printing keys.
- Report credential source: `env`, `config`, `mixed`, or `missing`.
- Test API connectivity through `DescribeCompShareSupportZone`.
- Return supported zones.
- Try to list current instances and include a bounded summary of up to 5 instances.
- On missing credentials or API failure, still emit parseable `--json` or `--agent` output.

Missing credentials should produce a nonzero exit code while still printing a valid structured payload.

Example `doctor --agent` success:

```json
{
  "ok": true,
  "command": "doctor",
  "summary": "CompShare CLI is configured and API is reachable. Found 2 zones and 1 instance.",
  "data": {
    "credentials": {"available": true, "source": "config"},
    "api": {"reachable": true},
    "zones": [
      {"region": "cn-wlcb", "zone": "cn-wlcb-01", "name": "华北二A"},
      {"region": "cn-sh2", "zone": "cn-sh2-02", "name": "上海二B"}
    ],
    "instances": {
      "count": 1,
      "items": [{"id": "uhost-xxx", "name": "xxx", "state": "Stopped"}]
    }
  },
  "warnings": [],
  "next_actions": [
    "Use an existing stopped instance if it matches the experiment requirements.",
    "Run price and capacity checks before creating a new instance."
  ],
  "commands": [
    {
      "label": "List current instances",
      "command": "compshare instance list --agent",
      "risk": "safe",
      "requires_confirmation": false
    },
    {
      "label": "Check zones",
      "command": "compshare resource zones --agent",
      "risk": "safe",
      "requires_confirmation": false
    }
  ],
  "cost_risk": "read-only",
  "debug": {}
}
```

## Command Output Strategy

### Resource Commands

- `resource zones --agent`: normalized zones and follow-up commands for images and instances.
- `resource images --agent`: bounded image summaries with ID, name, OS/type when available, and a command to retrieve full JSON.
- `resource machine-families --agent`: normalized machine family summaries.
- `resource instance-types --agent`: zone, region, and available machine type/spec summaries.
- `resource capacity --agent`: requested spec and available specs. If the requested spec appears available, include price, dry-run create, and real create commands. The real create command is `cost-incurring` and requires confirmation.

### Price Command

- `price create --agent`: normalized price summary including charge type, instance price, disk price, and estimated total when available.
- Include follow-up capacity, dry-run create, and real create commands.
- Mark the command risk as `read-only`; mark real create suggestion as `cost-incurring`.

### Instance Commands

- `instance list --agent`: bounded instance list with ID, name, state, zone, GPU type, GPU count, CPU, and memory GiB when available.
- For stopped instances, suggest `start` with `cost-incurring` risk.
- For running instances, suggest `show` and `stop`.
- `instance show --agent`: normalized instance detail, access information if present, and next operational commands.
- `instance create --dry-run --agent`: requested spec and request payload summary; no live create API call.
- `instance create --agent`: created instance IDs and follow-up show/list commands; command risk is `cost-incurring`.
- `instance start --agent`: operation result and follow-up show command; command risk is `cost-incurring`.
- `instance stop --agent`: operation result and follow-up show/list command; command risk is `may-incur-cost` until platform billing behavior is confirmed.
- `instance reboot --agent`: operation result and follow-up show command; command risk is `may-incur-cost`.
- `instance delete --agent`: operation result and follow-up list command; command risk is `destructive`.

## Logs And Debugging

The CLI must configure SDK logging so INFO request/response logs do not appear by default.

Rules:

- Default, `--json`, and `--agent` modes do not print SDK logs to stdout.
- `--debug` may enable diagnostic logging, but diagnostics must go to stderr or `--agent` envelope `debug`.
- Diagnostic payloads must redact credentials and secrets.
- `request_uuid` should be preserved when available because it helps support/debugging.

## Error Shapes

`--json` error shape:

```json
{
  "error": {
    "type": "MissingCredentials",
    "message": "Missing credentials...",
    "hint": "Set COMPSHARE_PUBLIC_KEY/COMPSHARE_PRIVATE_KEY or run compshare config set ..."
  }
}
```

`--agent` error shape:

```json
{
  "ok": false,
  "command": "price create",
  "summary": "Price check failed because credentials are missing.",
  "data": {},
  "warnings": ["No CompShare credentials configured."],
  "next_actions": ["Configure credentials before running live API commands."],
  "commands": [
    {
      "label": "Set public key",
      "command": "compshare config set public-key <PUBLIC_KEY>",
      "risk": "sensitive",
      "requires_confirmation": true
    }
  ],
  "cost_risk": "none",
  "debug": {}
}
```

## Testing

Unit tests:

- JSON helpers emit parseable stdout JSON.
- Agent envelope includes all required fields.
- Command suggestions include `risk` and `requires_confirmation`.
- Config and doctor outputs redact credentials.
- SDK logger is quiet by default.

CLI tests:

- `doctor --agent` with missing credentials emits parseable envelope and nonzero exit.
- `resource zones --agent` returns normalized zone fields.
- `price create --agent` includes normalized price summary and a cost-incurring create command.
- `instance create --dry-run --agent` does not call create API.
- `--json` output is parseable JSON without SDK logs in stdout.
- API errors under `--agent` return `ok=false` envelope.

Smoke tests:

```bash
uv run compshare --help
uv run compshare doctor --agent
uv run compshare resource zones --json
uv run compshare resource zones --agent
uv run compshare price create ... --agent
uv run compshare instance create ... --dry-run --agent
```

## Acceptance Criteria

- `--json` stdout can always be parsed by `json.loads` for supported commands.
- `--agent` stdout can always be parsed by `json.loads` for supported commands.
- `doctor --agent` is usable as the first command for a code agent.
- Generated commands include explicit risk and confirmation metadata.
- Default output avoids large raw dicts for common commands.
- SDK INFO logs do not pollute stdout.
- Credentials are never printed in full by default.
