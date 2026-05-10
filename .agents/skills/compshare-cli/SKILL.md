# compshare-cli Skill

Use this skill when the user needs to interact with CompShare GPU rental platform via CLI, such as checking zones, prices, creating instances, or managing GPU resources.

## First Command

Always start with:

```bash
compshare doctor --agent
```

This verifies CLI configuration and credentials for automated use.

## Safety Rules

- **No cost-incurring operations without explicit approval** – commands that create billable resources (e.g., `instance create`) require `--yes` flag or confirmation.
- **No destructive operations without approval** – termination commands require explicit consent.
- **No sensitive data exposure** – avoid printing API keys in output.

## Common Read Path (Safe)

These commands are read-only and safe to run without approval:
- `compshare doctor --agent`
- `compshare resource zones --agent`
- `compshare instance list --agent`
- `compshare instance show <id> --agent`

## New Instance Workflow

1. **Query price** (read-only):
   `compshare price create --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent`
2. **Preview creation** (dry-run, no billing):
   `compshare instance create --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --dry-run --agent`
3. **Check capacity** (read-only):
   `compshare resource capacity --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent`
4. **Get approval** from user for the displayed price and capacity.
5. **Create live instance** only after explicit approval:
   `compshare instance create --zone cn-sh2-02 --image-id <IMAGE_ID> --gpu-type 4090 --gpu 1 --cpu 16 --memory 64 --disk-size 200 --agent --yes`

Do not bypass the dry-run step or skip user approval when creating instances.
