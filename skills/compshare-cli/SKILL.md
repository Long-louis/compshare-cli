---
name: compshare-cli
description: Use when preparing, renting, inspecting, starting, stopping, rebooting, deleting, resizing, or reimaging CompShare GPU cloud instances; managing custom images and data disks; and mounting object storage — with the compshare CLI, especially for code-agent workflows on remote GPU servers.
---

# compshare-cli

## Overview

Use `compshare` to safely inspect CompShare GPU resources, estimate cost, check capacity, preview instance creation, and manage instances. Agents must preserve parseable output and never create billable or destructive changes without explicit user approval.

## Setup Check

If the CLI is not installed, install it from the public repository:

```bash
uv tool install git+https://github.com/Long-louis/compshare-cli.git
```

Then start every workflow with:

```bash
compshare doctor --agent
```

`--agent` returns a stable JSON envelope with `ok`, `summary`, `data`, `warnings`, `next_actions`, `commands`, and `cost_risk`. Prefer `--agent` for agent decisions and `--json` for raw script parsing.

## Credentials

The CLI needs `COMPSHARE_PUBLIC_KEY` and `COMPSHARE_PRIVATE_KEY`, or local config set by:

```bash
compshare config set public-key <PUBLIC_KEY>
compshare config set private-key <PRIVATE_KEY>
```

Never print, reveal, log, or paste the private key. `compshare config get` masks stored secrets by default.

## Safe Discovery

Read-only commands are safe to run without approval:

```bash
compshare doctor --agent
compshare resource zones --agent
compshare resource images --type platform --json
compshare resource images --type community --json
compshare resource instance-types --zone <ZONE> --json
compshare instance list --agent
compshare instance show <INSTANCE_ID> --agent
```

Use `resource images` to discover `--image-id` (platform, community, or custom). Use `resource instance-types` to discover valid GPU/machine types for a zone. Use `resource gpu-inventory --json` to see real-time GPU availability per zone/type (raw JSON only, no `--agent`).

## New Instance Workflow

Follow this order. Do not skip dry-run or approval.

1. Check price:

```bash
compshare price create --zone <ZONE> --image-id <IMAGE_ID> --gpu-type <GPU_TYPE> --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent
```

2. Check capacity:

```bash
compshare resource capacity --zone <ZONE> --image-id <IMAGE_ID> --gpu-type <GPU_TYPE> --gpu 1 --cpu 16 --memory 64 --disk-size 200 --json
```

3. Preview creation without billing:

```bash
compshare instance create --zone <ZONE> --image-id <IMAGE_ID> --gpu-type <GPU_TYPE> --gpu 1 --cpu 16 --memory 64 --disk-size 200 --name <NAME> --dry-run --agent
```

4. Ask the user for explicit approval. Include price, zone, GPU type, CPU, memory, disk, image, and instance name.

5. Create only after approval:

```bash
compshare instance create --zone <ZONE> --image-id <IMAGE_ID> --gpu-type <GPU_TYPE> --gpu 1 --cpu 16 --memory 64 --disk-size 200 --name <NAME> --agent --yes
```

If capacity is unavailable or the API returns insufficient resources, try another zone, GPU type, or smaller resource request; otherwise ask the user whether to retry later.

## Custom Image Workflow

Create a custom image from a running instance:

```bash
compshare image create --instance-id <ID> --name <NAME> --agent
```

Check creation progress:

```bash
compshare image show-progress --image-id <ID> --agent
```

List custom images:

```bash
compshare image list --agent
```

Use a custom image to launch a new instance:

```bash
compshare instance create --image-id <CUSTOM_IMAGE_ID> ... --dry-run --agent
```

`image create` auto-resolves the zone. `image delete` is destructive and requires `--yes`.

## Storage

Two storage options:

**Object storage (US3) mount** — attaches a US3 bucket to the instance:

```bash
compshare instance attach-us3 <INSTANCE_ID> --yes --agent
```

**Cloud data disk** — attaches a new SSD data disk to the instance:

```bash
compshare disk attach --instance-id <ID> --size <GiB> --yes --agent
```

Other disk operations:

```bash
compshare disk detach --disk-id <ID> --instance-id <ID> --yes --agent
compshare disk resize --disk-id <ID> --size <GiB> --yes --agent
compshare disk delete --disk-id <ID> --yes --agent
```

`--zone` is auto-resolved from `--instance-id` for `attach`/`detach`. All disk modifications require `--yes`.

## Instance Management

```bash
compshare instance list --agent
compshare instance show <INSTANCE_ID> --agent
compshare instance start <INSTANCE_ID> --agent
compshare instance stop <INSTANCE_ID> --agent
compshare instance reboot <INSTANCE_ID> --agent
compshare instance rename <INSTANCE_ID> --name <NAME> --agent
compshare instance reinstall <INSTANCE_ID> --image-id <IMAGE_ID> --yes --agent
compshare instance resize <INSTANCE_ID> --cpu <N> --memory <GiB> [--gpu <N>] [--gpu-type <TYPE>] --yes --agent
compshare instance set-stop-scheduler <INSTANCE_ID> --after-hours <N> --agent
compshare instance delete <INSTANCE_ID> --agent --yes
```

`start` may incur cost. `delete`, `reinstall`, and `resize` are destructive and require explicit approval plus `--yes`. `rename`, `reinstall`, `resize`, and `set-stop-scheduler` auto-resolve `--zone`. Ask before running lifecycle operations unless the user already gave a clear instruction.

## Common Mistakes

| Mistake | Correct Action |
| --- | --- |
| Creating directly from a user request | Run price, capacity, and dry-run first |
| Omitting `--agent` in agent workflows | Use `--agent` for decisions and suggestions |
| Guessing image IDs | Discover them with `resource images` |
| Guessing supported GPU types | Discover them with `resource instance-types` |
| Treating dry-run as approval | Ask the user before live create |
| Deleting/reinstalling/resizing without `--yes` | Always pass `--yes` for destructive operations |
| Guessing custom image IDs | List them with `image list --agent` |
| Using `--agent` on `gpu-inventory` | `gpu-inventory` only supports `--json` |
| Printing secrets for debugging | Use masked `config get` or `doctor --agent` |
