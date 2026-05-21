# compshare-cli — Agent Instructions

Python CLI for CompShare GPU rental platform. Wraps `ucloud-sdk-python3` against `https://api.compshare.cn`.

## Developer Commands

```bash
uv run pytest              # run all tests (no lint/typecheck in this repo)
uv run compshare --help    # run CLI from source
uv run compshare doctor --agent  # first entrypoint for agent workflows
```

## Package Layout

- `src/compshare/` — thin published package, entrypoint `compshare = "compshare:main"`
- `src/compshare_cli/` — runtime code (cli, config, sdk, output, errors, requests)
- `compshare/__init__.py` re-exports `compshare_cli.main`

**Wheel packaging:** `[tool.uv.build-backend] module-name = ["compshare", "compshare_cli"]` — both packages must be in the wheel.

## Install & Credentials

```bash
uv tool install git+https://github.com/Long-louis/compshare-cli.git
uv tool upgrade compshare
```

Credentials: `COMPSHARE_PUBLIC_KEY` / `COMPSHARE_PRIVATE_KEY` env vars (preferred) or `compshare config set`. Env overrides config. `config get` and `doctor` mask secrets by default.

## CLI Command Groups

| Group | Commands |
|---|---|
| `config` | `set`, `get`, `unset`, `path` |
| `resource` | `zones`, `instance-types --zone`, `images --type platform\|community\|custom`, `machine-families`, `capacity`, `gpu-inventory` |
| `price` | `create` (same spec as `instance create`) |
| `instance` | `create`, `list`, `show`, `start`, `stop`, `reboot`, `delete`, `rename`, `reinstall`, `resize`, `set-stop-scheduler`, `attach-us3` |
| `image` | `create`, `list`, `show-progress`, `delete` |
| `disk` | `attach`, `detach`, `resize`, `delete` |
| top-level | `doctor` |

### Key Behaviors

- **`instance create`**: requires `--dry-run` (no `--yes`) for preview, `--yes` for live creation. Live without `--yes` exits with error.
- **`instance start/stop/reboot`**: `--zone` is optional. When omitted, CLI auto-resolves via `DescribeCompShareInstance` lookup. `start` supports `--without-gpu` for cardless mode.
- **`instance delete`**: always requires `--yes`.
- **`image create/delete`**: `image delete` requires `--yes`. `image create` auto-resolves zone from `--instance-id`.
- **`disk attach/detach/resize/delete`**: require `--yes`. `attach`/`detach` auto-resolve `--zone` from `--instance-id` when omitted.
- **`instance reinstall/resize/attach-us3`**: require `--yes`. `--zone` optional, auto-resolves.
- **Zone resolution**: `region` is derived from `zone` via `DescribeCompShareSupportZone` API — never hardcoded.

## Output Modes

Every command supports `--json` (pure data, stdout-only) and `--agent` (stable decision envelope with `ok`, `summary`, `data`, `warnings`, `next_actions`, `commands`, `cost_risk`). Logs go to stderr.

**Agent workflow:** `doctor --agent` → discover resources → `price create --agent` → `instance create --dry-run --agent` → `instance create --yes --agent`.

## pyproject.toml

May be edited for metadata, dependencies, build config, or tool config. Verify with `uv run pytest` after changes. Lockfiles (`uv.lock`) must not be edited by hand.

## Testing

All tests in `tests/`. Uses `FakeCompShareClient` with monkeypatch pattern. `install_fake_client(monkeypatch)` returns the fake for call inspection.

## Repo

Public GitHub: `https://github.com/Long-louis/compshare-cli` (MIT).
Companion skill: `skills/compshare-cli/SKILL.md`.
