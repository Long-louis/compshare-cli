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
  --name my-gpu
```

Use `--dry-run --json` to inspect the request body without creating resources.

## JSON Output

Most commands accept `--json` for automation.
