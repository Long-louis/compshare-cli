import pytest

from compshare_cli.requests import CreateInstanceOptions, build_create_instance_request, resolve_zone_region


ZONES = [
    {"Region": "cn-wlcb", "Zone": "cn-wlcb-01", "Describe": "华北二A"},
    {"Region": "cn-sh2", "Zone": "cn-sh2-02", "Describe": "上海二"},
]


def test_resolve_zone_region_from_zone():
    assert resolve_zone_region("cn-sh2-02", None, ZONES) == ("cn-sh2", "cn-sh2-02")


def test_resolve_zone_region_rejects_unknown_zone():
    with pytest.raises(ValueError, match="Unknown zone"):
        resolve_zone_region("cn-foo-01", None, ZONES)


def test_resolve_zone_region_rejects_mismatched_region():
    with pytest.raises(ValueError, match="does not belong"):
        resolve_zone_region("cn-sh2-02", "cn-wlcb", ZONES)


def test_build_create_instance_request_converts_memory_and_disk():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
        name="my-gpu",
    )

    request = build_create_instance_request(options)

    assert request["Region"] == "cn-sh2"
    assert request["Zone"] == "cn-sh2-02"
    assert request["Memory"] == 65536
    assert request["MinimalCpuPlatform"] == "Auto"
    assert request["ChargeType"] == "Dynamic"
    assert request["Disks"] == [{"IsBoot": True, "Size": 200, "Type": "CLOUD_SSD"}]


def test_build_create_instance_request_rejects_empty_region():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
    )
    with pytest.raises(ValueError, match="region is required"):
        build_create_instance_request(options)


def test_build_create_instance_request_rejects_empty_zone():
    options = CreateInstanceOptions(
        zone="",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
    )
    with pytest.raises(ValueError, match="zone is required"):
        build_create_instance_request(options)


def test_build_create_instance_request_omits_name_when_none():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
        name=None,
    )
    request = build_create_instance_request(options)
    assert "Name" not in request


def test_build_create_instance_request_defaults():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
    )
    request = build_create_instance_request(options)
    assert request["MachineType"] == "G"
    assert request["ChargeType"] == "Dynamic"
    assert request["Disks"][0]["Type"] == "CLOUD_SSD"


def test_build_create_instance_request_rejects_non_positive_memory():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=0,
        disk_size_gib=200,
    )
    with pytest.raises(ValueError, match="memory must be a positive integer"):
        build_create_instance_request(options)


def test_build_create_instance_request_rejects_gpu_zero():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=0,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
    )
    with pytest.raises(ValueError, match="gpu must be a positive integer"):
        build_create_instance_request(options)


def test_build_create_instance_request_rejects_gpu_negative():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=-1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
    )
    with pytest.raises(ValueError, match="gpu must be a positive integer"):
        build_create_instance_request(options)


def test_build_create_instance_request_rejects_cpu_zero():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=0,
        memory_gib=64,
        disk_size_gib=200,
    )
    with pytest.raises(ValueError, match="cpu must be a positive integer"):
        build_create_instance_request(options)


def test_build_create_instance_request_rejects_disk_size_zero():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=0,
    )
    with pytest.raises(ValueError, match="disk_size must be a positive integer"):
        build_create_instance_request(options)


def test_build_create_instance_request_rejects_quantity_zero():
    options = CreateInstanceOptions(
        zone="cn-sh2-02",
        region="cn-sh2",
        image_id="compshareImage-xxx",
        gpu_type="4090",
        gpu=1,
        cpu=16,
        memory_gib=64,
        disk_size_gib=200,
        quantity=0,
    )
    with pytest.raises(ValueError, match="quantity must be a positive integer"):
        build_create_instance_request(options)
