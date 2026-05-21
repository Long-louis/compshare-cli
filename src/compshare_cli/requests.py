from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateInstanceOptions:
    zone: str
    region: str
    image_id: str
    gpu_type: str
    gpu: int
    cpu: int
    memory_gib: int
    disk_size_gib: int
    name: str | None = None
    machine_type: str = "G"
    disk_type: str = "CLOUD_SSD"
    minimal_cpu_platform: str = "Auto"
    charge_type: str = "Dynamic"
    quantity: int = 1


def resolve_zone_region(
    zone: str, region: str | None, zones: list[dict[str, Any]]
) -> tuple[str, str]:
    matches = [item for item in zones if item.get("Zone") == zone]
    if not matches:
        raise ValueError(f"Unknown zone: {zone}")
    resolved_region = str(matches[0].get("Region"))
    if region and region != resolved_region:
        raise ValueError(
            f"Zone {zone} does not belong to region {region}; "
            f"expected {resolved_region}"
        )
    return resolved_region, zone


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def build_create_instance_request(options: CreateInstanceOptions) -> dict[str, Any]:
    if not options.region or not options.region.strip():
        raise ValueError("region is required")
    if not options.zone or not options.zone.strip():
        raise ValueError("zone is required")
    _require_positive("gpu", options.gpu)
    _require_positive("cpu", options.cpu)
    _require_positive("memory", options.memory_gib)
    _require_positive("disk_size", options.disk_size_gib)
    _require_positive("quantity", options.quantity)

    request: dict[str, Any] = {
        "Region": options.region,
        "Zone": options.zone,
        "MachineType": options.machine_type,
        "CompShareImageId": options.image_id,
        "GPU": options.gpu,
        "GpuType": options.gpu_type,
        "CPU": options.cpu,
        "Memory": options.memory_gib * 1024,
        "MinimalCpuPlatform": options.minimal_cpu_platform,
        "ChargeType": options.charge_type,
        "Quantity": options.quantity,
        "Disks": [
            {"IsBoot": True, "Size": options.disk_size_gib, "Type": options.disk_type}
        ],
    }
    if options.name:
        request["Name"] = options.name
    return request
