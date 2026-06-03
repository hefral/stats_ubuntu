from __future__ import annotations

import argparse
import signal
import sys
import time

from .formatting import compact_status, menu_lines
from .metrics import MetricsReader, probe_temperature_candidates


APP_ID = "stats-ubuntu"
REFRESH_SECONDS = 2


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ubuntu status monitor for GNOME/AppIndicator.")
    parser.add_argument("--debug", action="store_true", help="print metrics to the terminal instead of starting the tray app")
    parser.add_argument("--probe-sensors", action="store_true", help="print discovered temperature sensors and exit")
    parser.add_argument("--interval", type=float, default=REFRESH_SECONDS, help="refresh interval in seconds")
    args = parser.parse_args(argv)

    if args.probe_sensors:
        run_sensor_probe()
        return

    if args.debug:
        run_debug(args.interval)
        return

    try:
        run_indicator(args.interval)
    except ImportError as exc:
        print(f"AppIndicator dependencies are missing: {exc}", file=sys.stderr)
        print("Try: sudo apt install gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 python3-gi", file=sys.stderr)
        print("You can still run: uv run stats-ubuntu --debug", file=sys.stderr)
        raise SystemExit(2) from exc


def run_debug(interval: float) -> None:
    reader = MetricsReader()
    try:
        while True:
            metrics = reader.read()
            print(compact_status(metrics), flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        return


def run_sensor_probe() -> None:
    candidates = probe_temperature_candidates()
    if not candidates:
        print("No hwmon temperature sensors found.")
        return

    for item in candidates:
        marker = "cpu" if item.priority is not None else "other"
        print(
            f"{marker:5} {item.temperature_c:5.1f}C "
            f"priority={item.priority if item.priority is not None else '-':>2} "
            f"chip={item.chip} label={item.label} path={item.path}"
        )


def run_indicator(interval: float) -> None:
    import gi

    gi.require_version("Gtk", "3.0")
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator
    except (ValueError, ImportError):
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppIndicator

    from gi.repository import GLib, Gtk

    reader = MetricsReader()
    indicator = AppIndicator.Indicator.new(
        APP_ID,
        "utilities-system-monitor",
        AppIndicator.IndicatorCategory.SYSTEM_SERVICES,
    )
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()
    metric_items = [Gtk.MenuItem(label="Starting...") for _ in range(7)]
    for item in metric_items:
        item.set_sensitive(False)
        menu.append(item)

    menu.append(Gtk.SeparatorMenuItem())
    quit_item = Gtk.MenuItem(label="Quit")
    quit_item.connect("activate", lambda _item: Gtk.main_quit())
    menu.append(quit_item)
    menu.show_all()
    indicator.set_menu(menu)

    def update() -> bool:
        metrics = reader.read()
        indicator.set_label(compact_status(metrics), APP_ID)
        for item, label in zip(metric_items, menu_lines(metrics), strict=True):
            item.set_label(label)
        return True

    update()
    GLib.timeout_add_seconds(max(1, int(interval)), update)

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()


if __name__ == "__main__":
    main()
