# compshare-cli

Python CLI for common CompShare GPU rental workflows.

## Install

```bash
uv tool install .
```

## Credentials

Use environment variables:

```bash
export COMPSHARE_PUBLIC_KEY=...
export COMPSHARE_PRIVATE_KEY=...
```

Or store credentials locally:

```bash
compshare config set public-key ...
compshare config set private-key ...
```

Environment variables override the local config file.

## Discover Zones

```bash
compshare resource zones
```

## Check Price

```bash
compshare price create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200
```

## Create Instance

```bash
compshare instance create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --name my-gpu \
  --yes
```

Use `--dry-run --json` to inspect the request body without creating resources. Live creation requires `--yes` because it can incur cost.

## JSON Output

Most commands accept `--json` for automation.

## Agent Mode

- Start with `compshare doctor --agent` to verify CLI is configured for automated use.
- Output modes:
  - Default: human-readable tables and progress
  - `--json`: machine-readable output for scripts and automation
  - `--agent`: optimized for AI agents (minimal decoration, stable JSON where applicable)
  - `--agent --debug`: agent mode with additional debug information
- Safety rules for risk values:
  - `--risk=low`: read-only operations only
  - `--risk=medium`: safe write operations (config, dry-run)
  - `--risk=high`: cost-incurring operations require explicit approval via `--yes` flag or interactive confirmation
- Typical agent flow commands:
  1. `compshare doctor --agent`
  2. `compshare resource zones --agent`
  3. `compshare price create ... --agent`
  4. `compshare instance create ... --dry-run --json --agent` (preview before live create)
  5. `compshare instance create ... --agent --yes` (after approval)
