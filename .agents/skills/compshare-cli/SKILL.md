# compshare-cli Skill

Use this skill when the user needs to interact with CompShare GPU rental platform via CLI, such as checking zones, prices, creating instances, or managing GPU resources.

## First Command

Always start with:
This verifies CLI configuration and credentials for automated use.

## Safety Rules

- **No cost-incurring operations without explicit approval** – commands that create billable resources (e.g., `instance create`) require `--yes` flag or confirmation.
- **No destructive operations without approval** – termination commands require explicit consent.
- **No sensitive data exposure** – avoid printing API keys in output.

## Common Read Path (Safe)

These commands are read-only and safe to run without approval:
- `compshare resource zones --agent`
- `compshare price create ... --agent` (dry-run pricing)
- `compshare instance list --agent`
- `compshare instance get <id> --agent`

## New Instance Workflow

1. **Query price** (read-only):
2. **Preview creation** (dry-run, no billing):
3. **Get approval** from user for the displayed price and capacity.
4. **Create live instance** only after explicit approval:

Do not bypass the dry-run step or skip user approval when creating instances.