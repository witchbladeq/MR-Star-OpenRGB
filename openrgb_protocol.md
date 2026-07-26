# OpenRGB Integration — Findn MR Star

OpenRGB **cannot** talk BLE directly from *Manually added devices* (no Generic BLE entry). Practical path: run a local **E1.31/DDP bridge** that OpenRGB already supports.

Native C++ detector notes remain below for a future OpenRGB upstream patch.

---

## Quick start (recommended): E1.31 bridge

```text
OpenRGB  --E1.31 UDP-->  openrgb_bridge.py  --BLE-->  LED strip
```

### 1. Start the bridge

```bash
pip install bleak
python openrgb_bridge.py
```

Leave this window open. It binds:

| Protocol | Port | Default |
|----------|------|---------|
| E1.31 / sACN | 5568 | universe 1 |
| DDP | 4048 | optional |

### 2. Add device in OpenRGB

**Settings → Manually added devices → Add device… → E1.31**

| Field | Value |
|-------|-------|
| Name | MR Star (any) |
| IP (Unicast) | `127.0.0.1` |
| Start Universe | `1` |
| Start Channel | `1` |
| Number of LEDs | `1` |
| Universe Size | `512` |
| Keepalive Time | default / 0 |

Then **Update device list** / rescan.

Use **1 LED** because the controller only accepts a single whole-strip HSV color (CMD 4), not per-pixel RGB.

### 3. Control

Open the new E1.31 device in OpenRGB, set mode to Direct / color, change color — the bridge prints `TX …` and updates the strip.

Black (`0,0,0`) → minimum brightness (power stays ON). Color wheel must not toggle power.

### Alternative: DDP

Same bridge also listens for **DDP** on port 4048. In OpenRGB: Add device → **DDP**, IP `127.0.0.1`.

---

## Device summary (native detector)

| Item | Value |
|------|-------|
| Transport | Bluetooth LE |
| Service | `0000FFF0-0000-1000-8000-00805F9B34FB` |
| Write char | `0000FFF3-0000-1000-8000-00805F9B34FB` |
| Notify char | `0000FFF4-0000-1000-8000-00805F9B34FB` |
| Framing | `BC ‖ CMD ‖ LEN ‖ PAYLOAD ‖ 55` |
| MTU write strategy | Split writes &gt; 20 bytes into 20-byte chunks, 200 ms apart |

Suggested detector name: **Findn MR Star**.

A native detector would live as a new OpenRGB controller using WinRT / BlueZ / CoreBluetooth. Until that exists, use `openrgb_bridge.py`.

---

## Recommended OpenRGB mode mapping (native)

### 1. Direct / Static (primary)

**Protocol:** CMD 4 (HSV) + CMD 5 (brightness).

```
BC 04 06 H_hi H_lo S_hi S_lo 00 00 55
BC 05 06 B_hi B_lo 00 00 00 00 55
```

**Power:** CMD 1 (`01` = on, `00` = off).

### 2. Effect / Scene modes

CMD 6 + CMD 8 + CMD 7. See [scenes.md](scenes.md).

---

## Zone / LED layout

Whole-strip only → **1 LED / 1 zone** in OpenRGB. No per-LED BLE packets exist in the app.

---

## Risks / limits

1. HSV-only color path (mirror app converter `e2.e.B`).
2. No per-LED control on the wire.
3. Do not run the Android app and the bridge at the same time (one GATT connection).
4. Bridge throttles BLE writes (~20 Hz); sACN is much faster.

---

## Minimal packet set

```
Power on:     BC 01 01 01 55
Power off:    BC 01 01 00 55
Set color:    BC 04 06 ... 00 00 55
Brightness:   BC 05 06 ... 00 00 00 00 55
```
