# Stats Ubuntu

A small Ubuntu/GNOME status monitor inspired by Stats for macOS.

Initial scope:

- CPU usage
- CPU temperature
- NVIDIA GPU usage and temperature
- Memory usage
- Network upload/download speed

The app uses Linux system files for most metrics and `nvidia-smi` for NVIDIA GPUs.

## Requirements

Ubuntu/GNOME usually needs AppIndicator support:

```bash
sudo apt install gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 python3-gi
```

For NVIDIA metrics, install the NVIDIA driver package that provides `nvidia-smi`.

## Run With uv

```bash
cd stats_ubuntu
uv sync
uv run stats-ubuntu
```

For a terminal-only debug loop:

```bash
uv run stats-ubuntu --debug
```

## Notes

CPU temperature probing scans `/sys/class/hwmon` first and prefers Intel `coretemp`
entries such as `Package id 0`. It also falls back to thermal zones.
