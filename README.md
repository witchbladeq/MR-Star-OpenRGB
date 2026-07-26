# MR Star OpenRGB

Unofficial OpenRGB bridge and BLE tools for **Findn MR Star** / compatible LED strips (Android app package `com.findn.mrstar`).

OpenRGB cannot talk BLE from *Manually added devices*. This project pretends to be an **E1.31 (sACN)** and/or **DDP** receiver on localhost and translates colors to the strip’s BLE protocol.

```text
OpenRGB  --E1.31 / DDP-->  openrgb_bridge.py  --BLE-->  LED strip
```

## Requirements

- Python 3.10+
- Bluetooth LE adapter
- [OpenRGB](https://openrgb.org/)
- Do not run the official Android app and the bridge at the same time (one GATT connection)

```bash
pip install -r requirements.txt
```

## Quick start (OpenRGB)

1. Power on the strip and find its BLE MAC (`python led.py scan`).
2. Start the bridge with your MAC:

```bash
python openrgb_bridge.py --mac AA:BB:CC:DD:EE:FF
```

3. In OpenRGB: **Settings → Manually added devices → Add device → E1.31**

| Field | Value |
|-------|-------|
| Name | MR Star (any) |
| IP (Unicast) | `127.0.0.1` |
| Start Universe | `1` |
| Start Channel | `1` |
| Number of LEDs | `1` |
| Universe Size | `512` |

Use **1 LED** — the controller accepts a single whole-strip HSV color, not per-pixel RGB.

4. Rescan / update device list and set a color. The bridge prints `TX …` on updates.

### Alternative: DDP

Same process also listens on UDP **4048**. In OpenRGB add a **DDP** device with IP `127.0.0.1`.

## CLI (`led.py`)

Direct BLE control without OpenRGB:

```bash
python led.py scan
python led.py on
python led.py color 255 80 0
python led.py scene 1
python led.py --help
```

## Docs

| File | Contents |
|------|----------|
| `openrgb_protocol.md` | OpenRGB setup + native-detector notes |
| `protocol.md` | Full BLE command catalog |
| `scenes.md` | Scene / effect ID table (CMD 6) |

## Limits

- Whole-strip color only (no per-LED wire packets in the OEM app).
- Color path is HSV (mirrors the Android converter).
- Bridge throttles BLE writes; sACN is much faster than the radio can accept.
- Use at your own risk; unofficial reverse-engineering, not affiliated with Findn / OpenRGB.
