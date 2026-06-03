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

On Ubuntu, use the setup script so the uv environment can see GTK/AppIndicator
packages installed by `apt`:

```bash
./scripts/setup-ubuntu.sh
```

Then run:

```bash
uv run stats-ubuntu
```

For a terminal-only debug loop:

```bash
uv run stats-ubuntu --debug
```

To inspect CPU temperature sensor detection:

```bash
uv run stats-ubuntu --probe-sensors
```

## Notes

CPU temperature probing scans `/sys/class/hwmon` first and prefers Intel `coretemp`
entries such as `Package id 0`. It also falls back to thermal zones.


好，明天到 Ubuntu 机器上先按这个顺序试就行：

```bash
sudo apt install gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 python3-gi
./scripts/setup-ubuntu.sh
uv run stats-ubuntu --debug
uv run stats-ubuntu --probe-sensors
uv run stats-ubuntu
```

如果 `--debug` 有数据但状态栏不显示，多半是 GNOME AppIndicator 扩展/托盘支持的问题；如果 CPU 温度不对，把 `--probe-sensors` 的输出贴给我，我就能按你那台微星 + Intel 的实际传感器名字继续调。