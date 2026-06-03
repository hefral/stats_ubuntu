from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import time


PROC = Path("/proc")
SYS = Path("/sys")


@dataclass(frozen=True)
class CpuSnapshot:
    idle: int
    total: int


@dataclass(frozen=True)
class NetSnapshot:
    rx_bytes: int
    tx_bytes: int
    timestamp: float


@dataclass(frozen=True)
class Metrics:
    cpu_usage: float | None
    cpu_temp_c: float | None
    gpu_usage: float | None
    gpu_temp_c: float | None
    memory_usage: float | None
    net_down_bps: float | None
    net_up_bps: float | None


@dataclass(frozen=True)
class TemperatureCandidate:
    path: Path
    chip: str
    label: str
    temperature_c: float
    priority: int | None


class MetricsReader:
    def __init__(self) -> None:
        self._prev_cpu = read_cpu_snapshot()
        self._prev_net = read_net_snapshot()

    def read(self) -> Metrics:
        cpu_now = read_cpu_snapshot()
        net_now = read_net_snapshot()

        cpu_usage = calculate_cpu_usage(self._prev_cpu, cpu_now)
        down_bps, up_bps = calculate_net_speed(self._prev_net, net_now)
        gpu_usage, gpu_temp = read_nvidia_gpu()

        self._prev_cpu = cpu_now
        self._prev_net = net_now

        return Metrics(
            cpu_usage=cpu_usage,
            cpu_temp_c=read_cpu_temperature(),
            gpu_usage=gpu_usage,
            gpu_temp_c=gpu_temp,
            memory_usage=read_memory_usage(),
            net_down_bps=down_bps,
            net_up_bps=up_bps,
        )


def read_cpu_snapshot() -> CpuSnapshot | None:
    try:
        first_line = (PROC / "stat").read_text(encoding="utf-8").splitlines()[0]
    except (FileNotFoundError, IndexError, OSError):
        return None

    parts = first_line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return None

    values = [int(v) for v in parts[1:] if v.isdigit()]
    if len(values) < 4:
        return None

    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return CpuSnapshot(idle=idle, total=total)


def calculate_cpu_usage(prev: CpuSnapshot | None, current: CpuSnapshot | None) -> float | None:
    if prev is None or current is None:
        return None

    total_delta = current.total - prev.total
    idle_delta = current.idle - prev.idle
    if total_delta <= 0:
        return None

    return clamp_percent((1 - idle_delta / total_delta) * 100)


def read_cpu_temperature() -> float | None:
    sensors = [(item.priority, item.temperature_c) for item in probe_temperature_candidates() if item.priority is not None]
    if sensors:
        sensors.sort(key=lambda item: item[0])
        return sensors[0][1]

    zones = []
    for zone in (SYS / "class" / "thermal").glob("thermal_zone*"):
        temp = read_millidegree_file(zone / "temp")
        if temp is not None:
            zone_type = read_text(zone / "type").lower()
            priority = 30
            if "x86_pkg_temp" in zone_type:
                priority = 0
            elif "cpu" in zone_type or "package" in zone_type:
                priority = 10
            zones.append((priority, temp))

    if not zones:
        return None

    zones.sort(key=lambda item: item[0])
    return zones[0][1]


def probe_temperature_candidates() -> list[TemperatureCandidate]:
    results: list[TemperatureCandidate] = []
    for hwmon in (SYS / "class" / "hwmon").glob("hwmon*"):
        chip_name = read_text(hwmon / "name").lower()
        for temp_input in hwmon.glob("temp*_input"):
            temp = read_millidegree_file(temp_input)
            if temp is None or temp <= 0:
                continue

            label = read_text(temp_input.with_name(temp_input.name.replace("_input", "_label"))).lower()
            text = f"{chip_name} {label}"
            priority = cpu_temp_priority(text)
            results.append(
                TemperatureCandidate(
                    path=temp_input,
                    chip=chip_name or "unknown",
                    label=label or temp_input.stem,
                    temperature_c=temp,
                    priority=priority,
                )
            )
    return results


def cpu_temp_priority(text: str) -> int | None:
    if "coretemp" in text and "package id 0" in text:
        return 0
    if "coretemp" in text and "package" in text:
        return 1
    if "coretemp" in text:
        return 5
    if "k10temp" in text and ("tctl" in text or "tdie" in text):
        return 10
    if "cpu" in text or "package" in text or "x86_pkg_temp" in text:
        return 20
    if "pch" in text or "acpitz" in text:
        return 50
    return None


def read_millidegree_file(path: Path) -> float | None:
    raw = read_text(path).strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value / 1000 if value > 1000 else value


def read_memory_usage() -> float | None:
    data: dict[str, int] = {}
    try:
        lines = (PROC / "meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines:
        match = re.match(r"^([A-Za-z_()]+):\s+(\d+)", line)
        if match:
            data[match.group(1)] = int(match.group(2))

    total = data.get("MemTotal")
    available = data.get("MemAvailable")
    if not total or available is None:
        return None

    return clamp_percent((total - available) / total * 100)


def read_nvidia_gpu() -> tuple[float | None, float | None]:
    if shutil.which("nvidia-smi") is None:
        return None, None

    command = [
        "nvidia-smi",
        "--query-gpu=utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1.5, check=False)
    except (OSError, subprocess.SubprocessError):
        return None, None

    if result.returncode != 0:
        return None, None

    first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    parts = [p.strip() for p in first_line.split(",")]
    if len(parts) < 2:
        return None, None

    return parse_float(parts[0]), parse_float(parts[1])


def read_net_snapshot() -> NetSnapshot | None:
    try:
        lines = (PROC / "net" / "dev").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    rx_total = 0
    tx_total = 0
    for line in lines[2:]:
        if ":" not in line:
            continue
        iface, values = line.split(":", 1)
        iface = iface.strip()
        if should_ignore_interface(iface):
            continue
        parts = values.split()
        if len(parts) < 16:
            continue
        rx_total += int(parts[0])
        tx_total += int(parts[8])

    return NetSnapshot(rx_bytes=rx_total, tx_bytes=tx_total, timestamp=time.monotonic())


def calculate_net_speed(prev: NetSnapshot | None, current: NetSnapshot | None) -> tuple[float | None, float | None]:
    if prev is None or current is None:
        return None, None
    elapsed = current.timestamp - prev.timestamp
    if elapsed <= 0:
        return None, None
    down = max(0, current.rx_bytes - prev.rx_bytes) / elapsed
    up = max(0, current.tx_bytes - prev.tx_bytes) / elapsed
    return down, up


def should_ignore_interface(name: str) -> bool:
    prefixes = ("lo", "docker", "br-", "veth", "virbr", "vmnet", "tailscale")
    return name.startswith(prefixes)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))
