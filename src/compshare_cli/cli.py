from __future__ import annotations

from typing import Annotated
import json

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
app.add_typer(instance_app, name="instance")

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
        raise CliError(MISSING_CREDENTIALS_MESSAGE, type_name="MissingCredentials")
    return CompShareClient(credentials)


def handle_cli_error(error: CliError, json_output: bool) -> None:
    if json_output:
        print_json(error.to_json())
    else:
        typer.echo(error.message, err=True)
    raise typer.Exit(1)


def print_response(response: dict, json_output: bool) -> None:
    if json_output:
        print_json(response)
    else:
        typer.echo(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))


@resource_app.command("zones")
def resource_zones(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        zones = get_client().support_zones()
    except CliError as error:
        handle_cli_error(error, json_output)
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
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, name)
        payload = build_create_instance_request(options)
        if dry_run:
            print_json(payload) if json_output else typer.echo(payload)
            return
        response = get_client().invoke("CreateCompShareInstance", payload)
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
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
) -> None:
    try:
        options = make_create_options(zone, region, image_id, gpu_type, gpu, cpu, memory, disk_size, None)
        response = get_client().invoke("GetCompShareInstancePrice", build_create_instance_request(options))
    except (CliError, ValueError) as error:
        handle_cli_error(error if isinstance(error, CliError) else CliError(str(error)), json_output)
    print_response(response, json_output)


@instance_app.command("list")
def instance_list(json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        response = get_client().invoke("DescribeCompShareInstance", {})
    except CliError as error:
        handle_cli_error(error, json_output)
    if json_output:
        print_json(response)
        return
    rows = [[item.get("UHostId", ""), item.get("Name", ""), item.get("State", "")] for item in response.get("UHostSet", [])]
    print_table(["ID", "NAME", "STATE"], rows)


@instance_app.command("show")
def instance_show(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    try:
        response = get_client().invoke("DescribeCompShareInstance", {"UHostIds": [instance_id]})
    except CliError as error:
        handle_cli_error(error, json_output)
    print_response(response, json_output)


def invoke_instance_action(action: str, instance_id: str, json_output: bool) -> None:
    try:
        response = get_client().invoke(action, {"UHostId": instance_id})
    except CliError as error:
        handle_cli_error(error, json_output)
    print_json(response) if json_output else typer.echo("OK")


@instance_app.command("start")
def instance_start(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    invoke_instance_action("StartCompShareInstance", instance_id, json_output)


@instance_app.command("stop")
def instance_stop(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    invoke_instance_action("StopCompShareInstance", instance_id, json_output)


@instance_app.command("reboot")
def instance_reboot(instance_id: str, json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False) -> None:
    invoke_instance_action("RebootCompShareInstance", instance_id, json_output)


@instance_app.command("delete")
def instance_delete(
    instance_id: str,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deletion.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON.")] = False,
) -> None:
    if not yes:
        typer.echo("instance delete requires --yes")
        raise typer.Exit(1)
    invoke_instance_action("TerminateCompShareInstance", instance_id, json_output)


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
    action = "DescribeCommunityImages" if image_type == "community" else "DescribeCompShareImages"
    try:
        response = get_client().invoke(action, {})
    except CliError as e:
        handle_cli_error(e, json_output)
    else:
        print_response(response, json_output)


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
