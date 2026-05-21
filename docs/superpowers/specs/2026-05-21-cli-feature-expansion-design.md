# CLI Feature Expansion Design

## Summary

Expand compshare-cli with four new capability areas: image management, instance operations, disk management, and GPU inventory. Follows existing patterns: `--json`/`--agent` output modes, auto-zone resolution for instance-scoped commands, credential masking, and `FakeCompShareClient` testing.

## Architecture

No structural changes to `src/compshare_cli/`. Add new command groups as Typer sub-apps in `cli.py`, following the existing `config_app`/`resource_app`/`price_app`/`instance_app` pattern.

### File boundaries

- **`cli.py`** — all new command definitions (image_app, disk_app, expanded instance_app/resource_app)
- **`requests.py`** — new request builders: `CreateImageOptions`, `DiskOptions`, `ResizeOptions` + corresponding `build_*` functions
- **`sdk.py`** — no changes needed; all APIs go through existing `CompShareClient.invoke()`
- **`output.py`** — no changes; existing `agent_envelope`/`command_suggestion` cover all new commands
- **`errors.py`** — no changes
- **`config.py`** — no changes

## Command Reference

### resource — expanded

| Command | API | Notes |
|---|---|---|
| `resource images --type custom` | `DescribeCompShareCustomImages` | Add `custom` to existing `--type` (platform/community) |
| `resource gpu-inventory` | `DescribeCompShareGpuInventory` | New command; optional `--zone`/`--gpu-type` filters |

### image — new command group

| Command | API | Required params |
|---|---|---|
| `image create` | `CreateCompShareCustomImage` | `--instance-id`, `--name` |
| `image list` | `DescribeCompShareCustomImages` | none |
| `image show-progress` | `GetCompShareImageCreateProgress` | `--image-id` |
| `image delete` | `TerminateCompShareCustomImage` | `--image-id`, `--yes` |

**`image create` optional params:** `--description`, `--framework`, `--framework-version`, `--cuda-version`, `--application`

**Zone resolution:** `image create/delete/show-progress` need Region/Zone. Auto-resolve from `--instance-id` via `DescribeCompShareInstance` (same as lifecycle commands). `image list` is region-scoped, no zone needed.

### instance — expanded

| Command | API | Required params |
|---|---|---|
| `instance rename` | `ModifyCompShareInstanceName` | `--name` |
| `instance reinstall` | `ReinstallCompShareInstance` | `--image-id` |
| `instance resize` | `ResizeCompShareInstance` | `--cpu`, `--memory` |
| `instance set-stop-scheduler` | `UpdateCompShareStopScheduler` | `--at` (ISO timestamp) or `--after-hours` |
| `instance attach-us3` | `AttachUS3` | none (uses instance auto-zone) |

**Constraints:**
- `reinstall` and `resize` require instance in Stopped state; CLI should warn if not
- `set-stop-scheduler` supports two modes: exact time (`--at "2026-05-21T23:00:00"`) or relative hours (`--after-hours 2`)
- `attach-us3` mounts US3 object storage to the instance

All instance commands inherit `--zone` optional auto-resolve pattern.

### disk — new command group

| Command | API | Required params |
|---|---|---|
| `disk attach` | `AttachCompShareDisk` | `--instance-id`, `--size` |
| `disk detach` | `DetachCompShareDisk` | `--disk-id`, `--instance-id` |
| `disk resize` | `ResizeCompShareDisk` | `--disk-id`, `--size` |
| `disk delete` | `DeleteCompShareDisk` | `--disk-id`, `--yes` |

**`disk attach` optional params:** `--type` (default `CLOUD_SSD`), `--name`
**Zone resolution:** disk commands need `--zone` (disks are zone-scoped). Auto-resolve from `--instance-id` when provided.

## Output Design

All commands follow existing output conventions:

- **Human-readable**: table or plain text on stdout
- **`--json`**: pure JSON on stdout, logs to stderr
- **`--agent`**: decision envelope with `ok`, `summary`, `data`, `warnings`, `next_actions`, `commands`, `cost_risk`

**Cost risk mapping:**
- `image create/delete`, `disk attach/detach/resize/delete`, `instance reinstall/resize/attach-us3` → `may-incur-cost`
- `image list`, `image show-progress`, `instance rename`, `instance set-stop-scheduler`, `resource gpu-inventory` → `read-only`

## Error Handling

- Instance not found → `CliError` with `type_name="InstanceNotFound"`
- Image creation failed → `CliError` with `type_name="ImageCreateFailed"`
- Instance not stopped for reinstall/resize → warning in agent output, error in human output
- All errors use existing `handle_cli_error()` path

## Testing

- Extend `FakeCompShareClient` in `test_cli_rental_loop.py` to handle new API actions
- Add `test_cli_image.py`, `test_cli_disk.py` for new command groups
- Test auto-zone resolution for image/disk commands
- Test `--agent` envelope structure for each new command
- Verify `--yes` gate on destructive commands (image delete, disk delete)

## Migration Notes

- No breaking changes to existing commands
- `resource images --type` gains `custom` as third option (backward compatible)
- `instance start/stop/reboot/delete` `--zone` remains optional (existing behavior)
