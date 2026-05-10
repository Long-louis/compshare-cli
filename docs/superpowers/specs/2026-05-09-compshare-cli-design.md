# CompShare CLI Design

## Goal

Build a Python command line tool named `compshare` for the common GPU rental workflow on CompShare. The first version focuses on the rental loop: discover rentable resources, check prices, create instances, inspect instances, and perform basic lifecycle operations.

The CLI should install cleanly with `uv tool install`, use the official `ucloud-sdk-python3` package for API access, and avoid reimplementing CompShare request signing or HTTP transport.

## Scope

First version includes:

- Credential configuration through environment variables and a local config file.
- Resource discovery for zones, machine families, available instance types, images, and capacity checks.
- Create-price queries using the same parameters as instance creation.
- Instance commands for create, list, show, start, stop, reboot, and delete.
- Default human-readable output with `--json` for automation.
- `--dry-run` for create commands to inspect the request body without creating resources.

First version does not include:

- Interactive creation wizard.
- A high-level `rent` command that automatically chooses resources.
- Full coverage of every CompShare API endpoint.
- Team management, custom image publishing, disk lifecycle beyond boot disk creation, or object storage operations.

## Architecture

The package is a thin wrapper around `ucloud-sdk-python3`.

- `compshare` is the console entry point.
- A CLI layer parses commands and options.
- A config layer reads credentials and optional defaults.
- A client layer creates the official UCloud SDK `Client` and exposes CompShare-specific helper methods.
- A request-building layer converts CLI-friendly values into SDK request dictionaries.
- An output layer renders default tables/text or JSON.

The SDK client uses `base_url=https://api.compshare.cn` by default. The CompShare region is not hardcoded for instance operations. Commands resolve or accept the region based on the selected zone.

## Credentials And Config

Credentials can come from both environment variables and a local user config file. Environment variables take precedence.

Supported environment variables:

- `COMPSHARE_PUBLIC_KEY`
- `COMPSHARE_PRIVATE_KEY`

Config commands:

```bash
compshare config set public-key <value>
compshare config set private-key <value>
compshare config get
compshare config unset public-key
compshare config path
```

If credentials are missing, commands that require API access fail with a direct remediation message explaining both setup methods.

## Commands

### Resource Commands

```bash
compshare resource zones
compshare resource instance-types --zone cn-sh2-02 --gpu-type 4090
compshare resource machine-families
compshare resource images --type platform
compshare resource images --type community
compshare resource capacity --zone cn-sh2-02 --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --image-id compshareImage-xxx --disk-size 200
```

`resource zones` calls `DescribeCompShareSupportZone` and displays both API IDs and human names. The known documented shape is:

```json
[
  {"Region": "cn-wlcb", "Zone": "cn-wlcb-01", "Describe": "华北二A"},
  {"Region": "cn-sh2", "Zone": "cn-sh2-02", "Describe": "上海二"}
]
```

### Price Commands

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

Price parameters should mirror create parameters so users can check a price and then create with the same option set.

### Instance Commands

```bash
compshare instance create \
  --zone cn-sh2-02 \
  --image-id compshareImage-xxx \
  --gpu-type 4090 \
  --gpu 1 \
  --cpu 16 \
  --memory 64 \
  --disk-size 200 \
  --name my-gpu

compshare instance list
compshare instance show <instance-id>
compshare instance start <instance-id>
compshare instance stop <instance-id>
compshare instance reboot <instance-id>
compshare instance delete <instance-id>
```

The create command uses explicit CLI parameters rather than an interactive wizard. This keeps the first version scriptable and predictable.

## Region And Zone Handling

CompShare documentation examples use `cn-wlcb` and `cn-wlcb-01`, but the supported-zone API returns multiple choices. The CLI must not hardcode one region for creation.

The recommended create flow is:

1. User passes `--zone`.
2. CLI calls `DescribeCompShareSupportZone`.
3. CLI finds the matching zone and derives its `Region`.
4. CLI sends both `Region` and `Zone` in create, price, and capacity requests.

The CLI may expose `--region` as an advanced override. If both `--zone` and `--region` are supplied, the CLI validates that the pair exists in the supported-zone list when possible.

## Parameter Mapping

CLI parameters use human-friendly units and names.

- `--memory 64` means 64 GiB and maps to `Memory=65536`.
- `--disk-size 200` means 200 GiB and maps to a boot disk with `Size=200`.
- `--disk-type` defaults to `CLOUD_SSD`.
- `--machine-type` defaults to `G`.
- `--charge-type` defaults to `Dynamic` for first-version examples unless the user passes another supported charge type.
- `--quantity` defaults to `1`.
- `--base-url` is a hidden or advanced global option defaulting to `https://api.compshare.cn`.

Create request shape:

```json
{
  "Region": "cn-sh2",
  "Zone": "cn-sh2-02",
  "MachineType": "G",
  "CompShareImageId": "compshareImage-xxx",
  "GPU": 1,
  "GpuType": "4090",
  "CPU": 16,
  "Memory": 65536,
  "ChargeType": "Dynamic",
  "Quantity": 1,
  "Name": "my-gpu",
  "Disks": [
    {
      "IsBoot": true,
      "Size": 200,
      "Type": "CLOUD_SSD"
    }
  ]
}
```

`--dry-run` prints this request body and exits before calling the create API.

## Output

Default output is optimized for terminal use.

- Lists render as compact tables.
- Mutating commands render concise success messages with returned IDs.
- Errors render concise messages with suggested next commands.

Every query and mutation command supports `--json`. JSON mode emits structured data suitable for scripts. On API success, JSON mode preserves useful SDK response fields. On failure, JSON mode emits a structured error object.

## Error Handling

Common errors should be explicit and actionable.

Missing credentials:

```text
Missing credentials. Set COMPSHARE_PUBLIC_KEY/COMPSHARE_PRIVATE_KEY or run:
  compshare config set public-key ...
  compshare config set private-key ...
```

Unknown zone:

```text
Unknown zone: cn-foo-01
Run `compshare resource zones` to list supported zones.
```

Invalid or unavailable spec:

```text
Invalid instance spec: CPU/Memory/GPU combination may not be available.
Run `compshare resource instance-types --zone cn-sh2-02 --gpu-type 4090`.
```

SDK exceptions are converted into concise CLI errors. If an API response includes `RetCode` or `Message`, those values are preserved in JSON mode and summarized in text mode.

## Testing Strategy

Most tests should not require a real CompShare account.

- Config precedence: environment variables override config file values.
- Parameter conversion: `--memory 64` maps to `Memory=65536`.
- Zone resolution: `cn-sh2-02` resolves to `cn-sh2` from mocked zone data.
- Create request construction maps all user options to the expected SDK payload.
- `--dry-run` does not call the create API.
- Default table output and `--json` output are both covered.
- SDK exceptions and non-zero API return codes render useful errors.

Integration tests with real credentials can be optional and disabled by default. They should only run when explicit environment variables are present.

## First-Version Decisions

- `--charge-type` defaults to `Dynamic`, matching the rental-loop use case and the documented Python create example.
- The local config file stores credentials only. Defaults such as preferred zone can be added later after real usage shows they are useful.
- `instance delete` requires `--yes` unless an interactive terminal confirmation is implemented. `instance stop` does not require confirmation because it is reversible.
