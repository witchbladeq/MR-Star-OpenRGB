# BLE Protocol — Findn MR Star (`com.findn.mrstar`)

Reverse-engineered from the official Android application (JADX decompile of
GATT helpers, UI fragments, and string resources).

Pass the device MAC with `--mac` (no hardcoded address in this repo).

## GATT

| Role | UUID |
|------|------|
| Service | `0000FFF0-0000-1000-8000-00805F9B34FB` |
| Write | `0000FFF3-0000-1000-8000-00805F9B34FB` |
| Notify | `0000FFF4-0000-1000-8000-00805F9B34FB` |
| CCCD | `00002902-0000-1000-8000-00805F9B34FB` |

All application commands are written through `MyApplication.d(byte[])` → characteristic **FFF3**.

Writes longer than **20 bytes** are split into 20-byte chunks with a **200 ms** gap (`s0.e`, `MyApplication.d`).

Scan filter manufacturer bytes (not a command): `0x22`, `0x20` (`MyApplication.e` / `f`).

---

## Packet framing

```
BC | CMD | LEN | PAYLOAD... | 55
```

| Field | Offset | Type | Notes |
|-------|--------|------|-------|
| Start | 0 | `0xBC` | Signed Java byte `-68` |
| Command | 1 | uint8 | Command ID |
| Length | 2 | uint8 | Number of payload bytes that follow (before end marker) |
| Payload | 3… | bytes | Command-specific |
| End | last | `0x55` | Signed Java byte `85` |

Total packet size = `3 + LEN + 1`.

---

## Command catalog

### CMD 1 — Power

```
BC 01 01 <state> 55
```

| `state` | Meaning |
|---------|---------|
| `01` | Power **ON** |
| `00` | Power **OFF** |

The power control is `cb_power` with drawable `cb_light_selector`:

- `state_checked=true` → icon `ic_off` → writes `00`
- `state_checked=false` → icon `ic_on` → writes `01`

So the checkbox *checked* flag is inverted relative to “lights on”.

**Examples**

```
BC 01 01 01 55   Power ON
BC 01 01 00 55   Power OFF
```

**Source:** `AdjustFragment` → `e1.b.onCheckedChanged` (`cb_power`); icons in `cb_light_selector.xml`

---

### CMD 2 — RGB channel order (wire order)

```
BC 02 01 <order> 55
```

`order = wheelPosition + 1`

| Value | Order |
|-------|-------|
| 1 | RGB |
| 2 | RBG |
| 3 | GRB |
| 4 | GBR |
| 5 | BRG |
| 6 | BGR |

**Example:** `BC 02 01 03 55` — GRB

**Source:** `MainActivity` → dialog `ll_set_line` / `c1.c`

**Note:** There is **no** IC-type BLE command in this application.

---

### CMD 3 — Pixel / LED count

```
BC 03 02 <hi> <lo> 55
```

- Count is **uint16 big-endian**: `(hi << 8) | lo`, built as `count/256`, `count%256`
- UI validates range **8–300**

**Example:** 150 LEDs → `BC 03 02 00 96 55`

**Source:** `c1.b` from `MainActivity` (`ll_set_point`) and `AdjustFragment` (`btn_set_pixels`)

---

### CMD 4 — HSV color (static / music visualizer)

```
BC 04 06 H_hi H_lo S_hi S_lo 00 00 55
```

| Field | Encoding |
|-------|----------|
| H | Hue degrees 0–360, uint16 BE (`/256`, `%256`) |
| S | Saturation × 1000 (0–1000), uint16 BE |
| Last two payload bytes | Always `00 00` (V unused; brightness is CMD 5) |

RGB→HSV via `e2.e.B()` → `Color.RGBToHSV`. If saturation > 1 or hue and sat are both 0, saturation is forced to `1.0`.

**Example:** hue 120, sat 1000 → `BC 04 06 00 78 03 E8 00 00 55`

**Sources:**
- `AdjustFragment.f0` / `h0` / `i0`
- `MusicFragment.b.onFftDataCapture` (phone music → continuous CMD 4)

---

### CMD 5 — Brightness

```
BC 05 06 B_hi B_lo 00 00 00 00 55
```

- Brightness uint16 BE, UI seekbar **min 100 / max 1000** (layout); write path clamps values **&lt; 3** up to 3 (`e1.d`)
- Stored in `MyApplication.f1781h` (default 1000)

**Example:** 500 → `BC 05 06 01 F4 00 00 00 00 55`

**Sources:** `e1.d` (Adjust), `e1.h` (Mode)

---

### CMD 6 — Scene / effect mode

```
BC 06 02 <hi> <lo> 55
```

**Encoding uses ÷255 / %255** (not 256):

```java
(byte)(id / 255), (byte)(id % 255)
```

For IDs 1–254 this yields `00 <id>`.

See [scenes.md](scenes.md) for the full ID ↔ name table (1–117).

**Example:** scene 15 → `BC 06 02 00 0F 55`

**Source:** `ModeFragment.f0` ← tab listener `e1.i`, wheel listener `e1.j` / `WheelPicker`

---

### CMD 7 — Effect direction

```
BC 07 01 <dir> 55
```

| `dir` | UI (`ls_direction`) | Stored `MyApplication.f1783j` |
|-------|---------------------|-------------------------------|
| `00` | Checked — Reverse (`R`) | `true` |
| `01` | Unchecked — Positive (`P`) | `false` |

**Examples**

```
BC 07 01 00 55   Reverse
BC 07 01 01 55   Positive / forward
```

**Source:** `e1.c.a` ← `ModeFragment` `LSwitch`

**Note:** There is no separate “auto color” BLE command. Scene **1** (`Automatic loop`) is the automatic cycling effect.

---

### CMD 8 — Effect speed

```
BC 08 01 <speed> 55
```

- SeekBar **min 1 / max 100**
- Stored in `MyApplication.f1782i` (default 50)

**Example:** `BC 08 01 50 55` — speed 80 decimal → `BC 08 01 50 55` if 80; speed 80 → `BC 08 01 50` is wrong — 80 = `0x50`: `BC 08 01 50 55`

**Source:** `e1.g` ← ModeFragment `sb_speed`

---

### CMD 9 — Phone-microphone HSV color

```
BC 09 06 H_hi H_lo S_hi S_lo 00 00 55
```

Same HSV encoding as CMD 4. Sent from the phone-mic amplitude → palette path.

**Source:** `f1.d.a` ← `MicroPhoneFragment` phone-mic mode (`CMD 15 = 0`)

---

### CMD 10 — Not present

No write or notify handler constructs command ID 10.

---

### CMD 11 — Clock sync

```
BC 0B 07 Y_hi Y_lo Month Day Hour Min Sec 55
```

| Byte | Source |
|------|--------|
| Y_hi, Y_lo | `e2.e.M(year)` → `(year >> 8) & 0xFF`, `year & 0xFF` |
| Month | `Calendar.MONTH + 1` (1–12) |
| Day | `DAY_OF_MONTH` |
| Hour / Min / Sec | 24-hour clock |

**Source:** `TimerFragment.P` on enter (see `_jadx_out/TimerFragment.java`)

On write failure, commands with `bArr[1] ∈ {11, 12, 80}` are retried (`MyApplication.c`). CMD **80** is never constructed by the app — retry sentinel only.

---

### CMD 12 — Timer query

```
BC 0C 01 01 55
```

**Sources:**
- `TimerFragment.P` after enabling FFF4 notifications
- `TimerFragment.onMessageEvent` if a notify arrives with `bArr[1] != 13`

---

### CMD 13 — Timer set

```
BC 0D 06 01 <slot> <enable> <weekMask> <hour> <min> 55
```

| Field | Values |
|-------|--------|
| Constant | Always `01` after LEN |
| `slot` | `01` = ON timer, `00` = OFF timer |
| `enable` | `01` enabled, `00` disabled |
| `weekMask` | Bitmask (see below) |
| `hour` | 0–23 |
| `min` | 0–59 |

**Week bitmask** (`TimerFragment.f0`):

| Bit | Day |
|-----|-----|
| 0 | Monday |
| 1 | Tuesday |
| 2 | Wednesday |
| 3 | Thursday |
| 4 | Friday |
| 5 | Saturday |
| 6 | Sunday |
| 7 | UI sync / enable-related flag (initialized `true` when Timer tab opens; toggled with the enable switch) |

Bit set ⇒ day selected: `mask |= (1 << bit)`.

**Sources:** `TimerFragment.h0` (OFF slot), `TimerFragment.i0` (ON slot)

**Notify response:** Device echoes CMD 13 on FFF4; `TimerFragment.onMessageEvent` parses the same layout (`bArr[4]` slot, `bArr[5]` enable, `bArr[6]` mask, `bArr[7]` hour, `bArr[8]` min).

---

### CMD 14 — Not present

---

### CMD 15 — Microphone source

```
BC 0F 01 <source> 55
```

| Value | Meaning | UI |
|-------|---------|-----|
| `01` | Device microphone | SegmentedButton position 0; default on `MicroPhoneFragment` create |
| `00` | Phone microphone | SegmentedButton position 1 |

**Sources:** `SegmentedButtonGroup.e`, `MicroPhoneFragment.E`

There is no dedicated “music enable” BLE command. The Music tab streams colors with **CMD 4** from the phone audio visualizer.

---

### CMD 16 — Sensitivity report (notify only)

No application write. Notify payload: `bArr[1] == 16` → `MyApplication.n = bArr[3]`.

Handled in `MainActivity.onMessageEvent`.

---

### CMD 17 — Device-mic effect mode

```
BC 11 01 <mode> 55
```

| Value | Radio ID | String resource |
|-------|----------|-----------------|
| 1 | `rb_classic` | Energy (`mic_energy`) |
| 2 | `rb_soft` | Rhythm (`mic_rhythm`) |
| 3 | `rb_dynamic` | Spectrum (`mic_spectrum`) |
| 4 | `rb_disco` | Scroll (`mic_scroll`) |

**Source:** `MicroPhoneFragment` → `e1.e`

---

### CMD 18 — Microphone sensitivity

```
BC 12 01 <level> 55
```

- SeekBar **min 1 / max 100**
- Also written to `MyApplication.n` (default 100)

**Source:** `e1.f` ← `sb_sensitivity`

---

### CMD 19 — Color-wheel angle

```
BC 13 02 <hi> <lo> 55
```

Angle as uint16 BE (`/256`, `%256`), derived from atan2 on `CustomColorPicker2` (≈0–360°). The picker view is present but marked invisible in the adjust UI; the write path still exists.

**Source:** `e1.c.b` ← `CustomColorPicker2` up-action

---

## Notify / response packets (FFF4)

Notifications are enabled in `TimerFragment.P` (CCCD write). Payloads are posted via EventBus as `b1.a(7, payload)`.

| `bArr[1]` | Handler | Action |
|-----------|---------|--------|
| 5 | `MainActivity` | Brightness ← `(bArr[3]<<8)\|bArr[4]` |
| 8 | `MainActivity` | Speed ← `bArr[3]` |
| 13 | `TimerFragment` | Timer state echo |
| 16 | `MainActivity` | Sensitivity ← `bArr[3]` |

Expected frame shape matches writes (`BC | CMD | LEN | … | 55`).

**Current color cannot be read.** The app never parses a CMD 4 (HSV) notify and never sends a “get color” / status-query command. Color lives only in the UI / last write. Notify traffic observed in the app is limited to brightness, speed, timer, and sensitivity.

---

## Features not present over BLE

Verified absent from all `MyApplication.d` / `byte[]{-68,…}` sites:

| Feature | Status |
|---------|--------|
| IC / LED chip type | Not exposed (CMD 2 is RGB order only) |
| Color temperature | Not present |
| Segment count | Not present |
| Power restore | Not present |
| Dedicated auto-color toggle | Not present (use scene 1) |
| Dedicated music on/off | Not present (Music tab → CMD 4 stream) |
| Music effect modes | Not present (mic modes are CMD 17) |
| Shake-to-color | Marketing string only; no sensor BLE path |
| CMD 10, 14 | Never constructed |
| CMD 80 | Retry sentinel only |

---

## Quick reference (hex examples)

```
BC 01 01 01 55                         Power ON
BC 01 01 00 55                         Power OFF
BC 02 01 01 55                         RGB order
BC 03 02 00 96 55                      150 pixels
BC 04 06 00 00 03 E8 00 00 55          HSV H=0 S=1000 (red-ish)
BC 05 06 01 F4 00 00 00 00 55          Brightness 500
BC 06 02 00 0F 55                      Scene 15
BC 07 01 00 55                         Direction reverse
BC 07 01 01 55                         Direction forward
BC 08 01 50 55                         Speed 80
BC 09 06 00 78 03 E8 00 00 55          Phone-mic HSV
BC 0B 07 07 E8 07 1A 0D 1E 00 55       Clock sync example (year 2024…)
BC 0C 01 01 55                         Timer query
BC 0D 06 01 01 01 7F 08 00 55          ON timer enable, week mask, 08:00
BC 0F 01 01 55                         Device mic
BC 0F 01 00 55                         Phone mic
BC 11 01 02 55                         Mic mode Rhythm
BC 12 01 32 55                         Sensitivity 50
BC 13 02 00 B4 55                      Angle 180
```
