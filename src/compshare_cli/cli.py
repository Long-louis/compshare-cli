from __future__ import annotations

from typing import Annotated
import json
import shlex

import typer

from .config import ConfigStore, credential_source, load_credentials, redact_secret
from .errors import CliError, MISSING_CREDENTIALS_MESSAGE
from .output import agent_envelope, command_suggestion, print_json, print_table, quiet_sdk_logs
from .requests import CreateInstanceOptions, build_create_instance_request, resolve_zone_region
from .sdk import CompShareClient

quiet_sdk_logs()
app = typer.Typer(help="CompShare GPU rental CLI.", no_args_is_help=True)
config_app = typer.Typer(help="Manage local credentials.", no_args_is_help=True)
resource_app = typer.Typer(help="Discover rentable CompShare resources.", no_args_is_help=True)
price_app = typer.Typer(help="Check CompShare prices.", no_args_is_help=True)
instance_app = typer.Typer(help="Manage CompShare instances.", no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(resource_app, name="resource")
app.add_typer(price_app, name="price")
image_app = typer.Typer(help="Manage CompShare custom images.", no_args_is_help=True)
app.add_typer(instance_app, name="instance")
app.add_typer(image_app, name="image")

CONFIG_KEYS = {"public-key": "public_key", "private-key": "private_key"}


@app.callback()
def main() -> None:
    """Manage CompShare GPU resources."""


@config_app.command("set")
def config_set(key: Annotated[str, typer.Argument()], value: Annotated[str, typer.Argument()]) -> None:
    if key not in CONFIG_KEYS:
        raise typer.BadParameter(f"key must be one of: {', '.join(CONFIG_KEYS)}")
    ConfigStore().set_value(CONFIG_KEYS[key], value)
    typer.echo(f"Saved {key}")


@config_app.command("get")
def config_get(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    data = ConfigStore().read()
    safe = {key: redact_secret(value) for key, value in data.items()}
    if json_output:
        print_json(safe)
        return
    for key in ("public_key", "private_key"):
        typer.echo(f"{key}: {safe.get(key, '')}")


@config_app.command("unset")
def config_unset(key: Annotated[str, typer.Argument()]) -> None:
    if key not in CONFIG_KEYS:
        raise typer.BadParameter(f"key must be one of: {', '.join(CONFIG_KEYS)}")
    ConfigStore().unset_value(CONFIG_KEYS[key])
    typer.echo(f"Removed {key}")


@config_app.command("path")
def config_path() -> None:
    typer.echo(str(ConfigStore().path))


def get_client() -> CompShareClient:
    credentials = load_credentials()
    if credentials is None:
        raise CliError(
            MISSING_CREDENTIALS_MESSAGE,
            type_name="MissingCredentials",
            hint="Set COMPSHARE_PUBLIC_KEY/COMPSHARE_PRIVATE_KEY or run compshare config set public-key/private-key."
        )
    return CompShareClient(credentials)


def handle_cli_error(error: CliError, json_output: bool, agent_output: bool = False, command: str = "command") -> None:
    if agent_output:
        first_line = error.message.splitlines()[0] if error.message else ""
        next_actions = [error.hint] if error.hint else []
        commands = []
        if error.type_name == "MissingCredentials":
            commands = [
                command_suggestion("Set public key", "compshare config set public-key YOUR_KEY", "sensitive", True),
                command_suggestion("Set private key", "compshare config set private-key YOUR_KEY", "sensitive", True),
            ]
        envelope = agent_envelope(
            command,
            first_line,
            {"error": error.message, "type": error.type_name},
            "none",
            ok=False,
            warnings=[first_line] if first_line else [],
            next_actions=next_actions,
            commands=commands,
        )
        print_json(envelope)
        raise typer.Exit(1)
    if json_output:
        print_json(error.to_json())
        raise typer.Exit(1)
    typer.echo(error.message, err=True)
    raise typer.Exit(1)


def print_response(response: dict, json_output: bool) -> None:
    if json_output:
        print_json(response)
    else:
        typer.echo(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))


@resource_app.command("zones")
def resource_zones(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        zones = get_client().support_zones()
    except CliError as error:
        handle_cli_error(error, json_output, agent_output, "resource zones")
    normalized = normalize_zones(zones)
    if agent_output:
        commands = [
            command_suggestion("List available zones", "compshare resource zones", "safe", False),
            command_suggestion("Check instance types", f"compshare resource instance-types --zone {normalized[0]['zone'] if normalized else ''} --gpu-type 4090", "safe", False),
        ]
        envelope = agent_envelope("resource_zones", f"Found {len(normalized)} zones", {"zones": normalized}, "none", ok=True, warnings=[], next_actions=[], commands=commands)
        print_json(envelope)
        return
    if json_output:
        print_json({"ZoneInfo": zones})
        return
    print_table(["REGION", "ZONE", "NAME"], [[z.get("Region", ""), z.get("Zone", ""), z.get("Describe", "")] for z in zones])


def make_create_options(
    zone: str,
    region: str | None,
    image_id: str,
    gpu_type: str,
    gpu: int,
    cpu: int,
    memory: int,
    disk_size: int,
    name: str | None,
) -> CreateInstanceOptions:
    client = get_client()
    resolved_region, resolved_zone = resolve_zone_region(zone, region, client.support_zones())
    return CreateInstanceOptions(
        zone=resolved_zone,
        region=resolved_region,
        image_id=image_id,
        gpu_type=gpu_type,
        gpu=gpu,
        cpu=cpu,
        memory_gib=memory,
        disk_size_gib=disk_size,
        name=name,
    )


@instance_app.command("create")
def instance_create(
    zone: Annotated[str, typer.Option("--zone")],
    image_id: Annotated[str, typer.Option("--image-id")],
    gpu_type: Annotated[str, typer.Option("--gpu-type")],
    gpu: Annotated[int, typer.Option("--gpu")],
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory", help="Memory in GiB.")],
    disk_size: Annotated[int, typer.Option("--disk-size", help="Boot disk size in GiB.")],
    region: Annotated[str | None, typer.Option("--region")] = None,
    name: Annotated[str | None, typer.Option("--name")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm live instance creation.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, name)
        payload = build_create_instance_request(options)
        if dry_run:
            if agent_output:
                base_opts = {
                    "zone": options.zone,
                    "image-id": options.image_id,
                    "gpu-type": options.gpu_type,
                    "gpu": options.gpu,
                    "cpu": options.cpu,
                    "memory": options.memory_gib,
                    "disk-size": options.disk_size_gib,
                    "dry-run": True,
                }
                if options.region:
                    base_opts["region"] = options.region
                if options.name:
                    base_opts["name"] = options.name
                create_cmd = create_command_from_payload("instance create", {k: v for k, v in base_opts.items() if k != "dry-run"} | {"yes": True})
                envelope = agent_envelope(
                    "instance_create",
                    "Previewed instance creation. No instance was created.",
                    {"dry_run": True, "request": payload},
                    "none",
                    ok=True,
                    warnings=["Live creation will incur cost."],
                    next_actions=["Ask the user before running the live create command."],
                    commands=[command_suggestion("Create instance", create_cmd, "cost-incurring", True)],
                )
                print_json(envelope)
                return
            print_json(payload) if json_output else typer.echo(payload)
            return
        if not yes:
            message = "instance create requires --yes for live creation"
            if agent_output:
                print_json(agent_envelope(
                    "instance_create",
                    message,
                    {"request": payload},
                    "cost-incurring",
                    ok=False,
                    warnings=[message],
                    next_actions=["Run the dry-run command first, then ask the user for explicit approval before using --yes."],
                ))
            elif json_output:
                print_json({"error": {"type": "ConfirmationRequired", "message": message, "hint": "Add --yes only after explicit user approval."}})
            else:
                typer.echo(message, err=True)
            raise typer.Exit(1)
        response = get_client().invoke("CreateCompShareInstance", payload)
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output, agent_output)
    if agent_output:
        envelope = agent_envelope(
            "instance_create",
            f"Created instance: {', '.join(response.get('UHostIds', []))}",
            {"instance_ids": response.get("UHostIds", [])},
            "cost-incurring",
            ok=True,
            commands=[command_suggestion("Show instance", f"compshare instance show {response.get('UHostIds', [''])[0]} --agent", "safe", False)],
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    typer.echo(f"Created instance: {', '.join(response.get('UHostIds', []))}")


@price_app.command("create")
def price_create(
    zone: Annotated[str, typer.Option("--zone")],
    image_id: Annotated[str, typer.Option("--image-id")],
    gpu_type: Annotated[str, typer.Option("--gpu-type")],
    gpu: Annotated[int, typer.Option("--gpu")],
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory")],
    disk_size: Annotated[int, typer.Option("--disk-size")],
    region: Annotated[str | None, typer.Option("--region")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, None)
        response = get_client().invoke("GetCompShareInstancePrice", build_create_instance_request(options))
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output, agent_output)
    if agent_output:
        base_opts = {
            "zone": options.zone,
            "image-id": options.image_id,
            "gpu-type": options.gpu_type,
            "gpu": options.gpu,
            "cpu": options.cpu,
            "memory": options.memory_gib,
            "disk-size": options.disk_size_gib,
        }
        if options.region:
            base_opts["region"] = options.region
        capacity_cmd = create_command_from_payload("resource capacity", base_opts)
        dry_run_cmd = create_command_from_payload("instance create", {**base_opts, "dry-run": True})
        create_cmd = create_command_from_payload("instance create", base_opts)
        commands = [
            command_suggestion("Check capacity", capacity_cmd, "read-only", False),
            command_suggestion("Dry-run instance creation", dry_run_cmd, "read-only", False),
            command_suggestion("Create instance", create_cmd, "cost-incurring", True),
        ]
        warnings = []
        if response.get("Price", 0) > 100:
            warnings.append("High estimated cost")
        envelope = agent_envelope(
            "price_create",
            f"Estimated price: {response.get('Price', 0)}",
            {"request": {
                "zone": options.zone,
                "region": options.region,
                "image_id": options.image_id,
                "gpu_type": options.gpu_type,
                "gpu": options.gpu,
                "cpu": options.cpu,
                "memory_gib": options.memory_gib,
                "disk_size_gib": options.disk_size_gib,
                "name": options.name,
            }, "price": response},
            "may-incur-cost",
            ok=True,
            warnings=warnings,
            next_actions=["Run capacity check before creating instance"],
            commands=commands,
        )
        print_json(envelope)
        return
    print_response(response, json_output)


@instance_app.command("list")
def instance_list(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("DescribeCompShareInstance", {})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
    if agent_output:
        instances = normalize_instances(response.get("UHostSet", []))
        suggestions = []
        for item in instances[:5]:
            instance_id = item.get("id", "")
            if item.get("state") == "Stopped":
                suggestions.append(command_suggestion(f"Start {instance_id}", f"compshare instance start {instance_id} --agent", "cost-incurring", True))
            elif item.get("state"):
                suggestions.append(command_suggestion(f"Show {instance_id}", f"compshare instance show {instance_id} --agent", "safe", False))
        envelope = agent_envelope(
            "instance_list",
            f"Found {len(instances)} instances.",
            {"instances": instances},
            "read-only",
            ok=True,
            commands=suggestions,
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    rows = [[item.get("UHostId", ""), item.get("Name", ""), item.get("State", "")] for item in response.get("UHostSet", [])]
    print_table(["ID", "NAME", "STATE"], rows)


@instance_app.command("show")
def instance_show(
    instance_id: str,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("DescribeCompShareInstance", {"UHostIds": [instance_id]})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
    if agent_output:
        instances = normalize_instances(response.get("UHostSet", []))
        envelope = agent_envelope(
            "instance_show",
            f"Instance {instance_id} details",
            {"instance": instances[0] if instances else {}},
            "read-only",
            ok=True,
            commands=[command_suggestion("List instances", "compshare instance list --agent", "safe", False)],
        )
        print_json(envelope)
        return
    print_response(response, json_output)


def _resolve_instance_zone(instance_id: str, client) -> tuple[str, str]:
    response = client.invoke("DescribeCompShareInstance", {"UHostIds": [instance_id]})
    instances = response.get("UHostSet", [])
    if not instances:
        raise CliError(f"Instance {instance_id} not found")
    zone = instances[0].get("Zone")
    if not zone:
        raise CliError(f"Instance {instance_id} has no Zone field")
    region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
    return region, resolved_zone


def invoke_instance_action(action: str, instance_id: str, zone: str | None, json_output: bool, agent_output: bool = False, command_name: str = "instance", without_gpu: bool = False) -> None:
    try:
        client = get_client()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        else:
            region, resolved_zone = _resolve_instance_zone(instance_id, client)
        payload: dict = {"Region": region, "Zone": resolved_zone, "UHostId": instance_id}
        if without_gpu:
            payload["WithoutGpu"] = True
        response = client.invoke(action, payload)
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
        return
    if agent_output:
        envelope = agent_envelope(
            f"{command_name}",
            f"Requested {command_name} for instance {instance_id}.",
            {"instance_id": instance_id, "response": response},
            "cost-incurring" if command_name == "start" else "may-incur-cost" if command_name in ["stop", "reboot"] else "destructive" if command_name == "delete" else "safe",
            ok=True,
            commands=[command_suggestion("Show instance", f"compshare instance show {instance_id} --agent", "safe", False)],
        )
        print_json(envelope)
        return
    print_json(response) if json_output else typer.echo("OK")


@instance_app.command("start")
def instance_start(
    instance_id: str,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    without_gpu: Annotated[bool, typer.Option("--without-gpu", help="Start without GPU card (cardless mode).")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    invoke_instance_action("StartCompShareInstance", instance_id, zone, json_output, agent_output, "start", without_gpu)


@instance_app.command("stop")
def instance_stop(
    instance_id: str,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    invoke_instance_action("StopCompShareInstance", instance_id, zone, json_output, agent_output, "stop")


@instance_app.command("reboot")
def instance_reboot(
    instance_id: str,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    invoke_instance_action("RebootCompShareInstance", instance_id, zone, json_output, agent_output, "reboot")


@instance_app.command("delete")
def instance_delete(
    instance_id: str,
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    if not yes:
        typer.echo("instance delete requires --yes")
        raise typer.Exit(1)
    invoke_instance_action("TerminateCompShareInstance", instance_id, zone, json_output, agent_output, "delete")


@image_app.command("create")
def image_create(
    instance_id: Annotated[str, typer.Option("--instance-id", help="Instance ID to create image from.")],
    name: Annotated[str, typer.Option("--name", help="Custom image name.")],
    description: Annotated[str | None, typer.Option("--description", help="Image description.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        client = get_client()
        region, zone = _resolve_instance_zone(instance_id, client)
        payload: dict[str, object] = {"Region": region, "Zone": zone, "UHostId": instance_id, "Name": name}
        if description is not None:
            payload["Description"] = description
        response = client.invoke("CreateCompShareCustomImage", payload)
        image_id = response.get("CompShareImageId", "")
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
    if agent_output:
        commands = [
            command_suggestion("Check image progress", f"compshare image show-progress --image-id {image_id} --agent", "read-only", False),
        ]
        envelope = agent_envelope(
            "image_create",
            f"Image creation started: {image_id}",
            {"image_id": image_id},
            "may-incur-cost",
            ok=True,
            commands=commands,
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    typer.echo(f"Image creation started: {image_id}")


@image_app.command("list")
def image_list(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("DescribeCompShareCustomImages", {})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
    if agent_output:
        images = response.get("ImageSet", [])
        items = [{"id": img.get("CompShareImageId", ""), "name": img.get("Name", ""), "status": img.get("Status", "")} for img in images]
        envelope = agent_envelope(
            "image_list",
            f"Found {len(items)} custom images.",
            {"images": items},
            "read-only",
            ok=True,
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    rows = [[img.get("CompShareImageId", ""), img.get("Name", ""), img.get("Status", ""), str(img.get("Size", 0))] for img in response.get("ImageSet", [])]
    print_table(["ID", "NAME", "STATUS", "SIZE(MB)"], rows)


@image_app.command("show-progress")
def image_show_progress(
    image_id: Annotated[str, typer.Option("--image-id", help="Custom image ID.")],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    try:
        response = get_client().invoke("GetCompShareImageCreateProgress", {"CompShareImageId": image_id})
        process = response.get("Process", 0)
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
    if agent_output:
        envelope = agent_envelope(
            "image_show_progress",
            f"Progress: {process}%",
            {"image_id": image_id, "process": process},
            "read-only",
            ok=True,
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    typer.echo(f"Progress: {process}%")


@image_app.command("delete")
def image_delete(
    image_id: Annotated[str, typer.Option("--image-id", help="Custom image ID.")],
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
) -> None:
    if not yes:
        message = "image delete requires --yes"
        if agent_output:
            print_json(agent_envelope(
                "image_delete",
                message,
                {},
                "may-incur-cost",
                ok=False,
                warnings=[message],
                next_actions=["Add --yes to confirm deletion."],
            ))
        elif json_output:
            print_json({"error": {"type": "ConfirmationRequired", "message": message}})
        else:
            typer.echo(message)
        raise typer.Exit(1)
    try:
        response = get_client().invoke("TerminateCompShareCustomImage", {"CompShareImageId": image_id})
    except CliError as error:
        handle_cli_error(error, json_output, agent_output)
    if agent_output:
        envelope = agent_envelope(
            "image_delete",
            "OK",
            {"image_id": image_id},
            "may-incur-cost",
            ok=True,
        )
        print_json(envelope)
        return
    if json_output:
        print_json(response)
        return
    typer.echo("OK")


@resource_app.command("machine-families")
def resource_machine_families(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        response = get_client().invoke("DescribeCompShareMachineTypeFamilies", {})
    except CliError as e:
        handle_cli_error(e, json_output)
    else:
        print_response(response, json_output)


@resource_app.command("instance-types")
def resource_instance_types(
    zone: Annotated[str, typer.Option("--zone")],
    gpu_type: Annotated[str | None, typer.Option("--gpu-type")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        client = get_client()
        region, resolved_zone = resolve_zone_region(zone, None, client.support_zones())
        payload = {"Region": region, "Zone": resolved_zone}
        if gpu_type:
            payload["MachineTypes"] = [gpu_type]
        response = client.invoke("DescribeAvailableCompShareInstanceTypes", payload)
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    else:
        print_response(response, json_output)


@resource_app.command("images")
def resource_images(
    image_type: Annotated[str, typer.Option("--type")] = "platform",
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    action = {"community": "DescribeCommunityImages", "custom": "DescribeCompShareCustomImages"}.get(image_type, "DescribeCompShareImages")
    try:
        response = get_client().invoke(action, {})
    except CliError as e:
        handle_cli_error(e, json_output)
    else:
        print_response(response, json_output)


@resource_app.command("gpu-inventory")
def resource_gpu_inventory(
    zone: Annotated[str | None, typer.Option("--zone")] = None,
    gpu_type: Annotated[str | None, typer.Option("--gpu-type")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        client = get_client()
        zones_info = client.support_zones()
        if zone:
            region, resolved_zone = resolve_zone_region(zone, None, zones_info)
        else:
            if not zones_info:
                raise ValueError("No zones available from API")
            resolved_zone = zones_info[0]["Zone"]
            region = zones_info[0]["Region"]
        payload: dict[str, object] = {"Region": region, "Zone": resolved_zone}
        if gpu_type:
            payload["MachineTypes"] = [gpu_type]
        response = client.invoke("DescribeCompShareGpuInventory", payload)
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    else:
        if json_output:
            print_json(response)
        else:
            inventory = response.get("InventorySet", [])
            rows = [[item.get("MachineType", ""), item.get("Zone", ""), str(item.get("Count", 0))] for item in inventory]
            print_table(["GPU TYPE", "ZONE", "COUNT"], rows)


@resource_app.command("capacity")
def resource_capacity(
    zone: Annotated[str, typer.Option("--zone")],
    image_id: Annotated[str, typer.Option("--image-id")],
    gpu_type: Annotated[str, typer.Option("--gpu-type")],
    gpu: Annotated[int, typer.Option("--gpu")],
    cpu: Annotated[int, typer.Option("--cpu")],
    memory: Annotated[int, typer.Option("--memory")],
    disk_size: Annotated[int, typer.Option("--disk-size")],
    region: Annotated[str | None, typer.Option("--region")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, None)
        response = get_client().invoke("CheckCompShareResourceCapacity", build_create_instance_request(options))
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    print_response(response, json_output)


def normalize_zones(zones: list[dict]) -> list[dict[str, object]]:
    return [{"region": z.get("Region", ""), "zone": z.get("Zone", ""), "name": z.get("Describe", "")} for z in zones]


def create_command_from_payload(command_name: str, options: dict[str, object]) -> str:
    parts = [command_name]
    for key, value in options.items():
        if value is not None:
            parts.append(f"--{key.replace('_', '-')} {shlex.quote(str(value))}")
    return "compshare " + " ".join(parts)


def normalize_instances(items: list[dict]) -> list[dict[str, object]]:
    return [{"id": item.get("UHostId", ""), "name": item.get("Name", ""), "state": item.get("State", ""), "zone": item.get("Zone", "")} for item in items]


@app.command("doctor")
def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
    agent_output: Annotated[bool, typer.Option("--agent", help="Agent-oriented JSON.")] = False,
    debug: Annotated[bool, typer.Option("--debug", help="Include debug info.")] = False,
) -> None:
    try:
        credentials = load_credentials()
        source = credential_source()
        if credentials is None:
            data = {"credentials": {"available": False, "source": source}}
            commands = [command_suggestion("Configure API keys", "compshare config set-public-key <key> && compshare config set-private-key <key>", "sensitive", True)]
            if agent_output:
                envelope = agent_envelope("doctor", "Missing credentials", data, "none", ok=False, warnings=[], next_actions=["Run `compshare config set` to configure keys"], commands=commands, debug={"source": source} if debug else {})
                print_json(envelope)
            else:
                print_json(data) if json_output else typer.echo("Missing credentials")
            raise typer.Exit(1)

        client = CompShareClient(credentials)
        zones = client.support_zones()
        instances_response = client.invoke("DescribeCompShareInstance", {})
        zones_normalized = normalize_zones(zones)
        instances_normalized = normalize_instances(instances_response.get("UHostSet", []))
        data = {
            "credentials": {"available": True, "source": source},
            "api": {"reachable": True},
            "zones": {"count": len(zones_normalized), "items": zones_normalized},
            "instances": {"count": len(instances_normalized), "items": instances_normalized},
        }
        commands = [
            command_suggestion("List available zones", "compshare resource zones", "safe", False),
            command_suggestion("List your instances", "compshare instance list", "safe", False),
        ]
        if agent_output:
            envelope = agent_envelope("doctor", "System check passed", data, "none", ok=True, warnings=[], next_actions=[], commands=commands, debug={"source": source} if debug else {})
            print_json(envelope)
        elif json_output:
            print_json(data)
        else:
            typer.echo(f"Credentials: {source}")
            typer.echo(f"API reachable: True")
            typer.echo(f"Zones: {len(zones_normalized)}")
            typer.echo(f"Instances: {len(instances_normalized)}")
    except CliError as error:
        handle_cli_error(error, json_output or agent_output)
