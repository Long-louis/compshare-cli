# compshare-cli

Python CLI for common [CompShare](https://www.compshare.cn/) GPU rental workflows.

中文文档：[`README.md`](README.md)

## Install

Install directly from a public Git repository:

```bash
uv tool install git+https://github.com/Long-louis/compshare-cli.git
```

For local development:

```bash
git clone https://github.com/Long-louis/compshare-cli.git
cd compshare-cli
uv sync
uv run compshare --help
```

If you cloned a fork or another mirror, replace the Git URL with that repository URL.

## Install The Companion Skill For Code Agents

This repository includes a `compshare-cli` skill for Claude Code, OpenCode, Cursor, and other code agents. It teaches agents to use this CLI with the safe read-only, price, capacity, dry-run, approval, and create/delete flow.

Install it for common agents:

```bash
npx skills add Long-louis/compshare-cli --skill compshare-cli --agent '*' --copy -y
```

Install globally:

```bash
npx skills add Long-louis/compshare-cli --skill compshare-cli --agent '*' --copy -g -y
```

List available skills from this repository:

```bash
npx skills add Long-louis/compshare-cli --list --full-depth
```

## Credentials

The CLI needs your CompShare `Public Key` and `Private Key`.

To obtain them:

1. Sign in to the [CompShare web console](https://www.compshare.cn/).
2. Open the account/API key management page.
3. Copy the platform-provided `Public Key` and `Private Key`.
4. Configure them with environment variables or local CLI config.

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

Environment variables override the local config file. Keep the `Private Key` secret and do not paste it into chat logs, issues, or documentation.

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

Inspect the request first without creating resources:

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
  --dry-run \
  --json
```

Live creation can incur cost and requires `--yes`:

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

## JSON Output

Most commands accept `--json` for automation. JSON output is intended to be parseable stdout without SDK logs or human text.

## Agent Mode

- Start with `compshare doctor --agent` to verify CLI configuration and API reachability.
- Output modes:
  - Default: human-readable tables and summaries.
  - `--json`: machine-readable factual data for scripts.
  - `--agent`: stable JSON envelope for code agents.
  - `--agent --debug`: agent envelope with extra diagnostics.
- Safety rules:
  - `read-only` / `safe`: agent can run without confirmation.
  - `cost-incurring`: requires explicit user approval and usually `--yes`.
  - `destructive`: requires explicit user approval and `--yes`.
  - `sensitive`: may expose or change secrets; requires explicit user approval.
- Typical agent flow:
  1. `compshare doctor --agent`
  2. `compshare resource zones --agent`
  3. `compshare price create ... --agent`
  4. `compshare instance create ... --dry-run --agent`
  5. `compshare instance create ... --agent --yes` after explicit approval.

## References

- [CompShare operation examples](https://www.compshare.cn/docs/gpus/operationexample)
- [CompShare Python SDK examples](https://github.com/ucloud/compshare-developer-examples/tree/main/python-sdk/compshare)

## License

[MIT](LICENSE)
