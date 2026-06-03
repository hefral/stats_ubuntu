from __future__ import annotations

from .metrics import Metrics


def percent(value: float | None) -> str:
    if value is None:
        return "--%"
    return f"{value:.0f}%"


def temp(value: float | None) -> str:
    if value is None:
        return "--C"
    return f"{value:.0f}C"


def speed(value: float | None) -> str:
    if value is None:
        return "--/s"
    units = ("B/s", "KB/s", "MB/s", "GB/s")
    amount = value
    unit = units[0]
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            break
        amount /= 1024
    if amount >= 100 or unit == "B/s":
        return f"{amount:.0f}{unit}"
    return f"{amount:.1f}{unit}"


def compact_status(metrics: Metrics) -> str:
    return (
        f"CPU {percent(metrics.cpu_usage)} {temp(metrics.cpu_temp_c)}  "
        f"GPU {percent(metrics.gpu_usage)} {temp(metrics.gpu_temp_c)}  "
        f"MEM {percent(metrics.memory_usage)}  "
        f"NET D {speed(metrics.net_down_bps)} U {speed(metrics.net_up_bps)}"
    )


def menu_lines(metrics: Metrics) -> list[str]:
    return [
        f"CPU usage: {percent(metrics.cpu_usage)}",
        f"CPU temperature: {temp(metrics.cpu_temp_c)}",
        f"NVIDIA GPU usage: {percent(metrics.gpu_usage)}",
        f"NVIDIA GPU temperature: {temp(metrics.gpu_temp_c)}",
        f"Memory usage: {percent(metrics.memory_usage)}",
        f"Download: {speed(metrics.net_down_bps)}",
        f"Upload: {speed(metrics.net_up_bps)}",
    ]
